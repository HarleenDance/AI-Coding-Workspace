"""上传本地 dist 并在服务器上构建简化前端镜像（无 vite build，避免 OOM）。"""
import io
import os
import zipfile
import paramiko
import time

from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent / "aI-coding-workspace-frontend"
DIST_DIR = FRONTEND_DIR / "dist"
NGINX_CONF = FRONTEND_DIR / "nginx.conf"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456", timeout=15)

def run(cmd, timeout=120):
    print(f">>> {cmd[:120]}")
    i, o, e = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
    out = o.read().decode()
    print(out, end="")
    return o.channel.recv_exit_status()

# 1. 打包 dist + nginx.conf + 简化 Dockerfile
print("===== 打包 dist =====")
zip_buf = io.BytesIO()
zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk(DIST_DIR):
    for f in files:
        full = Path(root) / f
        rel = full.relative_to(DIST_DIR)
        zf.write(full, f"dist/{rel}")
zf.write(NGINX_CONF, "nginx.conf")
# 写入简化 Dockerfile
zf.writestr("Dockerfile.local", """FROM nginx:alpine
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""")
zf.close()
print(f"打包完成: {len(zip_buf.getvalue())/1024/1024:.1f} MB")

# 2. 上传
print("\n===== 上传 =====")
sftp = ssh.open_sftp()
with sftp.file("/tmp/frontend_dist.zip", "wb") as f:
    f.write(zip_buf.getvalue())
sftp.close()
print("上传完成")

# 3. 远程解压 + 构建
print("\n===== 远程解压 + 构建 =====")
run("mkdir -p /tmp/fe-build && cd /tmp/fe-build && python3 -c \"import zipfile; zipfile.ZipFile('/tmp/frontend_dist.zip').extractall('.')\" && cp Dockerfile.local Dockerfile && ls -la")

# 4. docker build（只需 COPY，秒级完成，无内存消耗）
print("\n===== 构建前端镜像 =====")
run("cd /tmp/fe-build && export DOCKER_BUILDKIT=0 && docker build -t app-frontend:latest .")

# 5. 重启前端容器
print("\n===== 重启前端 =====")
run("docker rm -f ai-ide-frontend")
run("docker run -d --name ai-ide-frontend --network aide-net -p 8080:80 app-frontend:latest")

# 6. 重启后端（用之前已构建的镜像）
print("\n===== 重启后端 =====")
run("docker rm -f ai-ide-backend 2>/dev/null || true")
run("docker run -d --name ai-ide-backend --network aide-net --network-alias backend -p 8000:8000 "
    "-e AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@ai-ide-db:5432/ai_workspace_db "
    "-e AI_IDE_DEEPSEEK_API_KEY=sk-883b52eef3df4a7f873b32866f5d2e96 "
    "-e AI_IDE_DASHSCOPE_API_KEY=sk-1723d63c8020479ebff6db95d767ee9a "
    "-e UVICORN_WORKERS=1 "
    "-v /home/czm/app/runtime:/app/runtime "
    "app-backend:latest")

# 7. 等待 + 初始化 Agent
time.sleep(8)
print("\n===== 初始化新 Agent =====")
run("curl -s -X POST http://localhost:8000/api/agents/init-builtin")

# 8. 验证
print("\n===== 验证 =====")
run("docker ps --filter name=ai-ide --format 'table {{.Names}}\t{{.Status}}'")

ssh.close()
