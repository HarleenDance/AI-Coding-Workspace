"""测试端口连通性。"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456")

# 服务器内部测试
print("=== 服务器内部测试 8080 ===")
i, o, e = ssh.exec_command("curl -so /dev/null -w '%{http_code}' http://localhost:8080/")
print(f"HTTP status: {o.read().decode()}")

# 检查防火墙
print("\n=== 检查防火墙规则 ===")
i, o, e = ssh.exec_command("sudo -S iptables -L INPUT -n --line-numbers 2>&1")
i.write("czm123456\n")
i.flush()
print(o.read().decode()[:500])

# 检查 ufw
print("\n=== UFW 状态 ===")
i, o, e = ssh.exec_command("sudo -S ufw status 2>&1")
i.write("czm123456\n")
i.flush()
print(o.read().decode()[:300])

# 检查端口监听
print("\n=== 端口监听 ===")
i, o, e = ssh.exec_command("ss -tlnp | grep -E ':(80|8080|8000)'")
print(o.read().decode())

ssh.close()
