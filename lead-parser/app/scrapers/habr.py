"""Habr Freelance RSS parser."""
import logging
import feedparser
import httpx
from datetime import datetime, timezone

from app.filter import matches_keywords, extract_budget, passes_budget

log = logging.getLogger(__name__)
HABR_RSS_URL = "https://freelance.habr.com/tasks.rss"


async def fetch_habr_leads() -> list[dict]:
    leads = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                HABR_RSS_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            resp.raise_for_status()
        except Exception as e:
            log.error(f"Habr fetch failed: {type(e).__name__}: {e}")
            return leads

        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            text = entry.get("summary", "") or ""
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
                    "source": "habr",
                    "source_url": entry.get("link", ""),
                    "title": title[:512],
                    "text": full_text,
                    "budget": budget,
                    "contact": None,
                    "created_at": created_at,
                }
            )
    log.info(f"Habr: {len(leads)} leads fetched")
    return leads
