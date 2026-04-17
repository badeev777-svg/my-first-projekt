# ============================================================
# bot/client_bot.py — /book флоу для клиентов
# ============================================================
# Шаги: выбор услуги → дата → время → телефон → подтверждение → запись в БД
# Уведомление мастеру отправляется сразу после создания записи.

from datetime import date, time, timedelta, datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from sqlalchemy import select

from database import AsyncSessionLocal
from models.booking import Booking
from models.client import Client
from models.master import Master
from models.service import Service
from services.slots import get_free_slots

router = Router()

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# get_free_slots импортирован из services.slots


class BookFlow(StatesGroup):
    select_service = State()
    select_date    = State()
    select_time    = State()
    enter_phone    = State()
    confirm        = State()


def make_kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=d) for t, d in row]
            for row in rows
        ]
    )


# ============================================================
# /book — старт флоу
# ============================================================

@router.message(Command("book"))
async def cmd_book(message: Message, master: Master, state: FSMContext):
    if message.from_user.id == master.telegram_user_id:
        return

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Service)
            .where(Service.master_id == master.id, Service.is_active == True)
            .order_by(Service.sort_order, Service.id)
        )
        services = res.scalars().all()

    if not services:
        await message.answer("У мастера пока нет услуг. Попробуй позже.")
        return

    buttons = [
        [(f"{s.name} — {s.price}р ({s.duration_min}мин)", f"svc:{s.id}")]
        for s in services
    ]
    buttons.append([("Отмена", "cancel")])

    await state.set_state(BookFlow.select_service)
    await message.answer("Выбери услугу:", reply_markup=make_kb(buttons))


# ============================================================
# Шаг 1: выбор услуги
# ============================================================

@router.callback_query(BookFlow.select_service)
async def on_select_service(cb: CallbackQuery, master: Master, state: FSMContext):
    if cb.data == "cancel":
        await state.clear()
        await cb.message.edit_text("Запись отменена.")
        return

    if not cb.data.startswith("svc:"):
        return

    service_id = int(cb.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        svc = await db.get(Service, service_id)

    if not svc or svc.master_id != master.id:
        await cb.answer("Услуга не найдена.")
        return

    await state.update_data(
        service_id=svc.id,
        service_name=svc.name,
        service_price=svc.price,
        duration_min=svc.duration_min,
    )

    # Ищем до 7 ближайших дней со свободными слотами (проверяем 30 дней)
    today = date.today()
    date_buttons = []
    d = today
    for _ in range(30):
        if len(date_buttons) >= 7:
            break
        slots = await get_free_slots(master.id, d)
        if slots:
            label = f"{d.strftime('%d.%m')} {DAY_NAMES[d.weekday()]} ({len(slots)} окон)"
            date_buttons.append([(label, f"date:{d.isoformat()}")])
        d += timedelta(days=1)

    if not date_buttons:
        await state.clear()
        await cb.message.edit_text(
            "Нет свободных дней в ближайшие 30 дней. Попробуй позже."
        )
        return

    date_buttons.append([("Отмена", "cancel")])
    await state.set_state(BookFlow.select_date)
    await cb.message.edit_text(
        f"Услуга: {svc.name}\n\nВыбери дату:",
        reply_markup=make_kb(date_buttons),
    )


# ============================================================
# Шаг 2: выбор даты
# ============================================================

@router.callback_query(BookFlow.select_date)
async def on_select_date(cb: CallbackQuery, master: Master, state: FSMContext):
    if cb.data == "cancel":
        await state.clear()
        await cb.message.edit_text("Запись отменена.")
        return

    if not cb.data.startswith("date:"):
        return

    target_date = date.fromisoformat(cb.data.split(":", 1)[1])
    slots = await get_free_slots(master.id, target_date)

    if not slots:
        await cb.answer("Этот день уже занят, выбери другой.")
        return

    await state.update_data(date=target_date.isoformat())

    # Слоты попарно в одну строку для компактности
    rows = []
    for i in range(0, len(slots), 2):
        row = [InlineKeyboardButton(
            text=slots[i].strftime("%H:%M"),
            callback_data=f"time:{slots[i].strftime('%H:%M')}",
        )]
        if i + 1 < len(slots):
            row.append(InlineKeyboardButton(
                text=slots[i + 1].strftime("%H:%M"),
                callback_data=f"time:{slots[i + 1].strftime('%H:%M')}",
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])

    day_name = DAY_NAMES[target_date.weekday()]
    await state.set_state(BookFlow.select_time)
    await cb.message.edit_text(
        f"Дата: {target_date.strftime('%d.%m')} {day_name}\n\nВыбери время:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ============================================================
# Шаг 3: выбор времени
# ============================================================

@router.callback_query(BookFlow.select_time)
async def on_select_time(cb: CallbackQuery, state: FSMContext):
    if cb.data == "cancel":
        await state.clear()
        await cb.message.edit_text("Запись отменена.")
        return

    if not cb.data.startswith("time:"):
        return

    time_str = cb.data.split(":", 1)[1]   # "10:00"
    await state.update_data(time=time_str)
    await state.set_state(BookFlow.enter_phone)
    await cb.message.edit_text(
        f"Время: {time_str}\n\n"
        f"Введи номер телефона для подтверждения записи:\n"
        f"Пример: +7 900 123-45-67"
    )


# ============================================================
# Шаг 4: ввод телефона
# ============================================================

@router.message(BookFlow.enter_phone)
async def on_enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 7:
        await message.answer("Введи корректный номер телефона.")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()

    target_date = date.fromisoformat(data["date"])
    day_name = DAY_NAMES[target_date.weekday()]

    await state.set_state(BookFlow.confirm)
    await message.answer(
        f"Проверь данные:\n\n"
        f"Услуга: {data['service_name']}\n"
        f"Цена: {data['service_price']}р\n"
        f"Длительность: {data['duration_min']} мин\n"
        f"Дата: {target_date.strftime('%d.%m.%Y')} {day_name}\n"
        f"Время: {data['time']}\n"
        f"Телефон: {phone}",
        reply_markup=make_kb([[("Подтвердить", "confirm"), ("Отмена", "cancel")]]),
    )


# ============================================================
# Шаг 5: подтверждение → создание записи
# ============================================================

@router.callback_query(BookFlow.confirm)
async def on_confirm(cb: CallbackQuery, master: Master, state: FSMContext):
    if cb.data == "cancel":
        await state.clear()
        await cb.message.edit_text("Запись отменена.")
        return

    data = await state.get_data()
    await state.clear()

    target_date = date.fromisoformat(data["date"])
    h, m = map(int, data["time"].split(":"))
    booking_time = time(h, m)

    # Финальная проверка — слот ещё свободен?
    slots = await get_free_slots(master.id, target_date)
    if booking_time not in slots:
        await cb.message.edit_text(
            "Этот слот только что заняли. Выбери другое время: /book"
        )
        return

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Client).where(
                Client.master_id == master.id,
                Client.telegram_user_id == cb.from_user.id,
            )
        )
        client = res.scalar_one_or_none()
        if not client:
            client = Client(
                master_id=master.id,
                telegram_user_id=cb.from_user.id,
                telegram_chat_id=cb.message.chat.id,
                first_name=cb.from_user.first_name,
                last_name=cb.from_user.last_name,
                username=cb.from_user.username,
                phone=data["phone"],
            )
            db.add(client)
            await db.flush()
        else:
            client.phone = data["phone"]

        booking = Booking(
            master_id=master.id,
            client_id=client.id,
            service_id=data.get("service_id"),
            service_name=data["service_name"],
            service_price=data["service_price"],
            duration_min=data["duration_min"],
            date=target_date,
            time=booking_time,
            phone=data["phone"],
            status="confirmed",
        )
        db.add(booking)
        await db.commit()

    day_name = DAY_NAMES[target_date.weekday()]
    await cb.message.edit_text(
        f"Запись подтверждена!\n\n"
        f"{data['service_name']}\n"
        f"{target_date.strftime('%d.%m.%Y')} {day_name}, {data['time']}\n"
        f"Телефон: {data['phone']}\n\n"
        f"Мастер {master.name} ждёт тебя!"
    )

    # Уведомить мастера
    await _notify_master(master, cb, data, target_date, day_name)


async def _notify_master(
    master: Master,
    cb: CallbackQuery,
    data: dict,
    target_date: date,
    day_name: str,
) -> None:
    try:
        from aiogram import Bot
        from api.webhook import _bot_cache
        from services.crypto import decrypt_token

        bot = _bot_cache.get(master.id)
        if not bot:
            token = decrypt_token(master.bot_token)
            bot = Bot(token=token)

        client_display = cb.from_user.first_name or "Клиент"
        if cb.from_user.username:
            client_display += f" (@{cb.from_user.username})"

        await bot.send_message(
            master.telegram_user_id,
            f"Новая запись!\n\n"
            f"Клиент: {client_display}\n"
            f"Телефон: {data['phone']}\n"
            f"Услуга: {data['service_name']}\n"
            f"Дата: {target_date.strftime('%d.%m.%Y')} {day_name}, {data['time']}",
        )
    except Exception:
        pass
