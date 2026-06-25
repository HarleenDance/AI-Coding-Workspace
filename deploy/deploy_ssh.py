"""SSH 部署辅助脚本。

用法: python deploy_ssh.py probe | upload | build | up | logs | init
"""
import sys
import paramiko
import os
from pathlib import Path

HOST = "8.130.118.128"
USER = "czm"
PASSWORD = "czm123456"
REMOTE_APP_DIR = "/home/czm/app"
PROJECT_LOCAL_ROOT = Path(__file__).parent.parent  # AI Coding Workspace


def get_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
    return ssh


def run_remote(cmd: str, timeout: int = 120):
    """执行远程命令，实时打印输出。"""
    ssh = get_ssh()
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
        while not stdout.channel.exit_status_ready():
            line = stdout.readline()
            if line:
                print(line, end="")
        # 读剩余
        rest = stdout.read().decode("utf-8", errors="replace")
        if rest:
            print(rest, end="")
        err = stderr.read().decode("utf-8", errors="replace")
        if err:
            print(f"[stderr] {err}", end="")
        exit_code = stdout.channel.recv_exit_status()
        print(f"\n[exit_code={exit_code}]")
        return exit_code
    finally:
        ssh.close()


def probe():
    """探测服务器环境。"""
    print("===== 探测服务器环境 =====")
    run_remote(
        "echo '--- OS ---'; cat /etc/os-release | head -3; "
        "echo '--- Docker ---'; docker --version 2>&1; docker compose version 2>&1; "
        "echo '--- Disk ---'; df -h / | tail -1; "
        "echo '--- Memory ---'; free -h; "
        f"echo '--- App dir ---'; ls -la {REMOTE_APP_DIR} 2>&1 | head -20; "
        "echo '--- Git ---'; git --version 2>&1"
    )


def upload():
    """上传项目（排除 node_modules/.venv/runtime 等大目录）。"""
    import io
    import zipfile

    print("===== 打包并上传项目 =====")
    ssh = get_ssh()
    try:
        # 1. 本地打包 zip（内存中）
        print("打包中...")
        excludes_dirs = {
            "node_modules", ".venv", "venv", "__pycache__", ".git",
            "runtime", "dist", "build", ".next",
            ".pytest_cache", ".mypy_cache", ".ruff_cache",
            "awesome-agentic-ai-zh", "tmp_pgvector", ".idea", ".vscode",
        }
        excludes_suffixes = {".pyc", ".pyo", ".log", ".zip"}
        zip_buf = io.BytesIO()
        zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)

        for root, dirs, files in os.walk(PROJECT_LOCAL_ROOT):
            # 过滤目录（原地修改 dirs 控制 os.walk 递归）
            dirs[:] = [d for d in dirs if d not in excludes_dirs]
            for f in files:
                if f in excludes_dirs:
                    continue
                # 跳过排除后缀
                if any(f.endswith(suf) for suf in excludes_suffixes):
                    continue
                full = Path(root) / f
                rel = full.relative_to(PROJECT_LOCAL_ROOT)
                # 跳过大文件（>2MB）
                try:
                    if full.stat().st_size > 2 * 1024 * 1024:
                        continue
                except OSError:
                    continue
                zf.write(full, rel)

        zf.close()
        size_mb = len(zip_buf.getvalue()) / 1024 / 1024
        print(f"打包完成: {size_mb:.1f} MB")

        # 2. 上传 zip
        print("上传中...")
        sftp = ssh.open_sftp()
        remote_zip = f"/tmp/proj_deploy.zip"
        with sftp.file(remote_zip, "wb") as f:
            f.write(zip_buf.getvalue())
        print(f"已上传到 {remote_zip}")

        # 3. 远程解压（用 python，避免缺 unzip）
        print("远程解压中...")
        run_remote_safe(
            ssh,
            f"mkdir -p {REMOTE_APP_DIR} && "
            f"python3 -c \""
            f"import zipfile; zipfile.ZipFile('{remote_zip}').extractall('{REMOTE_APP_DIR}')"
            f"\" && rm {remote_zip} "
            f"&& echo '解压完成' && ls {REMOTE_APP_DIR}"
        )
        sftp.close()
    finally:
        ssh.close()


def run_remote_safe(ssh, cmd, timeout=120):
    """在已建立的 ssh 连接上执行命令。"""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out, end="")
    if err:
        print(f"[stderr] {err}", end="")
    return stdout.channel.recv_exit_status()


def write_env():
    """在服务器上写入 .env 文件。"""
    print("===== 写入 .env =====")
    env_content = """DB_PASSWORD=123456
DEEPSEEK_API_KEY=sk-883b52eef3df4a7f873b32866f5d2e96
DASHSCOPE_API_KEY=sk-1723d63c8020479ebff6db95d767ee9a
"""
    # 转义单引号
    safe = env_content.replace("'", "'\\''")
    run_remote(
        f"cd {REMOTE_APP_DIR} && cat > .env <<'ENVEOF'\n{env_content}ENVEOF\n"
        f"echo '已写入:' && cat .env"
    )


def build():
    print("===== 构建 Docker 镜像 =====")
    run_remote(
        f"cd {REMOTE_APP_DIR} && DOCKER_BUILDKIT=0 docker compose build --no-cache 2>&1",
        timeout=900,
    )


def up():
    print("===== 启动服务 =====")
    run_remote(
        f"cd {REMOTE_APP_DIR} && docker compose down 2>&1 || true; "
        f"docker compose up -d 2>&1 && sleep 5 && docker compose ps",
        timeout=120,
    )


def init_db():
    print("===== 初始化数据库 =====")
    run_remote(
        f"sleep 10 && cd {REMOTE_APP_DIR} && "
        "docker compose exec -T backend python scripts/init_db.py 2>&1",
        timeout=120,
    )


def init_agents():
    print("===== 初始化内置智能体 =====")
    run_remote(
        f"cd {REMOTE_APP_DIR} && docker compose exec -T backend python -c \""
        "import httpx; r = httpx.post('http://localhost:8000/api/agents/init-builtin'); print(r.json())"
        "\" 2>&1",
        timeout=60,
    )


def logs():
    print("===== 查看日志 =====")
    run_remote(f"cd {REMOTE_APP_DIR} && docker compose logs --tail=80", timeout=30)


def status():
    print("===== 服务状态 =====")
    run_remote(
        f"cd {REMOTE_APP_DIR} && docker compose ps && "
        "echo '--- 端口监听 ---'; sudo ss -tlnp | grep -E ':(80|8000|5433)' 2>&1"
    )


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "probe"
    funcs = {
        "probe": probe,
        "upload": upload,
        "env": write_env,
        "build": build,
        "up": up,
        "init-db": init_db,
        "init-agents": init_agents,
        "logs": logs,
        "status": status,
    }
    if action not in funcs:
        print(f"未知动作: {action}. 可选: {list(funcs.keys())}")
        sys.exit(1)
    funcs[action]()
