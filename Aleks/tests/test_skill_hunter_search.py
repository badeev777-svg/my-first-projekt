import pytest
from claude_agent_sdk import AssistantMessage, TextBlock

from app.skill_hunter.search import find_candidates


class _FakeMessages:
    def __init__(self, messages: list) -> None:
        self._messages = messages

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for message in self._messages:
            yield message


@pytest.mark.asyncio
async def test_find_candidates_parses_json_array_response(monkeypatch) -> None:
    payload = (
        '[{"title": "FastAPI Helper", "url": "https://github.com/x/fastapi-helper", '
        '"description": "Scaffolds FastAPI routes."}]'
    )
    fake_messages = _FakeMessages([AssistantMessage(content=[TextBlock(text=payload)], model="claude")])

    def fake_query(*, prompt, options):
        return fake_messages

    monkeypatch.setattr("app.skill_hunter.search.query", fake_query)

    candidates = await find_candidates("Python/FastAPI")

    assert len(candidates) == 1
    assert candidates[0].title == "FastAPI Helper"
    assert candidates[0].url == "https://github.com/x/fastapi-helper"


@pytest.mark.asyncio
async def test_find_candidates_returns_empty_list_on_empty_json_array(monkeypatch) -> None:
    fake_messages = _FakeMessages([AssistantMessage(content=[TextBlock(text="[]")], model="claude")])
    monkeypatch.setattr("app.skill_hunter.search.query", lambda *, prompt, options: fake_messages)

    candidates = await find_candidates("Obscure niche")

    assert candidates == []


@pytest.mark.asyncio
async def test_find_candidates_returns_empty_list_on_non_json_response(monkeypatch) -> None:
    fake_messages = _FakeMessages(
        [AssistantMessage(content=[TextBlock(text="Sorry, I couldn't search right now.")], model="claude")]
    )
    monkeypatch.setattr("app.skill_hunter.search.query", lambda *, prompt, options: fake_messages)

    candidates = await find_candidates("Python/FastAPI")

    assert candidates == []


@pytest.mark.asyncio
async def test_find_candidates_returns_empty_list_when_query_raises(monkeypatch) -> None:
    def fake_query(*, prompt, options):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.skill_hunter.search.query", fake_query)

    candidates = await find_candidates("Python/FastAPI")

    assert candidates == []


@pytest.mark.asyncio
async def test_find_candidates_skips_malformed_items_keeps_valid_ones(monkeypatch) -> None:
    payload = (
        '[{"title": "Good", "url": "https://github.com/x/good", "description": "d"}, '
        '{"title": "Missing url"}]'
    )
    fake_messages = _FakeMessages([AssistantMessage(content=[TextBlock(text=payload)], model="claude")])
    monkeypatch.setattr("app.skill_hunter.search.query", lambda *, prompt, options: fake_messages)

    candidates = await find_candidates("Python/FastAPI")

    assert len(candidates) == 1
    assert candidates[0].title == "Good"


@pytest.mark.asyncio
async def test_find_candidates_allows_websearch_tool_only(monkeypatch) -> None:
    fake_messages = _FakeMessages([AssistantMessage(content=[TextBlock(text="[]")], model="claude")])
    captured = {}

    def fake_query(*, prompt, options):
        captured["options"] = options
        return fake_messages

    monkeypatch.setattr("app.skill_hunter.search.query", fake_query)

    await find_candidates("Python/FastAPI")

    assert captured["options"].allowed_tools == ["WebSearch"]
    assert captured["options"].setting_sources == []
