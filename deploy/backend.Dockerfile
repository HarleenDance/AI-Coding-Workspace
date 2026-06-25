# ====== 后端 Dockerfile（多阶段构建，镜像约 400MB） ======
FROM python:3.12-slim AS backend-builder

WORKDIR /build
COPY pyproject.toml ./
# 使用阿里云 PyPI 镜像加速（国内服务器）
RUN pip install --no-cache-dir -e . -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com 2>/dev/null || pip install --no-cache-dir . -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 生产运行时
FROM python:3.12-slim AS backend

WORKDIR /app

# 换阿里云 Debian 源（加速 apt）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; \
    true

# 安装终端所需的系统依赖（Linux PTY 用标准库，bash 预装）
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

# 只拷运行时需要的（不带 dev 依赖）
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

COPY app/ ./app/
COPY scripts/ ./scripts/

# 拷贝 .env（部署时挂载或写入）
# COPY .env ./

# 生产 uvicorn 配置：关闭 reload，限制 worker
ENV UVICORN_WORKERS=2
ENV UVICORN_PORT=8000

EXPOSE 8000

# 用 gunicorn 管理多进程（比裸 uvicorn 更稳）
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${UVICORN_PORT} --workers ${UVICORN_WORKERS} --no-access-log"]
