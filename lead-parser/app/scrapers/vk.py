"""VK API scraper — читает посты из публичных групп с заказами."""
import logging
import httpx
from datetime import datetime, timezone

from app.config import VK_TOKEN, VK_GROUPS
from app.filter import matches_keywords, extract_budget, passes_budget, is_profile_or_resume

log = logging.getLogger(__name__)

VK_API = "https://api.vk.com/method/wall.get"
VK_VERSION = "5.199"


async def fetch_vk_leads() -> list[dict]:
    if not VK_TOKEN or not VK_GROUPS:
        log.debug("VK_TOKEN or VK_GROUPS not configured, skipping")
        return []

    leads = []
    async with httpx.AsyncClient(timeout=15) as client:
        for group in VK_GROUPS:
            try:
                resp = await client.get(VK_API, params={
                    "domain": group,
                    "count": 50,
                    "filter": "owner",
                    "v": VK_VERSION,
                    "access_token": VK_TOKEN,
                })
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                log.warning(f"VK group '{group}' failed: {type(e).__name__}: {e}")
                continue

            if "error" in data:
                log.warning(f"VK API error for '{group}': {data['error'].get('error_msg')}")
                continue

            items = data.get("response", {}).get("items", [])
            group_leads = 0
            for post in items:
                text = post.get("text", "")
                if not text:
                    continue

                # пропускаем репосты без текста
                if post.get("marked_as_ads"):
                    continue

                title = text[:100].replace("\n", " ")
                full_text = text

                if is_profile_or_resume(full_text):
                    continue

                if not matches_keywords(full_text):
                    continue

                budget = extract_budget(full_text)
                if not passes_budget(budget):
                    continue

                owner_id = post.get("owner_id", 0)
                post_id = post.get("id", 0)
                source_url = f"https://vk.com/wall{owner_id}_{post_id}"

                created_at = datetime.fromtimestamp(
                    post.get("date", 0), tz=timezone.utc
                )

                leads.append({
                    "source": "vk",
                    "source_url": source_url,
                    "title": title[:512],
                    "text": full_text,
                    "budget": budget,
                    "contact": None,
                    "created_at": created_at,
                })
                group_leads += 1

            log.info(f"VK '{group}': {group_leads} leads")

    log.info(f"VK total: {len(leads)} leads fetched")
    return leads
