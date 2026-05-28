"""Telegram bot notifications."""
import httpx
import logging
from app.config import BOT_TOKEN, BOT_CHAT_ID

log = logging.getLogger(__name__)

NOTIFICATION_MIN_RELEVANCE = 70
SOURCE_LABELS = {
    "telegram": "Telegram",
    "fl": "FL.ru",
    "habr": "Habr Freelance",
    "kwork": "Kwork",
}


async def notify_new_lead(lead: dict, relevance_score: int = None) -> None:
    if not BOT_TOKEN or not BOT_CHAT_ID:
        return

    if relevance_score is not None and relevance_score < NOTIFICATION_MIN_RELEVANCE:
        log.debug(f"Lead relevance {relevance_score}% below threshold {NOTIFICATION_MIN_RELEVANCE}%, skipping notification")
        return

    source = SOURCE_LABELS.get(lead["source"], lead["source"])
    budget = f"{lead['budget']:,} ₽".replace(",", " ") if lead.get("budget") else "не указан"
    contact = lead.get("contact") or "нет"
    title = lead.get("title") or lead["text"][:80]
    url = lead.get("source_url", "")

    relevance_bar = ""
    if relevance_score is not None:
        bar_len = relevance_score // 10
        relevance_bar = f"\n📊 Релевантность: {'█' * bar_len}{'░' * (10 - bar_len)} {relevance_score}%"

    text = (
        f"🔔 <b>Новая заявка</b> — {source}"
        f"{relevance_bar}\n\n"
        f"<b>{title}</b>\n\n"
        f"💰 Бюджет: {budget}\n"
        f"👤 Контакт: {contact}\n"
        f"🔗 <a href='{url}'>Открыть</a>"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": BOT_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
        except Exception:
            pass
