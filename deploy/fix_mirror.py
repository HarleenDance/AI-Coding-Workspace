"""修复 Docker 镜像源配置。"""
import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.130.118.128", username="czm", password="czm123456")

# 读取当前配置
i, o, e = ssh.exec_command("cat /etc/docker/daemon.json")
content = o.read().decode()
print("原配置:")
print(content)

config = json.loads(content)

# 只保留阿里云和稳定的源
bad_mirrors = {"https://mirror.iscas.ac.cn", "https://huecker.io", "https://dockerhub.timeweb.cloud", "https://noohub.ru"}
config["registry-mirrors"] = [m for m in config["registry-mirrors"] if m not in bad_mirrors]
new_content = json.dumps(config, indent=4, ensure_ascii=False)
print("新配置:")
print(new_content)

# 写入到临时文件（不需要 sudo）
sftp = ssh.open_sftp()
with sftp.file("/tmp/daemon.json", "w") as f:
    f.write(new_content)
sftp.close()
print("已写入 /tmp/daemon.json")

# 用 sudo cp 覆盖（密码通过 stdin 传给 sudo -S）
print("覆盖 /etc/docker/daemon.json...")
i, o, e = ssh.exec_command("sudo -S cp /tmp/daemon.json /etc/docker/daemon.json && echo COPIED", timeout=30)
i.write("czm123456\n")
i.flush()
print(o.read().decode())
err = e.read().decode()
if err:
    print(f"[stderr] {err}")

# 重启 docker
print("重启 docker...")
i, o, e = ssh.exec_command("sudo -S systemctl restart docker && echo DOCKER_RESTARTED", timeout=60)
i.write("czm123456\n")
i.flush()
print(o.read().decode())
err = e.read().decode()
if err:
    print(f"[stderr] {err}")

# 验证
print("验证新配置:")
i, o, e = ssh.exec_command("cat /etc/docker/daemon.json", timeout=10)
print(o.read().decode())

ssh.close()
