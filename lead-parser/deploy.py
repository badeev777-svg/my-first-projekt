#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deploy lead-parser to VPS via SSH + Docker."""
import paramiko
import os

HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"
APP_DIR = "/root/lead-parser"

def run_ssh(client, cmd):
    """Run SSH command."""
    print(f"[*] {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err and "WARNING" not in err:
        print(f"[!] {err}")
    return out

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("[*] Connecting to server...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    # Upload files via SFTP
    print("\n[*] Uploading files...")
    sftp = client.open_sftp()
    sftp.chdir(APP_DIR)

    # Upload app directory
    for root, dirs, files in os.walk("app"):
        for d in dirs:
            try:
                sftp.mkdir(f"app/{d}")
            except:
                pass
        for f in files:
            if f.endswith('.py'):
                local_path = os.path.join(root, f)
                remote_path = f"{APP_DIR}/{root}/{f}".replace("\\", "/")
                print(f"  Uploading {local_path}...")
                sftp.put(local_path, remote_path)

    # Upload main files
    sftp.put("main.py", f"{APP_DIR}/main.py")
    sftp.put("pyproject.toml", f"{APP_DIR}/pyproject.toml")

    sftp.close()

    # Restart container
    print("\n[*] Restarting Docker container...")
    run_ssh(client, "docker stop lead-parser-app || true")
    run_ssh(client, "docker rm lead-parser-app || true")
    run_ssh(client, f"cd {APP_DIR} && docker build -t lead-parser . 2>&1 | tail -5")
    run_ssh(client, f"cd {APP_DIR} && docker run -d --name lead-parser-app -p 8000:8000 --env-file .env.local -v {APP_DIR}/data:/app/data lead-parser")

    print("\n[OK] Deployment complete!")
    print("[*] App will be available at http://155.212.208.194:8000/leads/")

    client.close()

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
