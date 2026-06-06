"""Freelance.ru scraper — parses open project listings via httpx + BeautifulSoup.

freelance.ru redirects all category-filtered URLs to /task for guests.
We scrape /task (all categories, ~20-25 tasks) and rely on keyword filtering.
"""
import logging
import re
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

from app.filter import matches_keywords, extract_budget, passes_budget, is_profile_or_resume

log = logging.getLogger(__name__)

BASE = "https://freelance.ru"
TASK_URL = f"{BASE}/task"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*",
}


async def fetch_freelance_ru_leads() -> list[dict]:
    leads: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=_HEADERS) as client:
        try:
            resp = await client.get(TASK_URL)
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"Freelance.ru fetch failed: {type(e).__name__}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("article", class_="task-card")
        log.debug(f"Freelance.ru: {len(cards)} total cards")

        for card in cards:
            try:
                link_el = card.find("a", class_="task-card__title-link")
                if not link_el:
                    continue

                href = link_el.get("href", "")
                source_url = href if href.startswith("http") else BASE + href
                if source_url in seen:
                    continue
                seen.add(source_url)

                title = link_el.get_text(strip=True)

                desc_el = card.find("p", class_="task-card__desc")
                desc = desc_el.get_text(strip=True) if desc_el else ""
                full_text = f"{title}\n{desc}".strip()

                if is_profile_or_resume(full_text):
                    continue
                if not matches_keywords(full_text):
                    continue

                budget_el = card.find("div", class_="task-card__budget")
                budget_text = budget_el.get_text(strip=True) if budget_el else ""
                budget = extract_budget(budget_text) or extract_budget(full_text)
                if not passes_budget(budget):
                    continue

                time_el = card.find("span", class_="task-card__foot-item", title=True)
                created_at = _parse_date(time_el.get("title") if time_el else None)

                leads.append({
                    "source": "freelance_ru",
                    "source_url": source_url,
                    "title": title[:512],
                    "text": full_text,
                    "budget": budget,
                    "contact": None,
                    "created_at": created_at,
                })

            except Exception as e:
                log.debug(f"Freelance.ru card parse error: {e}")
                continue

    log.info(f"Freelance.ru: {len(leads)} leads fetched")
    return leads


def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.strptime(raw, "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    m = re.search(r"(\d+)\s+час", raw)
    if m:
        return datetime.now(timezone.utc) - timedelta(hours=int(m.group(1)))
    m = re.search(r"(\d+)\s+мин", raw)
    if m:
        return datetime.now(timezone.utc) - timedelta(minutes=int(m.group(1)))
    return datetime.now(timezone.utc)
