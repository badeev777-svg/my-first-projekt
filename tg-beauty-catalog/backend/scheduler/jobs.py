# ============================================================
# scheduler/jobs.py — фоновые задачи
# ============================================================
# Метафора: будильники которые сами срабатывают.
# APScheduler запускает эти функции по расписанию.
#
# Задачи:
#   - remind_24h:   каждые 15 мин — напоминания за 24 часа до записи
#   - remind_2h:    каждые 15 мин — напоминания за 2 часа до записи
#   - expire_subs:  ежедневно 00:00 — деактивация истёкших подписок
#
# TODO: реализовать в Фазе 3


async def remind_24h():
    """Находит записи через ~24 часа и отправляет напоминание клиенту."""
    # SELECT * FROM bookings WHERE date+time BETWEEN NOW()+23h45m AND NOW()+24h15m
    #   AND reminder_24h_sent = FALSE AND status = 'confirmed'
    # Для каждой → отправить сообщение через бот мастера → UPDATE reminder_24h_sent = TRUE
    pass


async def remind_2h():
    """Находит записи через ~2 часа и отправляет напоминание клиенту."""
    pass


async def expire_subscriptions():
    """Деактивирует истёкшие подписки и уведомляет мастеров."""
    # UPDATE masters SET subscription_status='expired', services_limit=5
    # WHERE subscription_status='active' AND subscription_expires_at < NOW()
    pass
