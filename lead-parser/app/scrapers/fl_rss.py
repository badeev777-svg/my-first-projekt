"""FL.ru RSS parser — no auth required."""
import feedparser
import httpx
from datetime import datetime, timezone

from app.filter import matches_keywords, extract_budget, passes_budget

FL_RSS_URLS = [
    "https://www.fl.ru/rss/all.xml?category=saity",
    "https://www.fl.ru/rss/all.xml?category=seo",
    "https://www.fl.ru/rss/all.xml?category=programmirovanie",
    "https://www.fl.ru/rss/all.xml?category=reklama-i-marketing",
]


async def fetch_fl_leads() -> list[dict]:
    leads = []
    async with httpx.AsyncClient(timeout=15) as client:
        for url in FL_RSS_URLS:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception:
                continue

            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                text = entry.get("summary", "") or entry.get("title", "")
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
                        "source": "fl",
                        "source_url": entry.get("link", ""),
                        "title": title[:512],
                        "text": full_text,
                        "budget": budget,
                        "contact": None,
                        "created_at": created_at,
                    }
                )
    return leads
