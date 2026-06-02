"""FL.ru RSS parser — no auth required."""
import logging
import feedparser
import httpx
from datetime import datetime, timezone

from app.filter import matches_keywords, extract_budget, passes_budget, is_profile_or_resume

log = logging.getLogger(__name__)

FL_RSS_URLS = [
    "https://www.fl.ru/rss/projects/?category=saity",
    "https://www.fl.ru/rss/projects/?category=seo",
    "https://www.fl.ru/rss/projects/?category=programmirovanie",
    "https://www.fl.ru/rss/projects/?category=reklama-i-marketing",
]


async def fetch_fl_leads() -> list[dict]:
    leads = []
    async with httpx.AsyncClient(timeout=15) as client:
        for url in FL_RSS_URLS:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception as e:
                log.warning(f"FL.ru {url} failed: {type(e).__name__}: {e}")
                continue

            feed = feedparser.parse(resp.text)
            log.info(f"FL.ru RSS has {len(feed.entries)} total entries")
            for entry in feed.entries:
                text = entry.get("summary", "") or entry.get("title", "")
                title = entry.get("title", "")
                full_text = f"{title}\n{text}"

                if is_profile_or_resume(full_text):
                    log.debug(f"Filtered (profile/resume): {title[:50]}")
                    continue

                if not matches_keywords(full_text):
                    log.debug(f"Filtered (no keywords): {title[:50]}")
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
                        "source": "fl",
                        "source_url": entry.get("link", ""),
                        "title": title[:512],
                        "text": full_text,
                        "budget": budget,
                        "contact": None,
                        "created_at": created_at,
                    }
                )
    log.info(f"FL.ru: {len(leads)} leads fetched")
    return leads
