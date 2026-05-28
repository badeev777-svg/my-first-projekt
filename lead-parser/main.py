import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import POLL_INTERVAL_MINUTES, DEMO_MODE
from app.collector import run_collection
from app.database import init_db
from app.web.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(demo=DEMO_MODE)
    log.info("Database ready")

    if not DEMO_MODE:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            _collect,
            "interval",
            minutes=POLL_INTERVAL_MINUTES,
            id="collect",
            next_run_time=__import__("datetime").datetime.now(),
        )
        scheduler.start()
        log.info(f"Scheduler started, interval={POLL_INTERVAL_MINUTES}m")
    else:
        log.info("Demo mode: scheduler disabled")

    yield

    if not DEMO_MODE:
        scheduler.shutdown()


async def _collect():
    try:
        n = await run_collection()
        if n:
            log.info(f"Collected {n} new leads")
    except Exception as e:
        log.error(f"Collection error: {e}")


app = FastAPI(title="Lead Parser", lifespan=lifespan)
app.include_router(router)

portfolio_dir = Path(__file__).parent.parent / "my-portfolio"
if portfolio_dir.exists():
    app.mount("/", StaticFiles(directory=str(portfolio_dir), html=True), name="portfolio")
