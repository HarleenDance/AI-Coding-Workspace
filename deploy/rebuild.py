"""重新构建前后端镜像并重启服务。"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456")

def run(cmd, timeout=600):
    print(f">>> {cmd[:120]}")
    i, o, e = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
    while not o.channel.exit_status_ready():
        line = o.readline()
        if line:
            print(line, end="")
    rest = o.read().decode()
    if rest:
        print(rest, end="")
    code = o.channel.recv_exit_status()
    print(f"[exit={code}]")
    return code

# 1. 构建后端
print("===== 构建后端 =====")
run("cd /home/czm/app && export DOCKER_BUILDKIT=0 && docker build -t app-backend:latest -f deploy/backend.Dockerfile aI-coding-workspace-backend")

# 2. 构建前端
print("\n===== 构建前端 =====")
run("cd /home/czm/app && export DOCKER_BUILDKIT=0 && docker build -t app-frontend:latest aI-coding-workspace-frontend")

# 3. 重启后端
print("\n===== 重启后端 =====")
run("docker rm -f ai-ide-backend && docker run -d --name ai-ide-backend --network aide-net --network-alias backend -p 8000:8000 -e AI_IDE_DATABASE_URL=postgresql+asyncpg://postgres:123456@ai-ide-db:5432/ai_workspace_db -e AI_IDE_DEEPSEEK_API_KEY=sk-883b52eef3df4a7f873b32866f5d2e96 -e AI_IDE_DASHSCOPE_API_KEY=sk-1723d63c8020479ebff6db95d767ee9a -e UVICORN_WORKERS=1 -v /home/czm/app/runtime:/app/runtime app-backend:latest")

# 4. 重启前端
print("\n===== 重启前端 =====")
run("docker rm -f ai-ide-frontend && docker run -d --name ai-ide-frontend --network aide-net -p 8080:80 app-frontend:latest")

# 5. 等待就绪
time.sleep(8)

# 6. 初始化新 Agent
print("\n===== 初始化内置 Agent =====")
run("curl -s -X POST http://localhost:8000/api/agents/init-builtin")

# 7. 验证
print("\n===== 验证服务 =====")
run("docker ps --filter name=ai-ide --format 'table {{.Names}}\t{{.Status}}'")
run("curl -so /dev/null -w '%{http_code}' http://localhost:8000/api/health/db")
print()
run("curl -so /dev/null -w '%{http_code}' http://localhost:8080/")
print()

ssh.close()
