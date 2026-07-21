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
async def test_run_turn_disables_filesystem_setting_sources(monkeypatch) -> None:
    """Regression test: without setting_sources=[], the SDK loads on-disk
    .claude/settings*.json from the target project dir, and can_use_tool is
    NOT invoked for tool calls already permitted by a permissions.allow rule
    there -- silently bypassing Telegram confirmation. Pinning
    setting_sources=[] makes can_use_tool the sole gate, always."""
    fake_messages = _FakeMessages(
        [
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

    captured_options = {}

    def fake_query(*, prompt, options):
        captured_options["options"] = options
        return fake_messages

    monkeypatch.setattr("app.agent_runner.query", fake_query)

    async def on_text(text: str) -> None:
        pass

    async def send_confirmation_prompt(correlation_id, tool_name, tool_input) -> None:
        raise AssertionError("no risky tool call expected in this test")

    bridge = ConfirmationBridge(timeout_seconds=5)
    await run_turn(
        prompt="почини баг",
        project_path="/root/projects/Aleks",
        session_id=None,
        confirmation_bridge=bridge,
        send_confirmation_prompt=send_confirmation_prompt,
        on_text=on_text,
    )

    assert captured_options["options"].setting_sources == []


@pytest.mark.asyncio
async def test_run_turn_scrubs_telegram_token_from_subprocess_env(monkeypatch) -> None:
    """TELEGRAM_BOT_TOKEN is never needed by the Claude Code CLI subprocess
    (it only talks to the Anthropic API and runs project tools), so it must
    not be exposed to Bash tool calls the agent makes.

    The installed claude_agent_sdk's SubprocessCLITransport.connect() (see
    _internal/transport/subprocess_cli.py, ~line 689) builds the child
    process env as::

        inherited_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        process_env = {**inherited_env, "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
                        **self._options.env, "CLAUDE_AGENT_SDK_VERSION": __version__}

    ``inherited_env`` is a full *independent copy* of this process's real
    os.environ, so merely omitting a key from ``options.env`` does nothing
    -- the real value still flows through from ``inherited_env`` unchanged.
    The only way to actually remove a key from the child's env is to
    override it in ``options.env`` with a replacement value. This test
    proves both halves: that ``options.env`` carries an explicit override,
    and -- by replaying the SDK's own merge formula against a fake
    os.environ containing the real secret -- that the resulting child env
    does NOT contain the real token value.

    NOTE: ANTHROPIC_API_KEY is deliberately NOT scrubbed here. That same
    CLI subprocess authenticates outbound to the Anthropic API using
    ANTHROPIC_API_KEY (see _internal/session_resume.py's
    ``opt_env.get("ANTHROPIC_API_KEY") or os.environ.get(...)`` fallback),
    and this deployment has no alternative credential (no
    CLAUDE_CODE_OAUTH_TOKEN, no keychain -- app/main.py's only auth path is
    the env var). Overriding it to blank would break the bot's ability to
    call Claude at all, so it cannot be scrubbed with the SDK version
    installed here without a larger architecture change (e.g. never
    putting it in this process's os.environ in the first place).
    TELEGRAM_BOT_TOKEN has no such conflict.
    """
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-tg-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-anthropic-key")
    monkeypatch.setenv("SOME_OTHER_VAR", "keep-me")

    fake_messages = _FakeMessages(
        [
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

    captured_options = {}

    def fake_query(*, prompt, options):
        captured_options["options"] = options
        return fake_messages

    monkeypatch.setattr("app.agent_runner.query", fake_query)

    async def on_text(text: str) -> None:
        pass

    async def send_confirmation_prompt(correlation_id, tool_name, tool_input) -> None:
        raise AssertionError("no risky tool call expected in this test")

    bridge = ConfirmationBridge(timeout_seconds=5)
    await run_turn(
        prompt="почини баг",
        project_path="/root/projects/Aleks",
        session_id=None,
        confirmation_bridge=bridge,
        send_confirmation_prompt=send_confirmation_prompt,
        on_text=on_text,
    )

    env = captured_options["options"].env

    # options.env must carry an *explicit override*, not merely omit the
    # key -- omission is a no-op against the SDK's inherited_env copy.
    assert env["TELEGRAM_BOT_TOKEN"] == ""
    assert env["SOME_OTHER_VAR"] == "keep-me"

    # Replay the SDK's own merge algebra (subprocess_cli.py ~line 689)
    # against a fake os.environ holding the real secret, to prove the
    # override actually wins in the real merge -- not just that our dict
    # looks right in isolation.
    fake_os_environ = {
        "TELEGRAM_BOT_TOKEN": "secret-tg-token",
        "ANTHROPIC_API_KEY": "secret-anthropic-key",
        "SOME_OTHER_VAR": "keep-me",
        "CLAUDECODE": "1",
    }
    inherited_env = {k: v for k, v in fake_os_environ.items() if k != "CLAUDECODE"}
    process_env = {
        **inherited_env,
        "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
        **env,
        "CLAUDE_AGENT_SDK_VERSION": "0.0.0",
    }

    assert process_env["TELEGRAM_BOT_TOKEN"] != "secret-tg-token"
    assert "secret-tg-token" not in process_env.values()


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


@pytest.mark.asyncio
async def test_risky_tool_timeout_returns_distinct_deny_message_and_notifies() -> None:
    bridge = ConfirmationBridge(timeout_seconds=0.05)
    notified = False

    async def send_prompt(correlation_id: str, tool_name: str, tool_input: dict) -> None:
        return None  # user never answers -> bridge times out

    async def on_confirmation_timeout() -> None:
        nonlocal notified
        notified = True

    can_use_tool = make_can_use_tool(bridge, send_prompt, on_confirmation_timeout)
    result = await can_use_tool(
        "Bash", {"command": "git push"}, ToolPermissionContext(tool_use_id="t4")
    )

    assert isinstance(result, PermissionResultDeny)
    assert "таймаут" in result.message.lower()
    assert notified is True


@pytest.mark.asyncio
async def test_risky_tool_explicit_rejection_keeps_original_deny_message() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)
    notified = False

    async def send_prompt(correlation_id: str, tool_name: str, tool_input: dict) -> None:
        bridge.resolve(correlation_id, False)

    async def on_confirmation_timeout() -> None:
        nonlocal notified
        notified = True

    can_use_tool = make_can_use_tool(bridge, send_prompt, on_confirmation_timeout)
    result = await can_use_tool(
        "Bash", {"command": "git push"}, ToolPermissionContext(tool_use_id="t5")
    )

    assert isinstance(result, PermissionResultDeny)
    assert result.message == "Отклонено пользователем в Telegram"
    assert notified is False
