"""快速测试远程命令。"""
import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456")

cmd = sys.argv[1] if len(sys.argv) > 1 else "echo hi"
print(f">>> {cmd}")
i, o, e = ssh.exec_command(cmd, timeout=int(sys.argv[2]) if len(sys.argv) > 2 else 120)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f"[stderr] {err}")
ssh.close()
