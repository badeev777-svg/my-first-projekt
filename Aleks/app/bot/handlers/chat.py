# app/bot/handlers/chat.py
import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from app.agent_runner import run_turn
from app.config import Settings
from app.confirmation import ConfirmationBridge
from app.state import StateStore

log = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


def _describe_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "Bash":
        return f"Bash: {tool_input.get('command', '')}"
    if tool_name in ("Write", "Edit"):
        return f"{tool_name}: {tool_input.get('file_path', '')}"
    return f"{tool_name}: {tool_input}"


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    user = update.effective_user
    if user is None or update.message is None or user.id != settings.allowed_user_id:
        return

    state: StateStore = context.bot_data["state"]
    project = await state.get_active_project(user.id)
    if project is None:
        await update.message.reply_text("Сначала выбери проект: /projects")
        return

    locks: dict[str, asyncio.Lock] = context.bot_data["project_locks"]
    lock = locks.setdefault(project, asyncio.Lock())
    if lock.locked():
        await update.message.reply_text(
            f"Ещё работаю над предыдущим запросом для {project}, подожди."
        )
        return

    async with lock:
        bridge: ConfirmationBridge = context.bot_data["confirmation_bridge"]
        chat_id = update.effective_chat.id

        async def send_confirmation_prompt(
            correlation_id: str, tool_name: str, tool_input: dict
        ) -> None:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Разрешить", callback_data=f"{correlation_id}:yes"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"{correlation_id}:no"),
                    ]
                ]
            )
            text = f"Подтверди действие:\n{_describe_tool(tool_name, tool_input)}"
            if len(text) > TELEGRAM_MESSAGE_LIMIT:
                suffix = "...(обрезано)"
                text = text[: TELEGRAM_MESSAGE_LIMIT - len(suffix)] + suffix
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
            )

        async def on_text(text: str) -> None:
            for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
                await context.bot.send_message(
                    chat_id=chat_id, text=text[i : i + TELEGRAM_MESSAGE_LIMIT]
                )

        session_id = await state.get_session_id(project)
        project_path = settings.projects[project]

        try:
            new_session_id = await run_turn(
                prompt=update.message.text,
                project_path=project_path,
                session_id=session_id,
                confirmation_bridge=bridge,
                send_confirmation_prompt=send_confirmation_prompt,
                on_text=on_text,
            )
        except Exception:
            log.exception("agent turn failed for project %s", project)
            await update.message.reply_text("Не получилось выполнить запрос, попробуй позже.")
            return

        if new_session_id:
            await state.set_session_id(project, new_session_id)


def register(app: Application) -> None:
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
