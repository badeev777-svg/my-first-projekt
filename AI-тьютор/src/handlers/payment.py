from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
from src.db.models import User
from src.db.database import AsyncSessionLocal
from src.services.payment import activate_premium, complete_payment
from src.config import Config


async def start_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Сначала пройди регистрацию — /start")
            return

    text = (
        f"💎 *Premium подписка*\n\n"
        f"Безлимитные сообщения в день\n\n"
        f"Цена: *{Config.PREMIUM_STARS_PRICE} ⭐ Telegram Stars* / 30 дней\n\n"
        f"Используй /buy\\_monthly для оплаты"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def buy_monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Сначала пройди регистрацию — /start")
            return

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="SpeakBuddy Premium",
        description="Безлимитные сообщения на 30 дней",
        payload=f"premium_monthly_{user_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("30 дней Premium", Config.PREMIUM_STARS_PRICE)],
    )


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment

    async with AsyncSessionLocal() as session:
        await complete_payment(
            session,
            user_id=user_id,
            telegram_payment_charge_id=payment_info.telegram_payment_charge_id,
            amount=payment_info.total_amount,
        )
        await activate_premium(session, user_id, days=30)

    await update.message.reply_text(
        "✅ Оплата прошла! Premium активирован на 30 дней.\n\n"
        "Напиши /new чтобы начать практику без ограничений."
    )
