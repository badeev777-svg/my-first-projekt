#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
import paramiko

HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"

def run_ssh_cmd(client, cmd):
    """Run SSH command and return output."""
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode().strip()

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("[*] Connecting to server...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    print("\n" + "="*50)
    print("[LEADS BY SOURCE]")
    print("="*50)

    cmd = """docker exec lead-parser-app sqlite3 /app/data/leads.db "SELECT source, COUNT(*) as count FROM leads GROUP BY source ORDER BY count DESC;" """
    output = run_ssh_cmd(client, cmd)
    for line in output.split('\n'):
        if line:
            parts = line.split('|')
            if len(parts) == 2:
                print(f"  {parts[0]}: {parts[1]} leads")

    print("\n" + "="*50)
    print("[LATEST 5 LEADS]")
    print("="*50)

    cmd = """docker exec lead-parser-app sqlite3 /app/data/leads.db "SELECT id, source, title, budget, relevance_score, processed, created_at FROM leads ORDER BY created_at DESC LIMIT 5;" """
    output = run_ssh_cmd(client, cmd)
    for line in output.split('\n'):
        if line and '|' in line:
            parts = line.split('|')
            lead_id, source, title, budget, score, processed, created = parts
            status = "[OK]" if processed == '1' else "[PENDING]"
            print(f"\n  {status} #{lead_id}: {source}")
            print(f"    Title: {title[:60] if title else 'N/A'}...")
            print(f"    Budget: {budget}, Score: {score}")
            print(f"    Created: {created}")

    print("\n" + "="*50)
    print("[TELEGRAM LEADS COUNT]")
    print("="*50)

    cmd = """docker exec lead-parser-app sqlite3 /app/data/leads.db "SELECT COUNT(*) FROM leads WHERE source = 'telegram';" """
    output = run_ssh_cmd(client, cmd)
    print(f"  Total: {output}")

    print("\n" + "="*50)
    print("[TELEGRAM SESSION]")
    print("="*50)

    cmd = """docker exec lead-parser-app ls -la /app/data/ | grep session"""
    output = run_ssh_cmd(client, cmd)
    if output:
        print(f"  [OK] Session file exists:\n    {output}")
    else:
        print("  [MISSING] No Telegram session (not authorized yet)")

    client.close()
    print("\n[DONE] Database check complete!")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
