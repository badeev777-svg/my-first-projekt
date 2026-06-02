"""Kwork.ru JSON API parser — парсит заказы через внутренний API биржи."""
import logging
import httpx
from datetime import datetime, timezone

from app.filter import extract_budget, passes_budget, is_profile_or_resume

log = logging.getLogger(__name__)

KWORK_URL = "https://kwork.ru/projects"

# Категории: 11=сайты/интернет, 28=дизайн, 38=SEO/реклама, 82=программирование
KWORK_CATEGORIES = [11, 28, 38, 82]

HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "sec-ch-ua-platform": "macOS",
    "sec-ch-ua-mobile": "?0",
    "Origin": "https://kwork.ru",
    "Referer": "https://kwork.ru/projects",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


async def fetch_kwork_leads() -> list[dict]:
    leads = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=HEADERS) as client:
        for cat_id in KWORK_CATEGORIES:
            try:
                resp = await client.post(KWORK_URL, data={"c": cat_id, "page": "1"})
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                log.warning(f"Kwork cat={cat_id} failed: {type(e).__name__}: {e}")
                continue

            wants = data.get("data", {}).get("wants", [])
            log.debug(f"Kwork cat={cat_id}: {len(wants)} total entries")

            for want in wants:
                title = (want.get("name") or "").strip()
                text = (want.get("description") or "").strip()
                full_text = f"{title}\n{text}"

                if is_profile_or_resume(full_text):
                    continue

                budget_raw = want.get("priceLimit")
                budget = int(float(budget_raw)) if budget_raw else extract_budget(full_text)

                if not passes_budget(budget):
                    continue

                want_id = want.get("id")
                source_url = f"https://kwork.ru/projects/{want_id}/view" if want_id else ""

                date_str = want.get("date_create", "")
                try:
                    created_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                except (ValueError, TypeError):
                    created_at = datetime.now(timezone.utc)

                leads.append(
                    {
                        "source": "kwork",
                        "source_url": source_url,
                        "title": title[:512],
                        "text": full_text,
                        "budget": budget,
                        "contact": None,
                        "created_at": created_at,
                    }
                )

    log.info(f"Kwork: {len(leads)} leads fetched")
    return leads
