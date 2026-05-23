from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from src.db.models import User, Dialog
from src.db.database import AsyncSessionLocal


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Please /start to register first!")
            return

        stmt = select(func.count(Dialog.id)).where(Dialog.user_id == user_id)
        dialog_count = await session.scalar(stmt)

        total_messages = 0
        stmt = select(Dialog).where(Dialog.user_id == user_id)
        dialogs = await session.scalars(stmt)
        for dialog in dialogs:
            total_messages += len(dialog.messages) // 2

        premium_status = "✅ Active" if user.premium_until else "❌ Free"

        profile_text = f"""
👤 **Your Profile**

Name: {user.first_name}
Age: {user.age or "Not specified"}
Level: {user.level}
Goal: {user.goal}
Joined: {user.created_at.strftime('%d.%m.%Y')}

📊 **Stats**
Dialogs: {dialog_count}
Total messages: {total_messages}
Premium: {premium_status}

💡 Tip: Use /new to start a conversation!
        """
        await update.message.reply_text(profile_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Please /start first!")
            return

        stmt = select(Dialog).where(Dialog.user_id == user_id)
        dialogs = await session.scalars(stmt)

        scenario_stats = {}
        for dialog in dialogs:
            if dialog.scenario not in scenario_stats:
                scenario_stats[dialog.scenario] = 0
            scenario_stats[dialog.scenario] += len(dialog.messages) // 2

        stats_text = "📈 **Detailed Stats**\n\n"
        for scenario, count in scenario_stats.items():
            stats_text += f"{scenario}: {count} messages\n"

        await update.message.reply_text(stats_text)


def get_profile_handlers():
    return []
