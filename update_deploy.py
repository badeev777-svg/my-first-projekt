#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import paramiko
import time
from pathlib import Path

HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"
REMOTE_PATH = "/root/lead-parser"
LOCAL_PATH = "C:\\Users\\User\\OneDrive\\Документы\\Projekt\\my-first-projekt\\lead-parser"

def execute_cmd(client, cmd):
    print(f"  → {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if error:
        print(f"  Warning: {error[:200]}")
    if output:
        print(f"  {output[:100].strip()}")
    return output, error

def upload_file(sftp, local_path, remote_path):
    sftp.put(local_path, remote_path)

def upload_tree(sftp, local_dir, remote_dir, exclude=None):
    if exclude is None:
        exclude = {'.venv', '__pycache__', '.pytest_cache', '.git', '.env.local'}

    for item in Path(local_dir).iterdir():
        if item.name in exclude:
            continue

        remote_item = f"{remote_dir}/{item.name}"

        if item.is_file():
            print(f"    {item.name}", end=" ")
            upload_file(sftp, str(item), remote_item)
            print("ok")
        elif item.is_dir():
            print(f"    {item.name}/")
            try:
                sftp.mkdir(remote_item)
            except IOError:
                pass
            upload_tree(sftp, str(item), remote_item, exclude)

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    print("Connection successful!\n")

    sftp = client.open_sftp()

    print("Uploading application files...")
    upload_tree(sftp, f"{LOCAL_PATH}\\app", f"{REMOTE_PATH}/app")
    print("  app/ uploaded\n")

    print("Uploading main.py...")
    upload_file(sftp, f"{LOCAL_PATH}\\main.py", f"{REMOTE_PATH}/main.py")
    print("  main.py uploaded\n")

    print("Uploading pyproject.toml...")
    upload_file(sftp, f"{LOCAL_PATH}\\pyproject.toml", f"{REMOTE_PATH}/pyproject.toml")
    print("  pyproject.toml uploaded\n")

    sftp.close()

    print("Stopping old container...")
    execute_cmd(client, "docker rm -f lead-parser-app")

    print("\nBuilding Docker image...")
    execute_cmd(client, f"cd {REMOTE_PATH} && docker build -t lead-parser .")

    print("\nStarting new container...")
    execute_cmd(client, f"docker run -d -p 8000:8000 --env-file {REMOTE_PATH}/.env.local --name lead-parser-app lead-parser")

    print("\nContainer logs:")
    time.sleep(2)
    execute_cmd(client, "docker logs lead-parser-app | head -20")

    print("\nDone!")
    print(f"Open: http://{HOST}:8000/leads/")
    print(f"Demo: http://{HOST}:8000/leads/demo")

    client.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
