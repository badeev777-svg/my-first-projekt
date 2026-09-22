from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.bot.auth import is_authorized
from app.config import Settings
from app.skill_hunter.hunter import run as run_skill_hunter


async def cmd_find_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return

    if not settings.skill_hunter_niches:
        await update.message.reply_text(
            "Список ниш пуст -- задайте SKILL_HUNTER_NICHES в .env"
        )
        return

    await update.message.reply_text("Ищу новые скиллы, это займёт немного времени...")

    async def send_message(text: str) -> None:
        await context.bot.send_message(chat_id=settings.skill_hunter_chat_id, text=text)

    await run_skill_hunter(
        settings.skill_hunter_niches, settings.skill_hunter_history_path, send_message
    )


def register(app: Application) -> None:
    app.add_handler(CommandHandler("find_skills", cmd_find_skills))
