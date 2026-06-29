from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import User
from src.db.database import AsyncSessionLocal

ASK_NAME, ASK_AGE, ASK_AUDIENCE, ASK_GOAL, LEVEL_TEST, TEST_SUMMARY = range(6)

LEVEL_TEST_QUESTIONS = [
    {
        "question": "Yesterday I ___ to school.",
        "options": {"A": "went", "B": "go", "C": "gone", "D": "going"},
        "correct": "A"
    },
    {
        "question": "She has been working here ___ 2019.",
        "options": {"A": "since", "B": "for", "C": "during", "D": "while"},
        "correct": "A"
    },
    {
        "question": "If I had more time, I ___ travel more.",
        "options": {"A": "would", "B": "will", "C": "could", "D": "can"},
        "correct": "A"
    },
    {
        "question": "The report ___ by the manager.",
        "options": {"A": "was written", "B": "wrote", "C": "is writing", "D": "writes"},
        "correct": "A"
    },
    {
        "question": "I'm looking forward to ___ you.",
        "options": {"A": "meeting", "B": "meet", "C": "to meet", "D": "have met"},
        "correct": "A"
    },
    {
        "question": "Which word means 'to procrastinate'?",
        "options": {"A": "hurry up", "B": "delay", "C": "celebrate", "D": "analyze"},
        "correct": "B"
    },
    {
        "question": "Find the error: 'She go to the store every day.'",
        "options": {"A": "No error", "B": "goes", "C": "to", "D": "every"},
        "correct": "B"
    }
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.user_id == user_id)
        existing_user = await session.scalar(stmt)

    if existing_user:
        await update.message.reply_text(
            f"Добро пожаловать, {existing_user.first_name}! 👋\n\n"
            f"Твой уровень: {existing_user.level}\n"
            f"Напиши /new чтобы начать диалог или /profile чтобы увидеть статистику."
        )
        return ConversationHandler.END

    await update.message.reply_text("Привет! Я SpeakBuddy. Как тебя зовут?")
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["first_name"] = update.message.text
    await update.message.reply_text("Сколько тебе лет? (или напиши 'skip')")
    return ASK_AGE


async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    try:
        if text.lower() != "skip":
            context.user_data["age"] = int(text)
        else:
            context.user_data["age"] = None
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число или 'skip'.")
        return ASK_AGE

    keyboard = [
        [InlineKeyboardButton("📚 Студент", callback_data="audience_students")],
        [InlineKeyboardButton("👨‍💼 Взрослый", callback_data="audience_adults")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Ты студент или взрослый?", reply_markup=reply_markup)
    return ASK_AUDIENCE


async def ask_audience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    audience_map = {
        "audience_students": "students",
        "audience_adults": "adults"
    }
    context.user_data["audience"] = audience_map.get(query.data)

    keyboard = [
        [InlineKeyboardButton("📝 Подготовка к экзамену", callback_data="goal_ielts")],
        [InlineKeyboardButton("💼 Собеседование", callback_data="goal_job")],
        [InlineKeyboardButton("🏢 Бизнес", callback_data="goal_business")],
        [InlineKeyboardButton("💬 Просто говорить", callback_data="goal_casual")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Какая твоя основная цель?", reply_markup=reply_markup)
    return ASK_GOAL


async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    goal_map = {
        "goal_ielts": "ielts",
        "goal_job": "job",
        "goal_business": "business",
        "goal_casual": "casual"
    }
    context.user_data["goal"] = goal_map.get(query.data)

    await query.edit_message_text(
        "Отлично! Давайте определим твой уровень. Ответь на 7 вопросов.\n\n"
        f"Вопрос 1: {LEVEL_TEST_QUESTIONS[0]['question']}"
    )

    keyboard = [
        [InlineKeyboardButton("A) " + LEVEL_TEST_QUESTIONS[0]["options"]["A"], callback_data="q0_A"),
         InlineKeyboardButton("B) " + LEVEL_TEST_QUESTIONS[0]["options"]["B"], callback_data="q0_B")],
        [InlineKeyboardButton("C) " + LEVEL_TEST_QUESTIONS[0]["options"]["C"], callback_data="q0_C"),
         InlineKeyboardButton("D) " + LEVEL_TEST_QUESTIONS[0]["options"]["D"], callback_data="q0_D")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выбери один:", reply_markup=reply_markup)

    context.user_data["test_score"] = 0
    context.user_data["current_question"] = 0

    return LEVEL_TEST


async def level_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    answer = query.data.split("_")[1]
    current_q = context.user_data["current_question"]
    correct = LEVEL_TEST_QUESTIONS[current_q]["correct"]

    if answer == correct:
        context.user_data["test_score"] += 1

    current_q += 1

    if current_q >= len(LEVEL_TEST_QUESTIONS):
        return await finish_test(update, context)

    context.user_data["current_question"] = current_q
    q = LEVEL_TEST_QUESTIONS[current_q]

    await query.edit_message_text(
        f"Вопрос {current_q + 1}: {q['question']}"
    )

    keyboard = [
        [InlineKeyboardButton("A) " + q["options"]["A"], callback_data=f"q{current_q}_A"),
         InlineKeyboardButton("B) " + q["options"]["B"], callback_data=f"q{current_q}_B")],
        [InlineKeyboardButton("C) " + q["options"]["C"], callback_data=f"q{current_q}_C"),
         InlineKeyboardButton("D) " + q["options"]["D"], callback_data=f"q{current_q}_D")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выбери один:", reply_markup=reply_markup)

    return LEVEL_TEST


async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    score = context.user_data["test_score"]

    level_map = {
        (0, 1): "A1",
        (2, 3): "A2",
        (4, 5): "B1",
        (5, 6): "B2",
        (6, 7): "C1",
        (7, 7): "C2"
    }

    assigned_level = "A1"
    for (min_score, max_score), level in level_map.items():
        if min_score <= score <= max_score:
            assigned_level = level
            break

    user_id = update.effective_user.id
    try:
        async with AsyncSessionLocal() as session:
            user = User(
                user_id=user_id,
                first_name=context.user_data.get("first_name", "User"),
                age=context.user_data.get("age"),
                level=assigned_level,
                goal=context.user_data.get("goal", "casual"),
                audience=context.user_data.get("audience", "adults"),
                format="text"
            )
            session.add(user)
            await session.commit()

        await update.callback_query.edit_message_text(
            f"🎉 Твой уровень: {assigned_level}!\n\n"
            f"Результат: {score}/7\n\n"
            f"Готов практиковаться? Напиши /new чтобы начать диалог!"
        )
    except Exception as e:
        await update.callback_query.edit_message_text(
            f"❌ Ошибка сохранения профиля. Попробуй /start снова.\nОшибка: {str(e)}"
        )
        return ConversationHandler.END

    return ConversationHandler.END
