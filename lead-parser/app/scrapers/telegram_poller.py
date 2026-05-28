"""Telegram channel monitor using Telethon userbot."""
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient
from telethon.tl.types import Message

from app.config import TG_API_ID, TG_API_HASH, TG_PHONE, TG_CHANNELS
from app.filter import matches_keywords, extract_budget, passes_budget

SESSION_FILE = "data/tg_session"

_client: TelegramClient | None = None


async def get_client() -> TelegramClient:
    global _client
    if _client is None or not _client.is_connected():
        _client = TelegramClient(SESSION_FILE, TG_API_ID, TG_API_HASH)
        await _client.start(phone=TG_PHONE)
    return _client


async def fetch_telegram_leads(since_minutes: int = 15) -> list[dict]:
    if not TG_API_ID or not TG_API_HASH or not TG_CHANNELS:
        return []

    client = await get_client()
    since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    leads = []

    for channel in TG_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            async for msg in client.iter_messages(entity, limit=50):
                if not isinstance(msg, Message) or not msg.text:
                    continue
                if msg.date < since:
                    break

                if not matches_keywords(msg.text):
                    continue

                budget = extract_budget(msg.text)
                if not passes_budget(budget):
                    continue

                sender = msg.sender
                contact = None
                if sender and hasattr(sender, "username") and sender.username:
                    contact = f"@{sender.username}"

                source_url = f"https://t.me/{channel}/{msg.id}"
                leads.append(
                    {
                        "source": "telegram",
                        "source_url": source_url,
                        "title": msg.text[:100],
                        "text": msg.text,
                        "budget": budget,
                        "contact": contact,
                        "created_at": msg.date,
                    }
                )
        except Exception:
            continue

    return leads
