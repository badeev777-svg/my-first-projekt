# ============================================================
# bot/master_bot.py — команды управления ботом мастера
# ============================================================
# Метафора: это «пульт управления» для каждого мастера.
# Один и тот же код обслуживает все боты всех мастеров —
# мастер передаётся через контекст из webhook-диспетчера.
#
# Мастер (telegram_user_id == master.telegram_user_id):
#   /start        — панель управления
#   /profile      — просмотр профиля
#   /set_name     /set_specialty  /set_city  /set_bio
#   /services     — список услуг
#   /add_service  — добавить услугу (FSM-диалог)
#   /delete_service <id>
#   /schedule     — расписание
#   /set_schedule — задать расписание (FSM-диалог)
#   /block_day <дд.мм> — заблокировать день
#   /today        — записи на сегодня
#   /upcoming     — записи на 7 дней
#
# Клиент (все остальные):
#   /start        — приветствие мастера

from datetime import date, time, timedelta

from aiogram import Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from sqlalchemy import select, delete, func

from database import AsyncSessionLocal
from models.booking import Booking
from models.client import Client
from models.master import Master
from models.schedule import WorkSchedule, SlotOverride
from models.service import Service


router = Router()
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

from bot.client_bot import router as client_router
dp.include_router(client_router)

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def is_master(message: Message, master: Master) -> bool:
    return message.from_user.id == master.telegram_user_id


def client_name(client: Client) -> str:
    parts = [client.first_name or "", client.last_name or ""]
    return " ".join(p for p in parts if p) or "Клиент"


# ============================================================
# FSM: добавление услуги
# ============================================================

class AddService(StatesGroup):
    category = State()
    name     = State()
    price    = State()
    duration = State()


# ============================================================
# FSM: настройка расписания
# ============================================================

class SetSchedule(StatesGroup):
    days       = State()
    hours      = State()
    slot_dur   = State()


# ============================================================
# /start
# ============================================================

@router.message(CommandStart())
async def cmd_start(message: Message, master: Master):
    if is_master(message, master):
        await message.answer(
            f"Панель управления\n"
            f"Мастер: {master.name}\n\n"
            f"/profile — профиль\n"
            f"/services — услуги\n"
            f"/schedule — расписание\n"
            f"/today — сегодняшние записи\n"
            f"/upcoming — записи на 7 дней"
        )
    else:
        await message.answer(
            f"Привет! Я помогу записаться к мастеру {master.name}.\n\n"
            f"Напиши /book чтобы выбрать услугу и время."
        )


# ============================================================
# Профиль
# ============================================================

@router.message(Command("profile"))
async def cmd_profile(message: Message, master: Master):
    if not is_master(message, master):
        return

    await message.answer(
        f"Профиль\n"
        f"Имя: {master.name}\n"
        f"Специализация: {master.specialty or '—'}\n"
        f"Город: {master.city or '—'}\n"
        f"О себе: {master.bio or '—'}\n"
        f"Slug: {master.slug}\n"
        f"Рейтинг: {master.rating} ({master.reviews_count} отзывов)\n"
        f"Подписка: {master.subscription_status}\n"
        f"Услуг: {master.services_limit} (лимит)\n\n"
        f"Изменить:\n"
        f"/set_name <имя>\n"
        f"/set_specialty <специализация>\n"
        f"/set_city <город>\n"
        f"/set_bio <о себе>"
    )


@router.message(Command("set_name"))
async def cmd_set_name(message: Message, master: Master):
    if not is_master(message, master):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_name Анна Гук")
        return
    async with AsyncSessionLocal() as db:
        m = await db.get(Master, master.id)
        m.name = parts[1].strip()
        await db.commit()
    await message.answer(f"Имя обновлено: {parts[1].strip()}")


@router.message(Command("set_specialty"))
async def cmd_set_specialty(message: Message, master: Master):
    if not is_master(message, master):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_specialty Мастер маникюра")
        return
    async with AsyncSessionLocal() as db:
        m = await db.get(Master, master.id)
        m.specialty = parts[1].strip()
        await db.commit()
    await message.answer("Специализация обновлена.")


@router.message(Command("set_city"))
async def cmd_set_city(message: Message, master: Master):
    if not is_master(message, master):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_city Киев")
        return
    async with AsyncSessionLocal() as db:
        m = await db.get(Master, master.id)
        m.city = parts[1].strip()
        await db.commit()
    await message.answer("Город обновлён.")


@router.message(Command("set_bio"))
async def cmd_set_bio(message: Message, master: Master):
    if not is_master(message, master):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_bio Работаю 5 лет, специализируюсь на...")
        return
    async with AsyncSessionLocal() as db:
        m = await db.get(Master, master.id)
        m.bio = parts[1].strip()
        await db.commit()
    await message.answer("Описание обновлено.")


# ============================================================
# Услуги
# ============================================================

@router.message(Command("services"))
async def cmd_services(message: Message, master: Master):
    if not is_master(message, master):
        return

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Service)
            .where(Service.master_id == master.id, Service.is_active == True)
            .order_by(Service.sort_order, Service.id)
        )
        services = res.scalars().all()

    if not services:
        await message.answer("Услуг пока нет.\n\nДобавить: /add_service")
        return

    lines = [f"Услуги ({len(services)} из {master.services_limit}):"]
    for s in services:
        lines.append(f"#{s.id} {s.name} — {s.price}р, {s.duration_min}мин [{s.category}]")
    lines += ["", "/add_service — добавить", "/delete_service <id> — удалить"]
    await message.answer("\n".join(lines))


@router.message(Command("add_service"))
async def cmd_add_service(message: Message, master: Master, state: FSMContext):
    if not is_master(message, master):
        return

    async with AsyncSessionLocal() as db:
        count = await db.scalar(
            select(func.count(Service.id))
            .where(Service.master_id == master.id, Service.is_active == True)
        )

    if count >= master.services_limit:
        await message.answer(
            f"Достигнут лимит услуг: {master.services_limit}.\n"
            f"Оформи подписку для снятия ограничений: /subscription"
        )
        return

    await state.set_state(AddService.category)
    await message.answer(
        "Категория услуги?\n"
        "Например: Маникюр, Педикюр, Ресницы, Брови, Массаж"
    )


@router.message(AddService.category)
async def add_svc_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await state.set_state(AddService.name)
    await message.answer("Название услуги?")


@router.message(AddService.name)
async def add_svc_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddService.price)
    await message.answer("Цена в рублях (только цифры)?")


@router.message(AddService.price)
async def add_svc_price(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Введи цену цифрами, например: 1500")
        return
    await state.update_data(price=int(message.text.strip()))
    await state.set_state(AddService.duration)
    await message.answer("Длительность в минутах, например: 60")


@router.message(AddService.duration)
async def add_svc_duration(message: Message, master: Master, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Введи длительность цифрами, например: 90")
        return

    data = await state.get_data()
    duration = int(message.text.strip())
    await state.clear()

    async with AsyncSessionLocal() as db:
        db.add(Service(
            master_id=master.id,
            category=data["category"],
            name=data["name"],
            price=data["price"],
            duration_min=duration,
        ))
        await db.commit()

    await message.answer(
        f"Услуга добавлена:\n"
        f"{data['name']} — {data['price']}р, {duration}мин\n"
        f"Категория: {data['category']}"
    )


@router.message(Command("delete_service"))
async def cmd_delete_service(message: Message, master: Master):
    if not is_master(message, master):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /delete_service <id>")
        return

    service_id = int(parts[1])
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Service).where(Service.id == service_id, Service.master_id == master.id)
        )
        svc = res.scalar_one_or_none()
        if not svc:
            await message.answer("Услуга не найдена.")
            return
        svc.is_active = False
        await db.commit()
    await message.answer(f"Услуга #{service_id} удалена.")


# ============================================================
# Расписание
# ============================================================

@router.message(Command("schedule"))
async def cmd_schedule(message: Message, master: Master):
    if not is_master(message, master):
        return

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(WorkSchedule)
            .where(WorkSchedule.master_id == master.id)
            .order_by(WorkSchedule.day_of_week)
        )
        schedule = res.scalars().all()

    if not schedule:
        await message.answer("Расписание не задано.\n\nНастроить: /set_schedule")
        return

    lines = ["Расписание:"]
    for s in schedule:
        if s.is_working:
            lines.append(
                f"{DAY_NAMES[s.day_of_week]}: "
                f"{s.start_time.strftime('%H:%M')}—{s.end_time.strftime('%H:%M')}, "
                f"слот {s.slot_duration_min}мин"
            )
        else:
            lines.append(f"{DAY_NAMES[s.day_of_week]}: выходной")
    lines += ["", "/set_schedule — изменить", "/block_day дд.мм — заблокировать день"]
    await message.answer("\n".join(lines))


@router.message(Command("set_schedule"))
async def cmd_set_schedule(message: Message, master: Master, state: FSMContext):
    if not is_master(message, master):
        return
    await state.set_state(SetSchedule.days)
    await message.answer(
        "Рабочие дни?\n"
        "Введи номера (1=Пн, 7=Вс) через запятую или диапазон:\n"
        "1,2,3,4,5 — Пн-Пт\n"
        "1-6 — Пн-Сб"
    )


@router.message(SetSchedule.days)
async def sched_days(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        if "-" in text and "," not in text:
            a, b = text.split("-")
            days = list(range(int(a) - 1, int(b)))
        else:
            days = [int(d.strip()) - 1 for d in text.split(",")]
        if not days or not all(0 <= d <= 6 for d in days):
            raise ValueError
    except (ValueError, IndexError):
        await message.answer("Неверный формат. Введи: 1,2,3,4,5 или 1-5")
        return

    await state.update_data(days=days)
    await state.set_state(SetSchedule.hours)
    await message.answer("Время работы?\nФормат: ЧЧ:ММ-ЧЧ:ММ, например: 10:00-19:00")


@router.message(SetSchedule.hours)
async def sched_hours(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        start_str, end_str = text.split("-")
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        start_t = time(sh, sm)
        end_t = time(eh, em)
        if start_t >= end_t:
            raise ValueError
    except Exception:
        await message.answer("Неверный формат. Введи: 10:00-19:00")
        return

    await state.update_data(start_time=start_t, end_time=end_t)
    await state.set_state(SetSchedule.slot_dur)
    await message.answer("Длительность слота в минутах?\nНапример: 60 или 90")


@router.message(SetSchedule.slot_dur)
async def sched_slot_dur(message: Message, master: Master, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Введи цифрами: 60 или 90")
        return

    data = await state.get_data()
    duration = int(message.text.strip())
    working_days = set(data["days"])
    await state.clear()

    async with AsyncSessionLocal() as db:
        await db.execute(delete(WorkSchedule).where(WorkSchedule.master_id == master.id))
        for day in range(7):
            db.add(WorkSchedule(
                master_id=master.id,
                day_of_week=day,
                start_time=data["start_time"],
                end_time=data["end_time"],
                slot_duration_min=duration,
                is_working=(day in working_days),
            ))
        await db.commit()

    lines = ["Расписание сохранено:"]
    for day in range(7):
        if day in working_days:
            lines.append(
                f"{DAY_NAMES[day]}: "
                f"{data['start_time'].strftime('%H:%M')}—{data['end_time'].strftime('%H:%M')}"
            )
        else:
            lines.append(f"{DAY_NAMES[day]}: выходной")
    await message.answer("\n".join(lines))


@router.message(Command("block_day"))
async def cmd_block_day(message: Message, master: Master):
    if not is_master(message, master):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /block_day 25.04")
        return
    try:
        d, m_num = parts[1].split(".")
        block_date = date(date.today().year, int(m_num), int(d))
    except Exception:
        await message.answer("Неверный формат. Используй: /block_day 25.04")
        return

    async with AsyncSessionLocal() as db:
        db.add(SlotOverride(
            master_id=master.id,
            date=block_date,
            is_blocked=True,
            reason="Заблокировано мастером",
        ))
        await db.commit()
    await message.answer(f"День {parts[1]} заблокирован. Запись на этот день закрыта.")


# ============================================================
# Записи
# ============================================================

@router.message(Command("today"))
async def cmd_today(message: Message, master: Master):
    if not is_master(message, master):
        return

    today = date.today()
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Booking, Client)
            .join(Client, Booking.client_id == Client.id)
            .where(
                Booking.master_id == master.id,
                Booking.date == today,
                Booking.status == "confirmed",
            )
            .order_by(Booking.time)
        )
        rows = res.all()

    if not rows:
        await message.answer(f"Записей на сегодня ({today.strftime('%d.%m')}) нет.")
        return

    lines = [f"Сегодня {today.strftime('%d.%m')}, записей: {len(rows)}"]
    for booking, cl in rows:
        lines.append(
            f"{booking.time.strftime('%H:%M')} — {client_name(cl)}, "
            f"{booking.service_name} ({booking.duration_min}мин), "
            f"{booking.service_price}р"
        )
    await message.answer("\n".join(lines))


@router.message(Command("upcoming"))
async def cmd_upcoming(message: Message, master: Master):
    if not is_master(message, master):
        return

    today = date.today()
    in_7 = today + timedelta(days=7)

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Booking, Client)
            .join(Client, Booking.client_id == Client.id)
            .where(
                Booking.master_id == master.id,
                Booking.date >= today,
                Booking.date <= in_7,
                Booking.status == "confirmed",
            )
            .order_by(Booking.date, Booking.time)
        )
        rows = res.all()

    if not rows:
        await message.answer("Записей на ближайшие 7 дней нет.")
        return

    lines = [f"Ближайшие записи ({len(rows)}):"]
    cur_date = None
    for booking, cl in rows:
        if booking.date != cur_date:
            cur_date = booking.date
            day_name = DAY_NAMES[cur_date.weekday()]
            lines.append(f"\n{cur_date.strftime('%d.%m')} {day_name}:")
        lines.append(
            f"  {booking.time.strftime('%H:%M')} {client_name(cl)} — "
            f"{booking.service_name}, {booking.service_price}р"
        )
    await message.answer("\n".join(lines))
