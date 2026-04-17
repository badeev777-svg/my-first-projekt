# ============================================================
# services/scheduler.py — фоновые задачи (APScheduler)
# ============================================================
# Задачи:
#   remind_24h  — напоминание клиенту за 24 часа (каждый час)
#   remind_2h   — напоминание клиенту за 2 часа  (каждые 15 мин)
#   expire_bookings — перевод прошедших записей в "completed" (раз в сутки)
#
# Timezone: Europe/Moscow (UTC+3) — мастера и клиенты в РФ

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update

from database import AsyncSessionLocal
from models.booking import Booking
from models.client import Client
from models.master import Master

TZ = ZoneInfo("Europe/Moscow")

scheduler = AsyncIOScheduler(timezone=TZ)


async def _send_reminder(master: Master, client: Client, booking: Booking, label: str) -> bool:
    """Отправляет сообщение-напоминание клиенту через бот мастера."""
    try:
        from aiogram import Bot
        from api.webhook import _bot_cache
        from services.crypto import decrypt_token

        bot = _bot_cache.get(master.id)
        if not bot:
            token = decrypt_token(master.bot_token)
            bot = Bot(token=token)
            _bot_cache[master.id] = bot

        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[booking.date.weekday()]
        time_str = booking.time.strftime("%H:%M")
        date_str = booking.date.strftime("%d.%m.%Y")

        await bot.send_message(
            client.telegram_chat_id,
            f"Напоминание о записи ({label}):\n\n"
            f"Услуга: {booking.service_name}\n"
            f"Дата: {date_str} {day_name}, {time_str}\n"
            f"Мастер: {master.name}\n\n"
            f"Ждём тебя!",
        )
        return True
    except Exception as e:
        print(f"[scheduler] reminder send error (booking {booking.id}): {e}")
        return False


async def job_remind_24h():
    """Раз в час ищет записи на завтра и отправляет напоминание за 24ч."""
    tomorrow = (datetime.now(TZ) + timedelta(days=1)).date()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Booking, Client, Master)
            .join(Client, Booking.client_id == Client.id)
            .join(Master, Booking.master_id == Master.id)
            .where(
                Booking.status == "confirmed",
                Booking.date == tomorrow,
                Booking.reminder_24h_sent == False,
                Master.is_active == True,
            )
        )
        rows = result.all()

        for booking, client, master in rows:
            sent = await _send_reminder(master, client, booking, "за 24 часа")
            if sent:
                await db.execute(
                    update(Booking)
                    .where(Booking.id == booking.id)
                    .values(reminder_24h_sent=True)
                )

        if rows:
            await db.commit()
            print(f"[scheduler] remind_24h: sent {len(rows)} reminders for {tomorrow}")


async def job_remind_2h():
    """Каждые 15 мин ищет записи через 1ч50м–2ч15м и отправляет напоминание за 2ч."""
    now = datetime.now(TZ)
    today = now.date()

    # Окно: записи, которые начнутся через 1ч50м — 2ч15м
    window_start = (now + timedelta(hours=1, minutes=50)).time()
    window_end = (now + timedelta(hours=2, minutes=15)).time()

    # Если окно не пересекает полночь — обычный запрос
    if window_start <= window_end:
        time_filter = (Booking.time >= window_start, Booking.time <= window_end)
        date_filter = (Booking.date == today,)
    else:
        # Окно пересекает полночь: часть сегодня, часть завтра — маловероятно для салона,
        # но обрабатываем корректно.
        tomorrow = (now + timedelta(days=1)).date()
        from sqlalchemy import or_, and_
        time_filter = (
            or_(
                and_(Booking.date == today, Booking.time >= window_start),
                and_(Booking.date == tomorrow, Booking.time <= window_end),
            ),
        )
        date_filter = ()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Booking, Client, Master)
            .join(Client, Booking.client_id == Client.id)
            .join(Master, Booking.master_id == Master.id)
            .where(
                Booking.status == "confirmed",
                Booking.reminder_2h_sent == False,
                Master.is_active == True,
                *date_filter,
                *time_filter,
            )
        )
        rows = result.all()

        for booking, client, master in rows:
            sent = await _send_reminder(master, client, booking, "через 2 часа")
            if sent:
                await db.execute(
                    update(Booking)
                    .where(Booking.id == booking.id)
                    .values(reminder_2h_sent=True)
                )

        if rows:
            await db.commit()
            print(f"[scheduler] remind_2h: sent {len(rows)} reminders")


async def job_expire_bookings():
    """Раз в сутки помечает прошедшие подтверждённые записи как completed."""
    yesterday = (datetime.now(TZ) - timedelta(days=1)).date()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Booking)
            .where(
                Booking.status == "confirmed",
                Booking.date <= yesterday,
            )
            .values(status="completed")
            .returning(Booking.id)
        )
        completed_ids = result.scalars().all()
        await db.commit()

    if completed_ids:
        print(f"[scheduler] expire_bookings: completed {len(completed_ids)} bookings")


def setup_scheduler():
    """Регистрирует джобы и возвращает настроенный планировщик."""
    scheduler.add_job(job_remind_24h,    "interval", hours=1,    id="remind_24h",    replace_existing=True)
    scheduler.add_job(job_remind_2h,     "interval", minutes=15, id="remind_2h",     replace_existing=True)
    scheduler.add_job(job_expire_bookings, "cron",   hour=0, minute=5, id="expire_bookings", replace_existing=True)
    return scheduler
