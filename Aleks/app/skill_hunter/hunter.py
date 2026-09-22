import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.skill_hunter import history
from app.skill_hunter.models import SkillCandidate
from app.skill_hunter.search import find_candidates

log = logging.getLogger(__name__)

SendMessage = Callable[[str], Awaitable[None]]


def _format_message(niche: str, candidates: list[SkillCandidate]) -> str:
    lines = [f"Новые скиллы для «{niche}»:"]
    for candidate in candidates:
        lines.append(f"- {candidate.title}\n  {candidate.description}\n  {candidate.url}")
    return "\n".join(lines)


async def run(
    niches: list[str],
    history_path: str,
    send_message: SendMessage,
    *,
    find_candidates_fn=find_candidates,
) -> None:
    now_iso = datetime.now(UTC).isoformat()
    for niche in niches:
        try:
            candidates = await find_candidates_fn(niche)
        except Exception:
            log.exception("skill_hunter: unexpected error searching niche=%s", niche)
            continue

        hist = await asyncio.to_thread(history.load_history, history_path)
        fresh = history.filter_new(hist, candidates)
        if not fresh:
            continue

        try:
            await send_message(_format_message(niche, fresh))
            await asyncio.to_thread(history.record, history_path, niche, fresh, now_iso)
        except Exception:
            log.exception("skill_hunter: failed to deliver/record digest for niche=%s", niche)
            continue
