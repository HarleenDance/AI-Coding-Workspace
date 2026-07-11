#!/usr/bin/env bash
set -euo pipefail

BACKEND_IMAGE="${BACKEND_IMAGE:-app-backend:latest}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-app-frontend:latest}"

cd "$(dirname "$0")/.."

step() {
  printf '\n==== %s ====\n' "$1"
}

step "Checking required commands"
docker --version
docker compose version

step "Preparing .env"
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Fill API keys for real AI calls."
  else
    cat > .env <<'EOF'
DB_PASSWORD=change_this_password
DEEPSEEK_API_KEY=
DASHSCOPE_API_KEY=
EOF
    echo "Created default .env."
  fi
fi

if [ -n "${DB_PASSWORD:-}" ]; then
  {
    echo "DB_PASSWORD=${DB_PASSWORD:-}"
    echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}"
    echo "DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY:-}"
  } > .env
  echo "Wrote .env from Jenkins environment variables."
fi

BUILD_ARGS=()
if [ "${NO_CACHE:-false}" = "true" ]; then
  BUILD_ARGS+=(--no-cache)
fi

step "Building backend image"
docker build "${BUILD_ARGS[@]}" -f deploy/backend.Dockerfile -t "$BACKEND_IMAGE" aI-coding-workspace-backend

step "Building frontend image"
docker build "${BUILD_ARGS[@]}" -t "$FRONTEND_IMAGE" aI-coding-workspace-frontend

step "Cleaning up old containers and volumes"
docker rm -f ai-ide-db ai-ide-backend ai-ide-frontend 2>/dev/null || true
# Remove old pgdata volume so POSTGRES_HOST_AUTH_METHOD takes effect
docker volume rm aicodingworkspace_pgdata ai-coding-workspace_pgdata 2>/dev/null || true

step "Starting services"
docker compose up -d db
docker compose up -d backend frontend

step "Service status"
docker compose ps

step "Backend health check"
# Jenkins runs inside Docker; use host.docker.internal to reach host-mapped ports
HEALTH_URL="http://host.docker.internal:8000/api/health/db"
if ! getent hosts host.docker.internal >/dev/null 2>&1; then
  HEALTH_URL="http://localhost:8000/api/health/db"
fi
for i in $(seq 1 30); do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    echo "Backend is healthy: $HEALTH_URL"
    echo "Frontend: http://localhost:3000/"
    echo "Backend API: http://localhost:8000/api"
    echo "Database: internal (db:5432)"
    exit 0
  fi
  sleep 3
done

echo "Backend health check failed. Recent backend logs:"
docker compose logs --tail=120 backend
exit 1
