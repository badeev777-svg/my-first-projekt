# ============================================================
# services/slots.py — генерация слотов и проверка занятости
# ============================================================

from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from database import AsyncSessionLocal
from models.booking import Booking
from models.schedule import SlotOverride, WorkSchedule


def generate_slots(
    start_time: time,
    end_time: time,
    slot_duration_min: int,
) -> list[time]:
    """Нарезает рабочий день на слоты заданной длины."""
    slots: list[time] = []
    current = timedelta(hours=start_time.hour, minutes=start_time.minute)
    end = timedelta(hours=end_time.hour, minutes=end_time.minute)
    step = timedelta(minutes=slot_duration_min)

    while current + step <= end:
        h, rem = divmod(int(current.total_seconds()), 3600)
        m = rem // 60
        slots.append(time(h, m))
        current += step

    return slots


async def get_free_slots(master_id: int, target_date: date) -> list[time]:
    """Возвращает список свободных слотов для мастера на указанную дату."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(WorkSchedule).where(
                WorkSchedule.master_id == master_id,
                WorkSchedule.day_of_week == target_date.weekday(),
                WorkSchedule.is_working == True,
            )
        )
        sched = res.scalar_one_or_none()
        if not sched:
            return []

        res = await db.execute(
            select(SlotOverride).where(
                SlotOverride.master_id == master_id,
                SlotOverride.date == target_date,
                SlotOverride.is_blocked == True,
                SlotOverride.time == None,
            )
        )
        if res.scalar_one_or_none():
            return []

        res = await db.execute(
            select(Booking.time).where(
                Booking.master_id == master_id,
                Booking.date == target_date,
                Booking.status == "confirmed",
            )
        )
        booked = {row[0] for row in res.all()}

    all_slots = generate_slots(sched.start_time, sched.end_time, sched.slot_duration_min)
    return [t for t in all_slots if t not in booked]
