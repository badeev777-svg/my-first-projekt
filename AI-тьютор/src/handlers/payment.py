from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User
from src.db.database import AsyncSessionLocal
from src.services.payment import (
    create_payment, activate_premium, verify_yukassa_webhook
)
from src.config import Config
import json


async def start_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Please /start first!")
            return

    text = f"""
💎 **Premium Subscription**

Unlimited daily messages + priority support

**Pricing:**
- Monthly: {Config.PREMIUM_MONTHLY_PRICE} ₽ (~30 days)
- Yearly: {Config.PREMIUM_YEARLY_PRICE} ₽ (~365 days)

Use /buy_monthly or /buy_yearly to purchase
    """
    await update.message.reply_text(text)


async def buy_monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        payment = await create_payment(
            session,
            user_id,
            Config.PREMIUM_MONTHLY_PRICE,
            method="yukassa"
        )

    await update.message.reply_text(
        f"Payment created: {payment['amount']} ₽\n"
        f"Payment ID: {payment['id']}\n\n"
        f"Use your payment method to complete purchase."
    )


async def webhook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = json.loads(update.body) if isinstance(update.body, str) else update.body
        signature = update.headers.get("X-Yandex-Checkout-API-Signature", "")

        if not verify_yukassa_webhook(data, signature):
            return {"status": "invalid"}

        event = data.get("event")
        payment_data = data.get("object", {})

        if event == "payment.succeeded":
            async with AsyncSessionLocal() as session:
                user_id = int(payment_data.get("metadata", {}).get("user_id", 0))
                if user_id:
                    await activate_premium(session, user_id, days=30)

            return {"status": "ok"}

    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}
