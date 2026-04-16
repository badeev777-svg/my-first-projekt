# ============================================================
# services/slots.py — генерация слотов и проверка занятости
# ============================================================
# Метафора: как сетка в Google Calendar.
# Берём шаблон недели (work_schedule) → нарезаем слоты →
# вычитаем уже занятые (bookings) и заблокированные (slot_overrides).
#
# TODO: реализовать в Фазе 2

from datetime import date, time, timedelta
from typing import List


def generate_slots(
    start_time: time,
    end_time: time,
    slot_duration_min: int,
) -> List[time]:
    """Нарезает рабочий день на слоты заданной длины."""
    slots = []
    current = timedelta(hours=start_time.hour, minutes=start_time.minute)
    end = timedelta(hours=end_time.hour, minutes=end_time.minute)
    step = timedelta(minutes=slot_duration_min)

    while current + step <= end:
        h, rem = divmod(int(current.total_seconds()), 3600)
        m = rem // 60
        slots.append(time(h, m))
        current += step

    return slots
