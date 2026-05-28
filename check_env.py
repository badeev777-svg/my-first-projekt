#!/usr/bin/env python3
import paramiko
import sys

HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {HOST}...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    sftp = client.open_sftp()

    # Check if .env.local exists
    try:
        with sftp.file("/root/lead-parser/.env.local", "r") as f:
            content = f.read().decode()
        print("Current .env.local on server:")
        print(content)
    except IOError as e:
        print(f".env.local not found on server: {e}")

    sftp.close()
    client.close()

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
