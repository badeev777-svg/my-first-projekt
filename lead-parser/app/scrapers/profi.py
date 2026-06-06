"""Profi.ru scraper via Playwright (JS-rendered SPA).

Requires: pip install playwright && playwright install chromium
If playwright is not installed, silently returns [].
"""
import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from app.filter import matches_keywords, extract_budget, passes_budget, is_profile_or_resume

log = logging.getLogger(__name__)

# Search queries sent to profi.ru/order/
_QUERIES = [
    "разработка сайта",
    "создание сайта",
    "лендинг",
    "интернет-магазин",
    "верстка",
    "SEO продвижение",
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def fetch_profi_leads() -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.debug("playwright not installed — Profi.ru skipped. Run: pip install playwright && playwright install chromium")
        return []

    leads: list[dict] = []
    seen: set[str] = set()

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            ctx = await browser.new_context(
                user_agent=_UA,
                locale="ru-RU",
                viewport={"width": 1280, "height": 800},
            )
            ctx.set_default_timeout(20_000)

            for query in _QUERIES:
                found = await _scrape_query(ctx, query, seen)
                leads.extend(found)

            await browser.close()

    except Exception as e:
        log.error(f"Profi.ru browser error: {type(e).__name__}: {e}")

    log.info(f"Profi.ru: {len(leads)} leads fetched")
    return leads


async def _scrape_query(ctx, query: str, seen: set) -> list[dict]:
    url = f"https://profi.ru/order/?q={quote(query)}"
    leads: list[dict] = []

    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30_000)

        # Try Next.js JSON payload first — avoids selector fragility
        raw = await page.evaluate("() => { const el = document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null; }")
        if raw:
            leads = _parse_nextjs(raw, seen)

        # Fallback: DOM extraction
        if not leads:
            leads = await _parse_dom(page, seen)

        await page.close()

    except Exception as e:
        log.warning(f"Profi.ru '{query}': {type(e).__name__}: {e}")

    return leads


def _parse_nextjs(raw: str, seen: set) -> list[dict]:
    leads: list[dict] = []
    try:
        data = json.loads(raw)
    except Exception:
        return []

    # Walk known paths where orders might live
    props = data.get("props", {}).get("pageProps", {})
    orders = (
        props.get("orders")
        or props.get("items")
        or props.get("data", {}).get("orders")
        or props.get("initialState", {}).get("orders")
        or []
    )
    if not isinstance(orders, list):
        return []

    for order in orders:
        if not isinstance(order, dict):
            continue

        order_id = order.get("id") or order.get("orderId") or order.get("slug")
        if not order_id:
            continue

        source_url = f"https://profi.ru/order/{order_id}/"
        if source_url in seen:
            continue
        seen.add(source_url)

        title = str(order.get("title") or order.get("name") or "Заказ Profi.ru")[:100]
        text = str(order.get("description") or order.get("text") or title)

        if is_profile_or_resume(text):
            continue
        if not matches_keywords(text):
            continue

        budget_raw = order.get("budget") or order.get("price") or order.get("priceMax")
        budget = int(budget_raw) if isinstance(budget_raw, (int, float)) else extract_budget(text)
        if not passes_budget(budget):
            continue

        created_at = _parse_dt(order.get("createdAt") or order.get("created_at") or order.get("date"))

        leads.append({
            "source": "profi",
            "source_url": source_url,
            "title": title[:512],
            "text": text,
            "budget": budget,
            "contact": None,
            "created_at": created_at,
        })

    return leads


async def _parse_dom(page, seen: set) -> list[dict]:
    """DOM-based fallback — tries common selector patterns."""
    leads: list[dict] = []

    # Profi.ru uses React; try data-attrs and class patterns
    for selector in [
        "[data-order-id]",
        "[data-qa='order-card']",
        ".order-card",
        ".order_card",
        "article[class*='Order']",
        "div[class*='orderItem']",
    ]:
        try:
            cards = await page.query_selector_all(selector)
        except Exception:
            continue
        if not cards:
            continue

        for card in cards[:30]:
            try:
                # resolve order id from link
                link_el = await card.query_selector("a[href*='/order/']")
                href = await link_el.get_attribute("href") if link_el else ""
                parts = [p for p in href.split("/") if p]
                order_id = parts[-1] if parts else ""
                if not order_id:
                    order_id = await card.get_attribute("data-order-id") or ""
                if not order_id:
                    continue

                source_url = f"https://profi.ru/order/{order_id}/"
                if source_url in seen:
                    continue
                seen.add(source_url)

                text = (await card.inner_text()).strip()
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                title = lines[0][:100] if lines else "Заказ Profi.ru"

                if is_profile_or_resume(text):
                    continue
                if not matches_keywords(text):
                    continue

                budget = extract_budget(text)
                if not passes_budget(budget):
                    continue

                leads.append({
                    "source": "profi",
                    "source_url": source_url,
                    "title": title[:512],
                    "text": text,
                    "budget": budget,
                    "contact": None,
                    "created_at": datetime.now(timezone.utc),
                })
            except Exception:
                continue
        break  # stop after first matching selector

    return leads


def _parse_dt(raw) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)
