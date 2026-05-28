#!/usr/bin/env python3
"""
Интерактивная авторизация Telegram-сессии для Telethon.
Запусти: python auth_telegram.py [КОД]
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Загружаем переменные из .env.local
load_dotenv(".env.local")

TG_API_ID = int(os.getenv("TG_API_ID") or "0")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_PHONE = os.getenv("TG_PHONE", "")

if not all([TG_API_ID, TG_API_HASH, TG_PHONE]):
    print("[ERROR] Ошибка: не все переменные установлены в .env.local")
    print(f"  TG_API_ID: {TG_API_ID}")
    print(f"  TG_API_HASH: {TG_API_HASH[:20]}..." if TG_API_HASH else "  TG_API_HASH: не установлена")
    print(f"  TG_PHONE: {TG_PHONE}")
    exit(1)

# Убеждаемся, что папка data существует
Path("data").mkdir(exist_ok=True)

SESSION_FILE = "data/tg_session"

async def main():
    code = sys.argv[1] if len(sys.argv) > 1 else None

    print("[AUTH] Телеграм авторизация")
    print(f"[PHONE] Номер: {TG_PHONE}")
    print()

    client = TelegramClient(SESSION_FILE, TG_API_ID, TG_API_HASH)

    try:
        await client.connect()

        if code:
            print(f"[CODE] Используем код: {code}")
            try:
                await client.sign_in(phone=TG_PHONE, code=code)
            except Exception as e:
                print(f"[ERROR] Ошибка с кодом: {e}")
                print("[INFO] Спрашиваю новый код...")
                await client.sign_in(phone=TG_PHONE)
        else:
            print("[INFO] Код не передан. Начинаю авторизацию интерактивно...")
            await client.sign_in(phone=TG_PHONE)

        print("[OK] Авторизация успешна!")
        print(f"[FILE] Файл сессии сохранён: {SESSION_FILE}")
        print()
        print("[READY] Готово к загрузке на сервер.")
        await client.disconnect()
    except SessionPasswordNeededError:
        print("[ERROR] Требуется пароль двухфакторной аутентификации.")
        print("[ERROR] Включите 2FA в Telegram и введите пароль вручную.")
        exit(1)
    except Exception as e:
        print(f"[ERROR] Ошибка авторизации: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
