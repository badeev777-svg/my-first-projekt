from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.models import Dialog, User
from src.db.database import AsyncSessionLocal
from src.services.claude import get_claude_response, get_initial_response
from src.services.limits import check_message_limit, increment_message_count, get_limit_warning_message
from src.prompts import system_prompts


async def new_dialog_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show scenario selection for new dialogue."""
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)

    if not user:
        await update.message.reply_text(
            "You need to register first! Use /start"
        )
        return

    if user.audience == "students":
        keyboard = [
            [InlineKeyboardButton("Экзамены", callback_data="scenario_exams"),
             InlineKeyboardButton("Жизнь в общежитии", callback_data="scenario_dorm_life")],
            [InlineKeyboardButton("Клубы и досуг", callback_data="scenario_student_clubs"),
             InlineKeyboardButton("Отношения", callback_data="scenario_dating")],
            [InlineKeyboardButton("Спорт", callback_data="scenario_sports"),
             InlineKeyboardButton("Здоровье", callback_data="scenario_health_lifestyle")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("Собеседование", callback_data="scenario_job_interview"),
             InlineKeyboardButton("Деловая встреча", callback_data="scenario_business_meeting")],
            [InlineKeyboardButton("Семья", callback_data="scenario_family_time"),
             InlineKeyboardButton("Путешествия", callback_data="scenario_travel")],
            [InlineKeyboardButton("Светская беседа", callback_data="scenario_small_talk"),
             InlineKeyboardButton("Карьерный рост", callback_data="scenario_career_growth")],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери сценарий:", reply_markup=reply_markup)


async def scenario_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create new dialog for selected scenario and generate opening."""
    query = update.callback_query
    await query.answer()

    scenario = query.data.split("_", 1)[1]
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await query.edit_message_text("Error: User not found.")
            return

        dialog = Dialog(
            user_id=user_id,
            scenario=scenario,
            level=user.level,
            is_active=True
        )
        session.add(dialog)
        await session.commit()

        system_prompt = system_prompts.get_system_prompt(user.audience, scenario, user.level)
        opener = system_prompts.get_scenario_opener(user.audience, scenario)

        response = await get_initial_response(system_prompt, opener)

        dialog.messages = [
            {"role": "assistant", "content": response}
        ]
        await session.commit()

    await query.edit_message_text(
        f"📚 Scenario: {scenario.replace('_', ' ').title()}\n"
        f"Level: {user.level}\n\n{response}"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming user message: check limit, call Claude, save to dialog."""
    user_id = update.effective_user.id
    user_message = update.message.text

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await update.message.reply_text("Please /start first!")
            return

        is_allowed, remaining = await check_message_limit(session, user_id)
        if not is_allowed:
            await update.message.reply_text(get_limit_warning_message(remaining))
            return

        stmt = select(Dialog).where(
            and_(Dialog.user_id == user_id, Dialog.is_active == True)
        ).order_by(Dialog.created_at.desc())
        active_dialog = await session.scalar(stmt)

        if not active_dialog:
            await update.message.reply_text(
                "No active dialog! Use /new to start one."
            )
            return

        system_prompt = system_prompts.get_system_prompt(user.audience, active_dialog.scenario, user.level)

        response = await get_claude_response(
            system_prompt=system_prompt,
            history=active_dialog.messages,
            user_message=user_message,
            max_tokens=200
        )

        active_dialog.messages.append({"role": "user", "content": user_message})
        active_dialog.messages.append({"role": "assistant", "content": response})

        await increment_message_count(session, user_id)
        await session.commit()

        await update.message.reply_text(response)


async def end_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark active dialog as inactive."""
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        stmt = select(Dialog).where(
            and_(Dialog.user_id == user_id, Dialog.is_active == True)
        )
        active_dialog = await session.scalar(stmt)

        if active_dialog:
            active_dialog.is_active = False
            await session.commit()
            await update.message.reply_text("Dialog ended. Use /new to start another!")
        else:
            await update.message.reply_text("No active dialog.")


def get_dialog_handlers():
    return []
