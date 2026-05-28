#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import sys
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import paramiko
import time

HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"
REMOTE_PATH = "/root/lead-parser"

def execute_cmd(client, cmd):
    print(f"  → {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if error:
        print(f"  ⚠️  {error[:300]}")
    if output:
        print(f"  ✓ {output[:150]}")
    return output, error

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Подключаюсь к {HOST}...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    print("✓ Подключение успешно!\n")

    print("Обновляю pyproject.toml...")
    # Копируем обновленный pyproject.toml на сервер
    sftp = client.open_sftp()
    sftp.put("C:\\Users\\User\\OneDrive\\Документы\\Projekt\\my-first-projekt\\lead-parser\\pyproject.toml",
             f"{REMOTE_PATH}/pyproject.toml")
    sftp.close()
    print("✓ Файл загружен\n")

    print("Удаляю старый контейнер...")
    execute_cmd(client, "docker rm -f lead-parser-app")

    print("\nПересобираю Docker образ...")
    execute_cmd(client, f"cd {REMOTE_PATH} && docker build -t lead-parser .")

    print("\nЗапускаю новый контейнер...")
    execute_cmd(client, f"docker run -d -p 8000:8000 --env-file {REMOTE_PATH}/.env.local --name lead-parser-app lead-parser")

    print("\nЛоги контейнера:")
    time.sleep(2)
    execute_cmd(client, "docker logs lead-parser-app | head -20")

    print("\n✅ Готово!")
    print(f"Открыть: http://{HOST}:8000/leads/")

    client.close()
except Exception as e:
    print(f"Ошибка: {e}")
    sys.exit(1)
