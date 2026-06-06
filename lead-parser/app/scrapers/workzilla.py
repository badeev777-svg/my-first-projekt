"""WorkZilla (work-zilla.com) scraper — parses recent tasks via httpx + BeautifulSoup.

NOTE: work-zilla.com does NOT expose open/active tasks to unauthenticated users.
The /tasks page shows recently COMPLETED tasks as portfolio examples.
These can still signal market demand, but are not open orders.
To get open tasks, login-based session scraping would be needed.

For now, this module is a no-op until a better source is found.
"""
import logging

log = logging.getLogger(__name__)


async def fetch_workzilla_leads() -> list[dict]:
    log.debug("WorkZilla: skipped — open tasks require authentication")
    return []
