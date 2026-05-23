from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.models import DailyLimits, User
from src.config import Config


async def check_message_limit(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """Check if user can send a message today.

    Args:
        session: Database session
        user_id: Telegram user ID

    Returns:
        (is_allowed, remaining_messages): is_allowed is True if user can send message,
        remaining_messages is -1 for premium users, or count for free users
    """
    user = await session.get(User, user_id)
    if not user:
        return False, 0

    if user.premium_until and user.premium_until > datetime.utcnow():
        return True, -1

    today = date.today()
    stmt = select(DailyLimits).where(
        and_(DailyLimits.user_id == user_id, DailyLimits.date == today)
    )
    limit_record = await session.scalar(stmt)

    if limit_record is None:
        return True, Config.FREE_DAILY_LIMIT

    remaining = Config.FREE_DAILY_LIMIT - limit_record.message_count
    return remaining > 0, max(remaining, 0)


async def increment_message_count(session: AsyncSession, user_id: int) -> int:
    """Increment daily message count for user.

    Args:
        session: Database session
        user_id: Telegram user ID

    Returns:
        New message count for today
    """
    today = date.today()
    stmt = select(DailyLimits).where(
        and_(DailyLimits.user_id == user_id, DailyLimits.date == today)
    )
    limit_record = await session.scalar(stmt)

    if limit_record is None:
        limit_record = DailyLimits(user_id=user_id, date=today, message_count=1)
        session.add(limit_record)
    else:
        limit_record.message_count += 1

    await session.commit()
    return limit_record.message_count


def get_limit_warning_message(remaining: int) -> str:
    """Get user-friendly message about message limit status.

    Args:
        remaining: Number of messages remaining

    Returns:
        Warning message string
    """
    if remaining <= 0:
        return "❌ You've reached your daily limit (10 messages). Upgrade to Premium for unlimited access!"
    elif remaining == 1:
        return f"⚠️ {remaining} message left today. Upgrade to Premium for unlimited!"
    else:
        return f"⚠️ {remaining} messages left today."
