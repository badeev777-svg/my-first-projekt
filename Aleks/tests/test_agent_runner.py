# tests/test_agent_runner.py
import pytest
from claude_agent_sdk import (
    AssistantMessage,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
)

from app.agent_runner import make_can_use_tool, run_turn
from app.confirmation import ConfirmationBridge


@pytest.mark.asyncio
async def test_safe_tool_allowed_without_confirmation() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)
    calls: list[str] = []

    async def send_prompt(correlation_id: str, tool_name: str, tool_input: dict) -> None:
        calls.append(correlation_id)

    can_use_tool = make_can_use_tool(bridge, send_prompt)
    result = await can_use_tool(
        "Read", {"file_path": "app/main.py"}, ToolPermissionContext(tool_use_id="t1")
    )

    assert isinstance(result, PermissionResultAllow)
    assert calls == []  # never asked


@pytest.mark.asyncio
async def test_risky_tool_allowed_after_approval() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)

    async def send_prompt(correlation_id: str, tool_name: str, tool_input: dict) -> None:
        bridge.resolve(correlation_id, True)

    can_use_tool = make_can_use_tool(bridge, send_prompt)
    result = await can_use_tool(
        "Bash", {"command": "git push"}, ToolPermissionContext(tool_use_id="t2")
    )

    assert isinstance(result, PermissionResultAllow)


@pytest.mark.asyncio
async def test_risky_tool_denied_after_rejection() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)

    async def send_prompt(correlation_id: str, tool_name: str, tool_input: dict) -> None:
        bridge.resolve(correlation_id, False)

    can_use_tool = make_can_use_tool(bridge, send_prompt)
    result = await can_use_tool(
        "Bash", {"command": "git push"}, ToolPermissionContext(tool_use_id="t3")
    )

    assert isinstance(result, PermissionResultDeny)
    assert result.message


# append to tests/test_agent_runner.py
from unittest.mock import AsyncMock

from claude_agent_sdk import ToolUseBlock


class _FakeMessages:
    def __init__(self, messages: list) -> None:
        self._messages = messages

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for message in self._messages:
            yield message


@pytest.mark.asyncio
async def test_run_turn_streams_text_and_returns_session_id(monkeypatch) -> None:
    fake_messages = _FakeMessages(
        [
            AssistantMessage(content=[TextBlock(text="Готово, запушил.")], model="claude"),
            ResultMessage(
                subtype="success",
                duration_ms=100,
                duration_api_ms=90,
                is_error=False,
                num_turns=1,
                session_id="new-session-id",
            ),
        ]
    )

    def fake_query(*, prompt, options):
        return fake_messages

    monkeypatch.setattr("app.agent_runner.query", fake_query)

    seen_text: list[str] = []

    async def on_text(text: str) -> None:
        seen_text.append(text)

    async def send_confirmation_prompt(correlation_id, tool_name, tool_input) -> None:
        raise AssertionError("no risky tool call expected in this test")

    bridge = ConfirmationBridge(timeout_seconds=5)
    session_id = await run_turn(
        prompt="запушь исправление",
        project_path="/root/projects/Aleks",
        session_id=None,
        confirmation_bridge=bridge,
        send_confirmation_prompt=send_confirmation_prompt,
        on_text=on_text,
    )

    assert seen_text == ["Готово, запушил."]
    assert session_id == "new-session-id"


@pytest.mark.asyncio
async def test_run_turn_returns_none_when_no_result_message(monkeypatch) -> None:
    fake_messages = _FakeMessages(
        [
            AssistantMessage(content=[TextBlock(text="Работаю...")], model="claude"),
        ]
    )

    def fake_query(*, prompt, options):
        return fake_messages

    monkeypatch.setattr("app.agent_runner.query", fake_query)

    seen_text: list[str] = []

    async def on_text(text: str) -> None:
        seen_text.append(text)

    async def send_confirmation_prompt(correlation_id, tool_name, tool_input) -> None:
        raise AssertionError("no risky tool call expected in this test")

    bridge = ConfirmationBridge(timeout_seconds=5)
    session_id = await run_turn(
        prompt="запушь исправление",
        project_path="/root/projects/Aleks",
        session_id=None,
        confirmation_bridge=bridge,
        send_confirmation_prompt=send_confirmation_prompt,
        on_text=on_text,
    )

    assert seen_text == ["Работаю..."]
    assert session_id is None
