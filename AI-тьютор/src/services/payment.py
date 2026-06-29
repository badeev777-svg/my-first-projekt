from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Payment, Subscription, User


async def create_payment(
    session: AsyncSession,
    user_id: int,
    amount: int,
    external_id: str = None,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency="XTR",
        status="pending",
        method="stars",
        external_id=external_id,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def complete_payment(
    session: AsyncSession,
    user_id: int,
    telegram_payment_charge_id: str,
    amount: int,
) -> bool:
    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency="XTR",
        status="completed",
        method="stars",
        external_id=telegram_payment_charge_id,
    )
    session.add(payment)
    await session.commit()
    return True


async def activate_premium(
    session: AsyncSession,
    user_id: int,
    days: int = 30,
) -> bool:
    user = await session.get(User, user_id)
    if not user:
        return False

    now = datetime.utcnow()
    # Extend from current premium_until if still active
    base = user.premium_until if user.premium_until and user.premium_until > now else now
    user.premium_until = base + timedelta(days=days)

    subscription = Subscription(
        user_id=user_id,
        start_date=now.date(),
        end_date=(now + timedelta(days=days)).date(),
        plan="monthly",
    )
    session.add(subscription)
    await session.commit()
    return True
