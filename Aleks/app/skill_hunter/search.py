import asyncio
import json
import logging

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from app.skill_hunter.models import SkillCandidate

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 180.0

_SYSTEM_PROMPT = (
    "You are a research assistant hunting for Claude Code skills (SKILL.md-based "
    "extensions) relevant to a specific niche. Use WebSearch to find real, "
    "existing skills on GitHub or skills.sh/skillsmp.com published in the last "
    "year. Return ONLY a JSON array (no prose, no markdown fences) of up to 5 "
    "objects with keys \"title\", \"url\", \"description\" (one sentence each, "
    "in Russian). If you find nothing relevant, return an empty array []."
)


async def _collect_text(niche: str, options: ClaudeAgentOptions) -> list[str]:
    text_parts: list[str] = []
    async for message in query(prompt=niche, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
    return text_parts


async def find_candidates(
    niche: str, *, model: str = "sonnet", timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> list[SkillCandidate]:
    options = ClaudeAgentOptions(
        system_prompt=_SYSTEM_PROMPT,
        model=model,
        allowed_tools=["WebSearch"],
        setting_sources=[],
    )

    try:
        text_parts = await asyncio.wait_for(
            _collect_text(niche, options), timeout=timeout_seconds
        )
    except TimeoutError:
        log.warning("skill_hunter: search timed out for niche=%s", niche)
        return []
    except Exception:
        log.exception("skill_hunter: search failed for niche=%s", niche)
        return []

    raw = "".join(text_parts).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("skill_hunter: non-JSON response for niche=%s: %r", niche, raw[:200])
        return []

    if not isinstance(data, list):
        log.warning("skill_hunter: expected JSON array for niche=%s, got %s", niche, type(data))
        return []

    candidates: list[SkillCandidate] = []
    for item in data:
        try:
            candidates.append(SkillCandidate(**item))
        except (TypeError, ValueError) as exc:
            log.warning("skill_hunter: skipping malformed candidate for niche=%s: %s", niche, exc)
    return candidates
