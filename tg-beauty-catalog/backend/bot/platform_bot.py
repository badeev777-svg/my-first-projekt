# ============================================================
# bot/platform_bot.py — платформенный бот (онбординг мастеров)
# ============================================================
# Метафора: это «ресепшн» платформы. Мастера приходят сюда
# чтобы подключить свой бот и получить доступ к каталогу.
#
# Команды мастера:
#   /start              — приветствие + инструкция
#   /connect <token>    — подключить бота мастера
#
# Команды супер-админа (только ADMIN_TELEGRAM_USER_ID):
#   /masters            — список всех мастеров
#   /activate <id>      — активировать подписку на 30 дней
#   /block <id>         — заблокировать мастера
#   /stats              — общая статистика

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from sqlalchemy import select, func

from config import settings
from database import AsyncSessionLocal
from models.master import Master
from services.bot_manager import connect_master, activate_subscription, block_master


# Глобальные объекты бота — создаются один раз при импорте
bot = Bot(token=settings.platform_bot_token)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# ============================================================
# Команды мастера
# ============================================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я платформа BeautyCatalog.\n\n"
        "Как подключить своего бота:\n"
        "1. Создай бота через @BotFather (/newbot)\n"
        "2. Скопируй токен\n"
        "3. Отправь мне: /connect <токен>\n\n"
        "Пример:\n"
        "/connect 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    )


@router.message(Command("connect"))
async def cmd_connect(message: Message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Укажи токен бота.\n"
            "Пример: /connect 123456:ABCdef..."
        )
        return

    token = parts[1].strip()

    # Базовая проверка формата: должен быть двоеточие и достаточная длина
    if ":" not in token or len(token) < 30:
        await message.answer(
            "Неверный формат токена.\n"
            "Скопируй его из @BotFather — он выглядит так: 123456789:ABCdef..."
        )
        return

    await message.answer("Проверяю токен, секунду...")

    try:
        status, data = await connect_master(
            telegram_user_id=message.from_user.id,
            token=token,
        )
    except Exception as e:
        await message.answer(
            f"Произошла ошибка при подключении.\n"
            f"Детали: {type(e).__name__}: {e}"
        )
        return

    if status == "already_connected":
        await message.answer(
            "Этот бот уже подключён к платформе."
        )

    elif status == "user_has_bot":
        await message.answer(
            "У тебя уже есть подключённый бот.\n"
            "Если нужна помощь — обратись к администратору."
        )

    elif status == "invalid_token":
        await message.answer(
            "Токен не прошёл проверку Telegram.\n"
            "Убедись, что скопировал его полностью и правильно из @BotFather."
        )

    else:  # success
        slug = data["slug"]
        bot_username = data["bot_username"]
        webhook_ok = data.get("webhook_ok", False)

        lines = [
            f"Бот @{bot_username} успешно подключён!",
            "",
            f"Твой адрес в каталоге:",
            f"/masters/{slug}",
            "",
            f"Открой @{bot_username} и напиши /start чтобы заполнить профиль.",
        ]

        if not webhook_ok:
            lines += [
                "",
                "Вебхук пока не установлен — сервер недоступен из интернета.",
                "Это нормально для локальной разработки.",
            ]

        await message.answer("\n".join(lines))


# ============================================================
# Команды администратора
# ============================================================

@router.message(Command("masters"))
async def cmd_masters(message: Message):
    if message.from_user.id != settings.admin_telegram_user_id:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Master).order_by(Master.created_at.desc()).limit(20)
        )
        masters = result.scalars().all()

    if not masters:
        await message.answer("Мастеров пока нет.")
        return

    lines = [f"Мастера ({len(masters)}):"]
    for m in masters:
        status_icon = "+" if m.is_active else "-"
        lines.append(
            f"[{status_icon}] #{m.id} @{m.bot_username} "
            f"slug:{m.slug} sub:{m.subscription_status}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("activate"))
async def cmd_activate(message: Message):
    if message.from_user.id != settings.admin_telegram_user_id:
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /activate <id>")
        return

    master_id = int(parts[1])
    ok = await activate_subscription(master_id, days=30)

    if ok:
        await message.answer(f"Мастер #{master_id} активирован на 30 дней.")
    else:
        await message.answer(f"Мастер #{master_id} не найден.")


@router.message(Command("block"))
async def cmd_block(message: Message):
    if message.from_user.id != settings.admin_telegram_user_id:
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /block <id>")
        return

    master_id = int(parts[1])
    ok = await block_master(master_id)

    if ok:
        await message.answer(f"Мастер #{master_id} заблокирован.")
    else:
        await message.answer(f"Мастер #{master_id} не найден.")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != settings.admin_telegram_user_id:
        return

    async with AsyncSessionLocal() as db:
        total = await db.scalar(select(func.count(Master.id)))
        active = await db.scalar(
            select(func.count(Master.id)).where(Master.is_active == True)
        )
        paid = await db.scalar(
            select(func.count(Master.id)).where(
                Master.subscription_status == "active"
            )
        )

    await message.answer(
        f"Статистика платформы:\n"
        f"Всего мастеров: {total}\n"
        f"Активных ботов: {active}\n"
        f"Платных подписок: {paid}"
    )
