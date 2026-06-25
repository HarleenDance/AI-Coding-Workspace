"""清理旧容器并直接用 docker run 启动服务。"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456")

def run(cmd, timeout=60):
    print(f">>> {cmd}")
    i, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode()
    err = e.read().decode()
    if out: print(out, end="")
    if err: print(f"[err] {err}", end="")
    return o.channel.recv_exit_status()

# 1. 停掉占用 80 端口的 super-admin-client
print("=== 停掉 super-admin 服务 ===")
run("docker stop super-admin-client-1 super-admin-server-1")

# 2. 删掉所有 ai-ide-* 容器
print("\n=== 清理旧 ai-ide 容器 ===")
run("docker rm -f ai-ide-db ai-ide-frontend ai-ide-backend 2>&1 || true")
run("docker rm -f eager_thompson 2>&1 || true")

# 3. 创建网络（如果不存在）
print("\n=== 创建网络 ===")
run("docker network create aide-net 2>&1 || true")

# 4. 启动数据库（不映射端口到宿主机，避免冲突）
print("\n=== 启动数据库 ===")
run("docker run -d --name ai-ide-db --network aide-net "
    "-e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=ai_workspace_db "
    "-v aide-pgdata:/var/lib/postgresql/data "
    "pgvector/pgvector:pg16")

# 5. 等数据库就绪
print("\n=== 等待数据库就绪 ===")
time.sleep(12)
run("docker exec ai-ide-db pg_isready -U postgres")

# 6. 启动后端
print("\n=== 启动后端 ===")
run("docker run -d --name ai-ide-backend --network aide-net "
    "-p 8000:8000 "
    "-e AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@ai-ide-db:5432/ai_workspace_db "
    "-e AI_IDE_DEEPSEEK_API_KEY=sk-883b52eef3df4a7f873b32866f5d2e96 "
    "-e AI_IDE_DASHSCOPE_API_KEY=sk-1723d63c8020479ebff6db95d767ee9a "
    "-e UVICORN_WORKERS=1 "
    "-v /home/czm/app/runtime:/app/runtime "
    "app-backend:latest")

# 7. 启动前端（nginx），连接后端
print("\n=== 启动前端 ===")
run("docker run -d --name ai-ide-frontend --network aide-net "
    "-p 80:80 "
    "app-frontend:latest")

# 8. 检查状态
print("\n=== 容器状态 ===")
time.sleep(3)
run("docker ps --filter name=ai-ide")

# 9. 检查后端日志
print("\n=== 后端日志 ===")
run("docker logs ai-ide-backend 2>&1 | head -30 || true")

ssh.close()
