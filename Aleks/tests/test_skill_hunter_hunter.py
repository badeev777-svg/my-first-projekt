import pytest

from app.skill_hunter.hunter import run
from app.skill_hunter.models import SkillCandidate


def _candidate(url: str, title: str = "Skill") -> SkillCandidate:
    return SkillCandidate(title=title, url=url, description="desc")


@pytest.mark.asyncio
async def test_run_sends_one_message_per_niche_with_fresh_candidates(tmp_path) -> None:
    history_path = str(tmp_path / "history.json")
    sent: list[str] = []

    async def send_message(text: str) -> None:
        sent.append(text)

    async def fake_find_candidates(niche: str) -> list[SkillCandidate]:
        return [_candidate(f"https://github.com/x/{niche}")]

    await run(
        ["niche-a", "niche-b"],
        history_path,
        send_message,
        find_candidates_fn=fake_find_candidates,
    )

    assert len(sent) == 2
    assert "niche-a" in sent[0]
    assert "niche-b" in sent[1]


@pytest.mark.asyncio
async def test_run_sends_nothing_when_niche_has_no_fresh_candidates(tmp_path) -> None:
    history_path = str(tmp_path / "history.json")
    sent: list[str] = []

    async def send_message(text: str) -> None:
        sent.append(text)

    async def fake_find_candidates(niche: str) -> list[SkillCandidate]:
        return []

    await run(["niche-a"], history_path, send_message, find_candidates_fn=fake_find_candidates)

    assert sent == []


@pytest.mark.asyncio
async def test_run_continues_after_one_niche_search_fails(tmp_path) -> None:
    history_path = str(tmp_path / "history.json")
    sent: list[str] = []

    async def send_message(text: str) -> None:
        sent.append(text)

    async def fake_find_candidates(niche: str) -> list[SkillCandidate]:
        if niche == "broken-niche":
            raise RuntimeError("boom")
        return [_candidate("https://github.com/x/ok")]

    await run(
        ["broken-niche", "ok-niche"],
        history_path,
        send_message,
        find_candidates_fn=fake_find_candidates,
    )

    assert len(sent) == 1
    assert "ok-niche" in sent[0]


@pytest.mark.asyncio
async def test_run_does_not_resend_same_skill_on_second_call(tmp_path) -> None:
    history_path = str(tmp_path / "history.json")
    sent: list[str] = []

    async def send_message(text: str) -> None:
        sent.append(text)

    async def fake_find_candidates(niche: str) -> list[SkillCandidate]:
        return [_candidate("https://github.com/x/stable")]

    await run(["niche-a"], history_path, send_message, find_candidates_fn=fake_find_candidates)
    await run(["niche-a"], history_path, send_message, find_candidates_fn=fake_find_candidates)

    assert len(sent) == 1  # second run found nothing new
