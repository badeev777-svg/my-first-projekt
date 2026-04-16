# ============================================================
# services/bot_manager.py — логика подключения бота мастера
# ============================================================
# Метафора: это «стойка регистрации» платформы.
# Мастер приходит с токеном, мы проверяем его паспорт (getMe),
# выдаём ему ключи (slug, webhook) и записываем в базу.

import hashlib
import re
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select

from config import settings
from database import AsyncSessionLocal
from models.master import Master, MasterSettings
from services.crypto import encrypt_token


def hash_token(token: str) -> str:
    """SHA-256 хеш сырого токена — используется как ключ роутинга вебхуков."""
    return hashlib.sha256(token.encode()).hexdigest()


def make_slug(bot_username: str) -> str:
    """
    Превращает username бота в slug страницы мастера.
    @beauty_masterbot → beauty_master
    @nailsbot         → nails
    """
    clean = bot_username.lower().lstrip("@")
    slug = re.sub(r"[_-]?bot$", "", clean)
    return slug if len(slug) >= 2 else clean


async def validate_bot_token(token: str) -> dict | None:
    """
    Вызывает Telegram getMe. Возвращает dict с info бота или None.
    Метафора: проверяем, что токен — настоящий ключ, а не бумажка.
    """
    try:
        async with httpx.AsyncClient(verify=False, timeout=8) as client:
            r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = r.json()
            if data.get("ok"):
                return data["result"]
    except Exception:
        pass
    return None


async def set_bot_webhook(token: str, token_hash: str) -> bool:
    """
    Устанавливает вебхук на наш сервер для бота мастера.
    URL: {API_BASE_URL}/v1/webhook/{token_hash}
    В dev режиме (localhost) Telegram не сможет достучаться — это нормально.
    """
    webhook_url = f"{settings.api_base_url}/v1/webhook/{token_hash}"
    try:
        async with httpx.AsyncClient(verify=False, timeout=8) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": webhook_url},
            )
            return r.json().get("ok", False)
    except Exception:
        return False


async def connect_master(
    telegram_user_id: int,
    token: str,
) -> tuple[str, dict]:
    """
    Главная функция онбординга мастера.

    Возвращает (статус, данные):
      "already_connected" — этот токен уже в системе
      "user_has_bot"      — у этого Telegram-пользователя уже есть бот
      "invalid_token"     — токен не принят Telegram (getMe вернул ошибку)
      "success"           — успешно, данные: slug, bot_username, webhook_ok
    """
    token_hash = hash_token(token)

    # Шаг 1: быстрые проверки в БД (короткие транзакции)
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Master).where(Master.bot_token_hash == token_hash)
        )
        if res.scalar_one_or_none():
            return "already_connected", {}

        res = await db.execute(
            select(Master).where(Master.telegram_user_id == telegram_user_id)
        )
        if res.scalar_one_or_none():
            return "user_has_bot", {}

    # Шаг 2: проверяем токен через Telegram API (вне DB-сессии)
    bot_info = await validate_bot_token(token)
    if not bot_info:
        return "invalid_token", {}

    bot_username = bot_info["username"]
    bot_name = bot_info.get("first_name", bot_username)

    # Шаг 3: создаём запись мастера (новая короткая транзакция)
    async with AsyncSessionLocal() as db:
        # Генерируем slug. Если занят — добавляем цифру (beauty, beauty2, beauty3...)
        slug = make_slug(bot_username)
        base_slug = slug
        counter = 1
        while True:
            res = await db.execute(select(Master).where(Master.slug == slug))
            if not res.scalar_one_or_none():
                break
            slug = f"{base_slug}{counter}"
            counter += 1

        # Шифруем токен перед сохранением в БД
        encrypted_token = encrypt_token(token)

        # Создаём запись мастера
        master = Master(
            telegram_user_id=telegram_user_id,
            bot_token=encrypted_token,
            bot_token_hash=token_hash,
            bot_username=bot_username,
            slug=slug,
            name=bot_name,
        )
        db.add(master)
        await db.flush()  # нужно, чтобы получить master.id для MasterSettings

        # Настройки по умолчанию
        db.add(MasterSettings(master_id=master.id))

        await db.commit()

    # Устанавливаем вебхук (делаем после commit, чтобы мастер точно был в БД)
    webhook_ok = await set_bot_webhook(token, token_hash)

    # Записываем время установки вебхука
    if webhook_ok:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Master).where(Master.bot_token_hash == token_hash)
            )
            master = res.scalar_one_or_none()
            if master:
                master.webhook_set_at = datetime.now(timezone.utc)
                await db.commit()

    return "success", {
        "slug": slug,
        "bot_username": bot_username,
        "webhook_ok": webhook_ok,
    }


async def activate_subscription(master_id: int, days: int = 30) -> bool:
    """Активирует подписку мастера на N дней. Используется из admin-команды /activate."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Master).where(Master.id == master_id))
        master = res.scalar_one_or_none()
        if not master:
            return False
        master.subscription_status = "active"
        master.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        master.services_limit = 999
        await db.commit()
    return True


async def block_master(master_id: int) -> bool:
    """Блокирует мастера. Используется из admin-команды /block."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Master).where(Master.id == master_id))
        master = res.scalar_one_or_none()
        if not master:
            return False
        master.is_active = False
        await db.commit()
    return True
