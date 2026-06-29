from telegram import Update
from telegram.ext import ContextTypes
from src.db.models import User
from src.db.database import AsyncSessionLocal


async def set_voice_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Сначала пройди регистрацию — /start")
            return
        user.format = "voice"
        await session.commit()
    await update.message.reply_text(
        "🎤 Голосовой режим включён.\n"
        "Отправляй голосовые или текстовые сообщения — отвечу голосом.\n\n"
        "Вернуться к тексту: /text"
    )


async def set_text_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Сначала пройди регистрацию — /start")
            return
        user.format = "text"
        await session.commit()
    await update.message.reply_text(
        "💬 Текстовый режим включён.\n\n"
        "Переключиться на голос: /voice"
    )
