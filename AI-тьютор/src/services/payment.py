from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import Payment, Subscription, User
from src.config import Config
import requests
import hashlib
from hmac import compare_digest


async def create_payment(
    session: AsyncSession,
    user_id: int,
    amount: int,
    method: str = "star"
) -> dict:
    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency="RUB",
        status="pending",
        method=method
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    return {
        "id": payment.id,
        "user_id": user_id,
        "amount": amount,
        "status": "pending",
        "created_at": payment.created_at.isoformat()
    }


async def update_payment_status(
    session: AsyncSession,
    payment_id: int,
    status: str,
    external_id: str = None
) -> bool:
    payment = await session.get(Payment, payment_id)
    if not payment:
        return False

    payment.status = status
    if external_id:
        payment.external_id = external_id
    payment.updated_at = datetime.utcnow()

    await session.commit()
    return True


async def activate_premium(
    session: AsyncSession,
    user_id: int,
    days: int = 30
) -> bool:
    user = await session.get(User, user_id)
    if not user:
        return False

    user.premium_until = datetime.utcnow() + timedelta(days=days)

    subscription = Subscription(
        user_id=user_id,
        start_date=datetime.utcnow().date(),
        end_date=(datetime.utcnow() + timedelta(days=days)).date(),
        plan="monthly" if days == 30 else "yearly",
    )
    session.add(subscription)
    await session.commit()

    return True


def verify_yukassa_webhook(data: dict, signature: str) -> bool:
    if not Config.YUKASSA_API_KEY:
        return False

    message = f"{data.get('type')}.{data.get('event')}.{data.get('id')}"
    expected_signature = hashlib.sha256(
        f"{message}.{Config.YUKASSA_API_KEY}".encode()
    ).hexdigest()

    return compare_digest(signature, expected_signature)
