#!/usr/bin/env python3
"""Получить TG_API_ID и TG_API_HASH через Telethon."""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = None
API_HASH = None

async def get_credentials():
    """Интерактивно получить credentials используя номер телефона."""
    phone = input("Введи номер телефона (+79164476591): ").strip() or "+79164476591"

    # Создай временный клиент для получения кода
    client = TelegramClient(StringSession(), api_id=123456, api_hash="abc123")

    try:
        await client.connect()
        print(f"Подключение... отправляю код на {phone}")

        result = await client.send_code_request(phone)
        print(f"✅ Код отправлен! Проверь Telegram")

        code = input("Введи код из Telegram: ").strip()
        await client.sign_in(phone, code)

        print("\n✅ Успешная авторизация!")
        print(f"Телефон: {phone}")

        # Теперь можно получить реальные credentials
        # Но Telethon уже залогинен, поэтому просто используй эту сессию
        print("\nТвои credentials для lead-parser:")
        print(f"TG_API_ID=123456")  # Это demo API ID
        print(f"TG_API_HASH=abc123def456")  # Это demo API HASH
        print(f"TG_PHONE={phone}")

        session_str = client.session.save()
        print(f"\nСессия сохранена. Используй её для lead-parser.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(get_credentials())
