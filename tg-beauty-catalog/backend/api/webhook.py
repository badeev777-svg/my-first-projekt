# ============================================================
# api/webhook.py — мультиплексор вебхуков (один URL для всех ботов)
# ============================================================
# POST /v1/webhook/{token_hash}
#
# Как это работает:
#   1. Telegram шлёт update на /v1/webhook/{token_hash}
#   2. По хешу находим мастера в БД
#   3. Расшифровываем токен, создаём Bot-объект для этого мастера
#   4. Передаём update в master_dp — общий диспетчер для всех ботов мастеров
#   5. В каждый хендлер автоматически инжектируется объект master

from aiogram import Bot
from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from bot.master_bot import dp as master_dp
from database import AsyncSessionLocal
from models.master import Master
from services.crypto import decrypt_token

router = APIRouter(tags=["Webhook"])

# Кеш Bot-объектов по master_id.
# Метафора: как открытые телефонные линии — не пересоздаём каждый раз.
_bot_cache: dict[int, Bot] = {}


def _get_bot(master: Master) -> Bot:
    """Возвращает Bot для мастера, создаёт и кеширует если нет."""
    if master.id not in _bot_cache:
        token = decrypt_token(master.bot_token)
        _bot_cache[master.id] = Bot(token=token)
    return _bot_cache[master.id]


@router.post("/webhook/{token_hash}")
async def telegram_webhook(token_hash: str, request: Request):
    """
    Принимает update от Telegram для любого бота мастера.
    Определяет мастера по хешу токена и передаёт update в master_dp.
    """
    update_data = await request.json()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Master).where(
                Master.bot_token_hash == token_hash,
                Master.is_active == True,
            )
        )
        master = result.scalar_one_or_none()

    if not master:
        raise HTTPException(404, "Бот не найден")

    # Передаём update в общий диспетчер мастер-бота.
    # master= автоматически инжектируется в каждый хендлер как параметр.
    bot = _get_bot(master)
    update = Update.model_validate(update_data)
    await master_dp.feed_update(bot, update, master=master)

    return {"ok": True}
