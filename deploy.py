#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy lead-parser to Beget VPS via SSH
"""
import os
import sys
import io
from pathlib import Path

# Fix encoding on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import paramiko
except ImportError:
    print("❌ paramiko не установлен. Установи: pip install paramiko")
    sys.exit(1)

# Конфигурация
HOST = "155.212.208.194"
USER = "root"
PASSWORD = "j84sYBm*XODl"
REMOTE_PATH = "/root/lead-parser"

# Локальная папка проекта
LOCAL_PROJECT = Path(__file__).parent / "lead-parser"

def connect_ssh():
    """Подключиться по SSH"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"🔌 Подключаюсь к {HOST}...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    return client

def execute_cmd(client, cmd):
    """Выполнить команду на сервере"""
    print(f"  → {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if error:
        print(f"  ⚠️  {error}")
    if output:
        print(f"  ✓ {output[:200]}")  # Первые 200 символов
    return output, error

def upload_files(client):
    """Загрузить файлы на сервер"""
    sftp = client.open_sftp()

    print(f"📁 Создаю директорию {REMOTE_PATH}...")
    try:
        sftp.mkdir(REMOTE_PATH)
    except IOError:
        pass  # Папка уже существует

    print(f"📤 Загружаю файлы...")

    exclude = {'.venv', '__pycache__', '.pytest_cache', 'data', '.git', '.env'}

    for root, dirs, files in os.walk(LOCAL_PROJECT):
        # Пропустить исключённые папки
        dirs[:] = [d for d in dirs if d not in exclude]

        for file in files:
            local_file = Path(root) / file
            rel_path = local_file.relative_to(LOCAL_PROJECT)
            remote_file = f"{REMOTE_PATH}/{rel_path}".replace("\\", "/")

            # Создать удалённую папку если нужно
            remote_dir = remote_file.rsplit('/', 1)[0]
            try:
                sftp.stat(remote_dir)
            except IOError:
                execute_cmd(client, f"mkdir -p {remote_dir}")

            # Загрузить файл
            print(f"  {rel_path}", end=" ... ")
            sftp.put(str(local_file), remote_file)
            print("✓")

    sftp.close()
    print("✅ Файлы загружены!")

def deploy(client):
    """Развернуть проект"""
    print("\n🐳 Проверяю Docker...")
    execute_cmd(client, "docker --version")

    print("\n🔨 Собираю Docker образ (это может занять время)...")
    _, err = execute_cmd(client, f"cd {REMOTE_PATH} && docker build -t lead-parser .")
    if err and "error" in err.lower():
        print(f"❌ Ошибка при сборке образа: {err}")
        return False

    print("\n🗑️  Удаляю старый контейнер...")
    execute_cmd(client, "docker rm -f lead-parser-app 2>/dev/null || true")

    print("\n🚀 Запускаю контейнер...")
    _, err = execute_cmd(client,
        f"docker run -d -p 8000:8000 --env-file {REMOTE_PATH}/.env.local --name lead-parser-app lead-parser"
    )

    print("\n📋 Логи контейнера:")
    time.sleep(2)
    execute_cmd(client, "docker logs lead-parser-app")

    print("\n✅ Деплой завершён!")
    print(f"📍 Открыть в браузере: http://{HOST}:8000/leads/")
    return True

def main():
    try:
        client = connect_ssh()
        print("✅ Подключение успешно!\n")

        upload_files(client)
        deploy(client)

        client.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import time
    main()
