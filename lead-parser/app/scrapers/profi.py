"""Profi.ru scraper — placeholder for future implementation.

Note: Profi.ru uses JavaScript rendering (SPA), so simple HTTP + BeautifulSoup
doesn't work. To implement this properly, we would need:
  - Playwright or Selenium (adds 500+ MB, slows collector)
  - Or find Profi.ru API (usually hidden in DevTools)
  - Or use Profi.ru RSS if available (currently not found)

For now, this returns empty list. When needed, upgrade with Playwright.
"""

async def fetch_profi_leads() -> list[dict]:
    """Fetch leads from Profi.ru. Currently disabled due to JS rendering."""
    # TODO: Implement with Playwright when volume justifies 500MB dep
    return []
