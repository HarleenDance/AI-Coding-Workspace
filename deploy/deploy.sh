#!/bin/bash
# ====== 一键部署脚本（阿里云 Ubuntu/Debian 4G 服务器） ======
# 用法: sudo bash deploy/deploy.sh
set -e

echo "========================================"
echo "  AI Coding Workspace - Production Deploy"
echo "========================================"

# 1. 检查 root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo bash deploy/deploy.sh"
  exit 1
fi

# 2. 配置 2G swap（关键！4G 服务器必备）
echo "[1/6] Configuring swap..."
if ! swapon --show | grep -q "/swapfile"; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  # 开机自动挂载
  if ! grep -q "/swapfile" /etc/fstab; then
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
  fi
  # 调低 swap 倾向（10 比 60 好，避免频繁 swap）
  sysctl vm.swappiness=10
  if ! grep -q "swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=10" >> /etc/sysctl.conf
  fi
  echo "  -> Swap 2G created and enabled"
else
  echo "  -> Swap already configured"
fi

# 3. 安装 Docker
echo "[2/6] Checking Docker..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  echo "  -> Docker installed"
else
  echo "  -> Docker already installed"
fi

# 4. 加载环境变量
echo "[3/6] Loading .env..."
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  cat > .env <<'EOF'
# 生产环境配置
DB_PASSWORD=change_this_password
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
EOF
  echo "  -> .env created. Edit it before continuing!"
  echo "  -> Run: nano .env"
  exit 1
fi
set -a; source .env; set +a
echo "  -> .env loaded"

# 5. 构建镜像
echo "[4/6] Building images..."
docker compose build --no-cache
echo "  -> Images built"

# 6. 启动服务
echo "[5/6] Starting services..."
docker compose down 2>/dev/null || true
docker compose up -d
echo "  -> Services started"

# 7. 初始化数据库 + 内置智能体
echo "[6/6] Initializing database..."
sleep 10  # 等 db ready
docker compose exec -T backend python scripts/init_db.py
docker compose exec -T backend python -c "
import httpx
r = httpx.post('http://localhost:8000/api/agents/init-builtin')
print(r.json())
" || echo "  -> Agent init skipped"

echo ""
echo "========================================"
echo "  Deployment complete!"
echo "========================================"
echo ""
echo "  Frontend: http://$(curl -s ifconfig.me)"
echo "  Backend:  http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "  Memory usage:"
free -h
echo ""
echo "  Logs: docker compose logs -f"
echo "  Stop: docker compose down"
echo "========================================"
