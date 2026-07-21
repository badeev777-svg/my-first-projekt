# app/bot/handlers/confirm.py
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from app.config import Settings
from app.confirmation import ConfirmationBridge


def _is_authorized(update: Update, allowed_user_id: int) -> bool:
    user = update.effective_user
    return user is not None and user.id == allowed_user_id


async def on_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    settings: Settings = context.bot_data["settings"]
    if not _is_authorized(update, settings.allowed_user_id):
        await query.answer()
        return

    await query.answer()
    correlation_id, _, decision = query.data.partition(":")
    bridge: ConfirmationBridge = context.bot_data["confirmation_bridge"]
    bridge.resolve(correlation_id, decision == "yes")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


def register(app: Application) -> None:
    app.add_handler(
        CallbackQueryHandler(on_confirmation_callback, pattern=r"^[^:]+:(yes|no)$")
    )
