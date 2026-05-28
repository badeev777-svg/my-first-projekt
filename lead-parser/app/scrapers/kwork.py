"""Kwork.ru RSS parser — парсит заказы с русской биржи."""
import logging
import feedparser
import httpx
from datetime import datetime, timezone

from app.filter import matches_keywords, extract_budget, passes_budget

log = logging.getLogger(__name__)

# Kwork RSS URL (глобальный RSS со всеми услугами, фильтруем по ключевым словам)
# Примечание: старые endpoints /feed/services/* были заменены на один глобальный RSS
KWORK_RSS_URLS = [
    "https://kwork.ru/rss",
]


async def fetch_kwork_leads() -> list[dict]:
    """Парсит RSS ленты с заказами с kwork.ru."""
    leads = []
    async with httpx.AsyncClient(timeout=15) as client:
        for url in KWORK_RSS_URLS:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception as e:
                log.warning(f"Kwork {url} failed: {type(e).__name__}: {e}")
                continue

            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                text = entry.get("summary", "") or entry.get("description", "") or ""
                title = entry.get("title", "")
                full_text = f"{title}\n{text}"

                if not matches_keywords(full_text):
                    continue

                budget = extract_budget(full_text)
                if not passes_budget(budget):
                    continue

                pub = entry.get("published_parsed")
                created_at = (
                    datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.utcnow()
                )

                leads.append(
                    {
                        "source": "kwork",
                        "source_url": entry.get("link", ""),
                        "title": title[:512],
                        "text": full_text,
                        "budget": budget,
                        "contact": None,
                        "created_at": created_at,
                    }
                )
    log.info(f"Kwork: {len(leads)} leads fetched")
    return leads
