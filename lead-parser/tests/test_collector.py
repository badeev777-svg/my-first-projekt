import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, func

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app.collector as collector
from app.database import Base, Lead


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def patch_collector(monkeypatch, session_factory):
    monkeypatch.setattr(collector, "SessionLocal", session_factory)

    async def noop_notify(_lead):
        return None

    monkeypatch.setattr(collector, "notify_new_lead", noop_notify)


@pytest.mark.asyncio
async def test_run_collection_saves_fl_habr_and_telegram_leads(monkeypatch):
    async def fake_fl_leads():
        return [
            {
                "source": "fl",
                "source_url": "https://fl.ru/task/1",
                "title": "FL lead",
                "text": "Нужен сайт с бюджетом 50 тыс руб",
                "budget": 50000,
                "contact": None,
                "created_at": datetime.now(timezone.utc),
            }
        ]

    async def fake_habr_leads():
        return [
            {
                "source": "habr",
                "source_url": "https://freelance.habr.com/tasks/1",
                "title": "Habr lead",
                "text": "Создание лендинга с бюджетом 20 тыс руб",
                "budget": 20000,
                "contact": None,
                "created_at": datetime.now(timezone.utc),
            }
        ]

    async def fake_tg_leads():
        return [
            {
                "source": "telegram",
                "source_url": "https://t.me/example/1",
                "title": "Telegram lead",
                "text": "Требуется разработка сайта, бюджет 30 тыс руб",
                "budget": 30000,
                "contact": "@user",
                "created_at": datetime.now(timezone.utc),
            }
        ]

    monkeypatch.setattr(collector, "fetch_fl_leads", fake_fl_leads)
    monkeypatch.setattr(collector, "fetch_habr_leads", fake_habr_leads)
    monkeypatch.setattr(collector, "fetch_telegram_leads", fake_tg_leads)

    saved = await collector.run_collection()
    assert saved == 3

    async with collector.SessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(Lead))
        count = result.scalar_one()
        assert count == 3

    # Duplicate records should be skipped on second run
    saved_again = await collector.run_collection()
    assert saved_again == 0
