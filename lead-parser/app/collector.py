"""Orchestrates all scrapers, saves new leads, sends notifications."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.analyzer import analyze_lead
from app.database import SessionLocal, Lead
from app.notifier import notify_new_lead
from app.scrapers.fl_rss import fetch_fl_leads
from app.scrapers.habr import fetch_habr_leads
from app.scrapers.kwork import fetch_kwork_leads
from app.scrapers.profi import fetch_profi_leads

log = logging.getLogger(__name__)


async def run_collection() -> int:
    raw: list[dict] = []
    log.info("Starting collection cycle")

    fl_leads = await fetch_fl_leads()
    raw.extend(fl_leads)

    # Habr RSS deprecated (410 Gone) — disabled 2026-05-30
    # habr_leads = await fetch_habr_leads()
    # raw.extend(habr_leads)

    kwork_leads = await fetch_kwork_leads()
    raw.extend(kwork_leads)

    profi_leads = await fetch_profi_leads()
    raw.extend(profi_leads)

    log.info(f"Total raw leads collected: {len(raw)}")
    saved = 0
    async with SessionLocal() as session:
        for data in raw:
            if not data.get("source_url"):
                continue

            existing = await session.scalar(
                select(Lead).where(Lead.source_url == data["source_url"])
            )
            if existing:
                continue

            lead = Lead(
                source=data["source"],
                source_url=data["source_url"],
                title=data.get("title"),
                text=data["text"],
                budget=data.get("budget"),
                contact=data.get("contact"),
                created_at=data.get("created_at") or datetime.now(timezone.utc),
                fetched_at=datetime.now(timezone.utc),
            )
            session.add(lead)
            try:
                await session.commit()
                await session.refresh(lead)
                saved += 1
                log.info(f"Saved lead #{lead.id}: {lead.title[:50]}")

                try:
                    analysis = await analyze_lead(
                        source=data["source"],
                        title=data.get("title"),
                        text=data["text"],
                        budget=data.get("budget")
                    )
                    if analysis:
                        lead.relevance_score = analysis.get("relevance_score")
                        lead.tags = analysis.get("tags")
                        lead.summary = analysis.get("summary")
                        lead.estimated_budget = analysis.get("estimated_budget")
                        lead.processed = True
                        await session.commit()
                        log.info(f"Analyzed lead #{lead.id}, relevance={lead.relevance_score}")
                        await notify_new_lead(data, relevance_score=lead.relevance_score)
                    else:
                        log.warning(f"Analysis returned None for lead #{lead.id}")
                        await notify_new_lead(data)
                except Exception as e:
                    log.error(f"Analysis/notification failed for lead #{lead.id}: {type(e).__name__}: {e}")
            except IntegrityError as e:
                log.error(f"IntegrityError while saving lead: {e}")
                await session.rollback()

    log.info(f"Collection cycle completed: {saved} new leads saved")
    return saved
