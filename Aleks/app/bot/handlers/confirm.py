# app/bot/handlers/confirm.py
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from app.confirmation import ConfirmationBridge


async def on_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    correlation_id, _, decision = query.data.partition(":")
    bridge: ConfirmationBridge = context.bot_data["confirmation_bridge"]
    bridge.resolve(correlation_id, decision == "yes")
    await query.edit_message_reply_markup(reply_markup=None)


def register(app: Application) -> None:
    app.add_handler(
        CallbackQueryHandler(on_confirmation_callback, pattern=r"^[^:]+:(yes|no)$")
    )
