"""YouDo.com scraper via Playwright — logs in with YOUDO_LOGIN/YOUDO_PASSWORD
and parses open tasks in the "сайты и разработка" category.

Requires: pip install playwright && playwright install chromium
If playwright is not installed or credentials are missing, silently returns [].

NOTE: YouDo's DOM/selectors may change over time — this scraper uses several
selector fallbacks (same approach as profi.py) but may need updating if the
site layout changes.
"""
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from app.config import YOUDO_LOGIN, YOUDO_PASSWORD
from app.filter import matches_keywords, extract_budget, passes_budget, is_profile_or_resume

log = logging.getLogger(__name__)

LOGIN_URL = "https://youdo.com/login"

# Поисковые запросы на бирже YouDo
_QUERIES = [
    "разработка сайта",
    "создание сайта",
    "лендинг",
    "интернет-магазин",
    "верстка сайта",
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def fetch_youdo_leads() -> list[dict]:
    if not YOUDO_LOGIN or not YOUDO_PASSWORD:
        log.debug("YOUDO_LOGIN/YOUDO_PASSWORD not set — YouDo skipped")
        return []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.debug("playwright not installed — YouDo skipped. Run: pip install playwright && playwright install chromium")
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

            page = await ctx.new_page()
            logged_in = await _login(page)
            if not logged_in:
                log.error("YouDo: login failed, skipping collection")
                await browser.close()
                return []

            for query in _QUERIES:
                found = await _scrape_query(ctx, query, seen)
                leads.extend(found)

            await browser.close()

    except Exception as e:
        log.error(f"YouDo browser error: {type(e).__name__}: {e}")

    log.info(f"YouDo: {len(leads)} leads fetched")
    return leads


async def _login(page) -> bool:
    try:
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(1500)

        for selector in ["input[name='login']", "input[type='email']", "input[name='email']"]:
            field = await page.query_selector(selector)
            if field:
                await field.fill(YOUDO_LOGIN)
                break
        else:
            log.error("YouDo: login field not found")
            return False

        for selector in ["input[name='password']", "input[type='password']"]:
            field = await page.query_selector(selector)
            if field:
                await field.fill(YOUDO_PASSWORD)
                break
        else:
            log.error("YouDo: password field not found")
            return False

        for selector in ["button[type='submit']", "button:has-text('Войти')"]:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                break
        else:
            log.error("YouDo: submit button not found")
            return False

        await page.wait_for_timeout(3000)

        # Login succeeded if we're no longer on the login page
        return "login" not in page.url

    except Exception as e:
        log.error(f"YouDo login error: {type(e).__name__}: {e}")
        return False


async def _scrape_query(ctx, query: str, seen: set) -> list[dict]:
    url = f"https://youdo.com/tasks-all-all-1?q={quote(query)}"
    leads: list[dict] = []

    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(2000)

        leads = await _parse_dom(page, seen)
        await page.close()

    except Exception as e:
        log.warning(f"YouDo '{query}': {type(e).__name__}: {e}")

    return leads


async def _parse_dom(page, seen: set) -> list[dict]:
    leads: list[dict] = []

    for selector in [
        "[data-test-id='task-item']",
        "a[href*='/task/']",
        ".TaskCard",
        "article[class*='task']",
    ]:
        try:
            cards = await page.query_selector_all(selector)
        except Exception:
            continue
        if not cards:
            continue

        for card in cards[:30]:
            try:
                link_el = card if (await card.get_attribute("href")) else await card.query_selector("a[href*='/task/']")
                href = await link_el.get_attribute("href") if link_el else ""
                if not href:
                    continue
                source_url = href if href.startswith("http") else f"https://youdo.com{href}"
                if source_url in seen:
                    continue
                seen.add(source_url)

                text = (await card.inner_text()).strip()
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                title = lines[0][:100] if lines else "Заказ YouDo"

                if is_profile_or_resume(text):
                    continue
                if not matches_keywords(text):
                    continue

                budget = extract_budget(text)
                if not passes_budget(budget):
                    continue

                leads.append({
                    "source": "youdo",
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
