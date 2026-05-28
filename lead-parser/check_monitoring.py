#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check monitoring status: container health and lead counts."""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
import paramiko
import json
from datetime import datetime, timedelta

HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"

def run_ssh_command(client, command):
    """Run SSH command and return output."""
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("[*] Connecting to server...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    # 1. Check container status
    print("\n" + "="*50)
    print("[1] CONTAINER STATUS")
    print("="*50)
    out, err = run_ssh_command(client, "docker ps | grep lead-parser-app")
    if out:
        lines = out.split('\n')
        for line in lines:
            if line:
                print(f"[OK] {line}")
    else:
        print("[FAIL] Container not running!")
        print(err)

    # 2. Check recent logs
    print("\n" + "="*50)
    print("[2] DOCKER LOGS (last 10 lines)")
    print("="*50)
    out, err = run_ssh_command(client, "docker logs lead-parser-app --tail=30 2>&1")
    if out:
        for line in out.split('\n')[-10:]:
            if line:
                print(f"  {line}")

    # 3. Check lead database counts
    print("\n" + "="*50)
    print("[3] LEADS IN DATABASE")
    print("="*50)

    # Check if we can query the database
    db_check = """
    docker exec lead-parser-app psql -U postgres -d lead_parser -c \
    "SELECT source, COUNT(*) as count FROM leads GROUP BY source ORDER BY count DESC;" 2>&1
    """
    out, err = run_ssh_command(client, db_check)
    if "source" in out:
        print(out)
    else:
        # Try alternative: check sqlite if using that
        sqlite_check = "docker exec lead-parser-app ls -la /app/data/ 2>&1"
        out, err = run_ssh_command(client, sqlite_check)
        if "No such file" not in out:
            print("[DIR] Data directory:", out)

    # 4. Check process list
    print("\n" + "="*50)
    print("[4] RUNNING PROCESSES")
    print("="*50)
    out, err = run_ssh_command(client, "docker top lead-parser-app 2>&1")
    if "python" in out:
        for line in out.split('\n')[1:3]:
            if line.strip():
                print(f"  {line}")

    # 5. Check monitoring script health
    print("\n" + "="*50)
    print("[5] TELEGRAM MONITORING")
    print("="*50)

    monitor_check = """
    docker exec lead-parser-app python3 -c \
    "from app.monitors.telegram_monitor import TelegramMonitor; print('✅ Module imports OK')" 2>&1
    """
    out, err = run_ssh_command(client, monitor_check)
    print(out if out else err)

    client.close()
    print("\n[DONE] Monitoring check complete!")

except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
