"""启动后端和前端（带 network-alias）。"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456")

def run(cmd, timeout=60):
    print(f">>> {cmd[:100]}...")
    i, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode()
    err = e.read().decode()
    if out: print(out, end="")
    if err: print(f"[err] {err}", end="")
    return o.channel.recv_exit_status()

# 启动后端（加 network-alias backend）
print("=== 启动后端 ===")
run("docker run -d --name ai-ide-backend --network aide-net "
    "--network-alias backend "
    "-p 8000:8000 "
    "-e AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@ai-ide-db:5432/ai_workspace_db "
    "-e AI_IDE_DEEPSEEK_API_KEY=sk-883b52eef3df4a7f873b32866f5d2e96 "
    "-e AI_IDE_DASHSCOPE_API_KEY=sk-1723d63c8020479ebff6db95d767ee9a "
    "-e UVICORN_WORKERS=1 "
    "-v /home/czm/app/runtime:/app/runtime "
    "app-backend:latest")

# 等后端就绪
time.sleep(5)

# 启动前端
print("\n=== 启动前端 ===")
run("docker run -d --name ai-ide-frontend --network aide-net "
    "-p 80:80 "
    "app-frontend:latest")

time.sleep(3)

# 检查状态
print("\n=== 容器状态 ===")
run("docker ps --filter name=ai-ide")

# 检查后端日志
print("\n=== 后端日志 ===")
run("docker logs ai-ide-backend 2>&1 | head -20")

# 检查前端日志
print("\n=== 前端日志 ===")
run("docker logs ai-ide-frontend 2>&1 | head -20")

# 测试连通性
print("\n=== 测试后端 API ===")
run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/health/db || true")
print()
run("curl -s -o /dev/null -w '%{http_code}' http://localhost/ || true")
print()

ssh.close()
