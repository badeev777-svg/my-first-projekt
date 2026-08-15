import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_API = "https://botapi.max.ru/messages/send"

_LEAD_TEMPLATE = (
    "🔔 НОВЫЙ ЛИД — диагностика завершена!\n\n"
    "📦 Бизнес: {business_name}\n"
    "🎯 Ниша: {niche}\n"
    "😤 Боли: {pain_points}\n"
    "🌐 Источник: {utm_source}{utm_medium}\n\n"
    "→ Детали: {admin_url}/admin/leads/{lead_id}"
)

_CONTACT_TEMPLATE = (
    "📋 Новая заявка с сайта!\n\n"
    "👤 Имя: {name}\n"
    "📞 Телефон: {phone}\n"
    "📧 Email: {email}"
)


async def notify_contact(name: str, phone: str, email: str) -> None:
    text = _CONTACT_TEMPLATE.format(name=name, phone=phone, email=email or "не указан")
    async with httpx.AsyncClient(timeout=15) as client:
        if settings.TG_BOT_TOKEN and settings.TG_CHAT_ID:
            await _send_telegram(client, text)
        if settings.MAX_BOT_TOKEN and settings.MAX_USER_ID:
            await _send_max(client, text)


async def notify_all(
    lead_id: int = 0,
    business_name: str = "",
    niche: str = "",
    pain_points: str = "",
    utm_source: str = "",
    utm_medium: str = "",
) -> None:
    admin_url = settings.ADMIN_URL.rstrip("/").rsplit("/admin", 1)[0]
    utm_medium_str = f" / {utm_medium}" if utm_medium else ""

    text = _LEAD_TEMPLATE.format(
        business_name=business_name or "—",
        niche=niche or "—",
        pain_points=pain_points or "—",
        utm_source=utm_source or "прямой",
        utm_medium=utm_medium_str,
        admin_url=admin_url,
        lead_id=lead_id,
    )
    async with httpx.AsyncClient(timeout=15) as client:
        if settings.TG_BOT_TOKEN and settings.TG_CHAT_ID:
            await _send_telegram(client, text)
        if settings.MAX_BOT_TOKEN and settings.MAX_USER_ID:
            await _send_max(client, text)


async def _send_telegram(client: httpx.AsyncClient, text: str) -> None:
    try:
        r = await client.post(
            _TG_API.format(token=settings.TG_BOT_TOKEN),
            json={
                "chat_id": settings.TG_CHAT_ID,
                "text": text[:4096],
            },
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("Telegram notify failed: HTTP %s", e.response.status_code)
    except Exception:
        logger.error("Telegram notify failed: request error")


async def _send_max(client: httpx.AsyncClient, text: str) -> None:
    try:
        r = await client.post(
            _MAX_API,
            params={"access_token": settings.MAX_BOT_TOKEN},
            json={
                "recipient": {"user_id": settings.MAX_USER_ID},
                "text": text[:2000],
            },
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("MAX notify failed: HTTP %s", e.response.status_code)
    except Exception:
        logger.error("MAX notify failed: request error")
