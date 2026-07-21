# Личный coding-агент на VPS (Telegram + Claude Agent SDK) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Telegram-бот на выделенной VPS, который через Claude Agent SDK читает/пишет код во всех проектах пользователя, запрашивает подтверждение рискованных действий inline-кнопками в Telegram и переживает рестарты процесса благодаря персистентным сессиям на проект.

**Architecture:** `python-telegram-bot` (long polling) принимает сообщения и решает, какой проект активен для пользователя; каждое сообщение превращается в один вызов `claude_agent_sdk.query()` с `cwd` проекта и `resume=<сохранённый session_id>`; `can_use_tool` hook классифицирует вызовы инструментов как risky/safe и для risky — блокирует выполнение, пока пользователь не нажмёт ✅/❌ в Telegram (мост через `asyncio.Future`, ключ — `correlation_id`). Состояние (активный проект на пользователя, `session_id` на проект) хранится в SQLite и переживает рестарт systemd-сервиса.

**Tech Stack:** Python ≥3.11, `python-telegram-bot>=21.0`, `claude-agent-sdk`, `pydantic>=2.5` + `pydantic-settings>=2.1`, `aiosqlite`, `python-dotenv`, `tenacity`; тесты — `pytest`, `pytest-asyncio`, `pytest-mock`.

**Spec:** `docs/superpowers/specs/2026-07-21-server-agent-design.md`

---

## File Structure

```
Aleks/
  pyproject.toml
  .env.example
  app/
    __init__.py
    config.py                    # Settings (pydantic-settings) + get_settings()
    risk.py                      # is_risky(tool_name, tool_input) -> bool
    state.py                     # StateStore (aiosqlite): active project + per-project session_id
    confirmation.py              # ConfirmationBridge: correlation_id -> asyncio.Future bridge
    agent_runner.py              # make_can_use_tool() + run_turn(): wraps claude_agent_sdk.query()
    bot/
      __init__.py
      handlers/
        __init__.py
        project.py                # /project, /projects commands
        confirm.py                 # callback_query handler for ✅/❌ buttons
        chat.py                     # plain-text handler: runs one agent turn
    main.py                        # entrypoint: builds Application, wires handlers, run_polling()
  tests/
    __init__.py
    test_risk.py
    test_state.py
    test_confirmation.py
    test_agent_runner.py
    test_bot_project_handler.py
    test_bot_confirm_handler.py
    test_bot_chat_handler.py
  deploy/
    aleks-agent.service            # systemd unit
```

Each module has one responsibility: `risk.py` never touches Telegram or the SDK; `confirmation.py` never touches Telegram directly (it takes a `send_prompt` callback); `agent_runner.py` never touches Telegram; `bot/handlers/*.py` never talk to the SDK directly — they call `agent_runner.run_turn`. This keeps everything except the three handler modules testable without mocking Telegram or Anthropic's API at all.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/bot/__init__.py`
- Create: `app/bot/handlers/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "aleks-agent"
version = "0.1.0"
description = "Личный coding-агент на VPS, управляемый через Telegram (Claude Agent SDK)"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "python-telegram-bot>=21.0",
    "claude-agent-sdk>=0.1.0",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "python-dotenv>=1.0",
    "aiosqlite>=0.19",
    "tenacity>=8.2",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 2: Create `.env.example`**

```
TELEGRAM_BOT_TOKEN=123456:your-bot-father-token
ALLOWED_USER_ID=123456789
ANTHROPIC_API_KEY=sk-ant-your-key
PROJECTS={"aleks": "/root/projects/Aleks", "content-agent-bot": "/root/projects/content-agent-bot"}
CONFIRMATION_TIMEOUT_SECONDS=600
DB_PATH=state.db
LOG_LEVEL=INFO
```

- [ ] **Step 3: Create empty package markers**

```bash
mkdir -p app/bot/handlers tests
touch app/__init__.py app/bot/__init__.py app/bot/handlers/__init__.py tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -e ".[dev]"` (or `uv sync` if the VPS/local env uses `uv`)
Expected: dependencies resolve without error.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example app/__init__.py app/bot/__init__.py app/bot/handlers/__init__.py tests/__init__.py
git commit -m "chore: scaffold aleks-agent project"
```

---

## Task 2: Risk classifier

**Files:**
- Create: `app/risk.py`
- Test: `tests/test_risk.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_risk.py
import pytest

from app.risk import is_risky


@pytest.mark.parametrize(
    ("tool_name", "tool_input", "expected"),
    [
        ("Bash", {"command": "git push origin main"}, True),
        ("Bash", {"command": "git commit --amend -m x"}, True),
        ("Bash", {"command": "rm -rf /var/www/app"}, True),
        ("Bash", {"command": "sudo systemctl restart nginx"}, True),
        ("Bash", {"command": "docker compose up -d"}, True),
        ("Bash", {"command": "bash deploy.sh"}, True),
        ("Bash", {"command": "git diff"}, False),
        ("Bash", {"command": "git commit -m 'wip'"}, False),
        ("Bash", {"command": "ls -la"}, False),
        ("Write", {"file_path": "/root/projects/Aleks/.env"}, True),
        ("Write", {"file_path": "/root/projects/Aleks/credentials.json"}, True),
        ("Edit", {"file_path": "/root/projects/Aleks/secrets/token.pem"}, True),
        ("Write", {"file_path": "/root/projects/Aleks/app/main.py"}, False),
        ("Read", {"file_path": "/root/projects/Aleks/.env"}, False),
        ("Glob", {"pattern": "**/*.py"}, False),
    ],
)
def test_is_risky(tool_name: str, tool_input: dict, expected: bool) -> None:
    assert is_risky(tool_name, tool_input) is expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_risk.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.risk'`

- [ ] **Step 3: Write the implementation**

```python
# app/risk.py
import re

_RISKY_BASH_PATTERNS = [
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+commit\b.*--amend"),
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bdocker\b"),
    re.compile(r"\bsystemctl\s+(restart|stop)\b"),
    re.compile(r"deploy"),
]

_RISKY_PATH_PATTERNS = [
    re.compile(r"\.env(\.|$)"),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"secrets", re.IGNORECASE),
    re.compile(r"\.pem$"),
]

_RISKY_WRITE_TOOLS = {"Write", "Edit"}


def is_risky(tool_name: str, tool_input: dict) -> bool:
    """Decide whether a tool call needs Telegram confirmation before running."""
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        return any(pattern.search(command) for pattern in _RISKY_BASH_PATTERNS)
    if tool_name in _RISKY_WRITE_TOOLS:
        path = str(tool_input.get("file_path", ""))
        return any(pattern.search(path) for pattern in _RISKY_PATH_PATTERNS)
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_risk.py -v`
Expected: PASS (15 passed)

- [ ] **Step 5: Commit**

```bash
git add app/risk.py tests/test_risk.py
git commit -m "feat: add risky tool-call classifier"
```

---

## Task 3: Config

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from app.config import Settings


def test_settings_parses_projects_mapping_from_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("PROJECTS", '{"aleks": "/root/projects/Aleks"}')

    settings = Settings(_env_file=None)

    assert settings.telegram_bot_token == "test-token"
    assert settings.allowed_user_id == 42
    assert settings.projects == {"aleks": "/root/projects/Aleks"}
    assert settings.confirmation_timeout_seconds == 600.0
    assert settings.db_path == "state.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Write the implementation**

```python
# app/config.py
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., description="Token from @BotFather")
    allowed_user_id: int = Field(..., description="Telegram user id of the owner")
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude Agent SDK")
    projects: dict[str, str] = Field(
        default_factory=dict,
        description="Project name -> absolute path on the VPS",
    )
    confirmation_timeout_seconds: float = Field(default=600.0, ge=1)
    db_path: str = Field(default="state.db")
    log_level: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add pydantic-settings config"
```

---

## Task 4: State store

**Files:**
- Create: `app/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_state.py
import pytest

from app.state import StateStore


@pytest.mark.asyncio
async def test_active_project_roundtrip(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()

    assert await store.get_active_project(user_id=1) is None

    await store.set_active_project(user_id=1, project="aleks")
    assert await store.get_active_project(user_id=1) == "aleks"

    await store.set_active_project(user_id=1, project="lead-parser")
    assert await store.get_active_project(user_id=1) == "lead-parser"


@pytest.mark.asyncio
async def test_session_id_roundtrip(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()

    assert await store.get_session_id("aleks") is None

    await store.set_session_id("aleks", "session-a")
    assert await store.get_session_id("aleks") == "session-a"

    await store.set_session_id("aleks", "session-b")
    assert await store.get_session_id("aleks") == "session-b"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.state'`

- [ ] **Step 3: Write the implementation**

```python
# app/state.py
import aiosqlite


class StateStore:
    """Persists the active project per Telegram user and the resumable
    Claude Agent SDK session_id per project, so context survives restarts."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS active_project ("
                "user_id INTEGER PRIMARY KEY, project TEXT NOT NULL)"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS project_session ("
                "project TEXT PRIMARY KEY, session_id TEXT NOT NULL)"
            )
            await db.commit()

    async def get_active_project(self, user_id: int) -> str | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT project FROM active_project WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_active_project(self, user_id: int, project: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO active_project (user_id, project) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET project = excluded.project",
                (user_id, project),
            )
            await db.commit()

    async def get_session_id(self, project: str) -> str | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT session_id FROM project_session WHERE project = ?", (project,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_session_id(self, project: str, session_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO project_session (project, session_id) VALUES (?, ?) "
                "ON CONFLICT(project) DO UPDATE SET session_id = excluded.session_id",
                (project, session_id),
            )
            await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/state.py tests/test_state.py
git commit -m "feat: add SQLite-backed state store for active project and session ids"
```

---

## Task 5: Confirmation bridge

**Files:**
- Create: `app/confirmation.py`
- Test: `tests/test_confirmation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_confirmation.py
import asyncio

import pytest

from app.confirmation import ConfirmationBridge


@pytest.mark.asyncio
async def test_resolve_approved_before_timeout() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)

    async def send_prompt(correlation_id: str) -> None:
        bridge.resolve(correlation_id, True)

    approved = await bridge.request("corr-1", send_prompt)

    assert approved is True
    assert "corr-1" not in bridge.pending


@pytest.mark.asyncio
async def test_resolve_denied_before_timeout() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)

    async def send_prompt(correlation_id: str) -> None:
        bridge.resolve(correlation_id, False)

    approved = await bridge.request("corr-2", send_prompt)

    assert approved is False


@pytest.mark.asyncio
async def test_auto_deny_on_timeout() -> None:
    bridge = ConfirmationBridge(timeout_seconds=0.05)

    async def send_prompt(correlation_id: str) -> None:
        return None  # user never answers

    approved = await bridge.request("corr-3", send_prompt)

    assert approved is False
    assert "corr-3" not in bridge.pending


@pytest.mark.asyncio
async def test_resolve_unknown_correlation_id_is_noop() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)
    bridge.resolve("does-not-exist", True)  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_confirmation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.confirmation'`

- [ ] **Step 3: Write the implementation**

```python
# app/confirmation.py
import asyncio
from collections.abc import Awaitable, Callable


class ConfirmationBridge:
    """Bridges canUseTool's synchronous-looking wait to an async Telegram
    button press. `send_prompt` is responsible for actually delivering the
    confirmation message; this class only tracks the pending Future."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.pending: dict[str, asyncio.Future[bool]] = {}

    async def request(
        self,
        correlation_id: str,
        send_prompt: Callable[[str], Awaitable[None]],
    ) -> bool:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self.pending[correlation_id] = future
        try:
            await send_prompt(correlation_id)
            return await asyncio.wait_for(future, timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            return False
        finally:
            self.pending.pop(correlation_id, None)

    def resolve(self, correlation_id: str, approved: bool) -> None:
        future = self.pending.get(correlation_id)
        if future is not None and not future.done():
            future.set_result(approved)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_confirmation.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/confirmation.py tests/test_confirmation.py
git commit -m "feat: add Telegram confirmation bridge with timeout auto-deny"
```

---

## Task 6: Agent runner (Claude Agent SDK wiring)

**Files:**
- Create: `app/agent_runner.py`
- Test: `tests/test_agent_runner.py`

This is the only module that imports `claude_agent_sdk`. It exposes two testable seams: `make_can_use_tool()` (pure decision logic, no SDK streaming involved) and `run_turn()` (streams a `query()` call, which the test monkeypatches).

- [ ] **Step 1: Write the failing test for `make_can_use_tool`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.agent_runner'`

- [ ] **Step 3: Write `make_can_use_tool` and the `run_turn` skeleton**

```python
# app/agent_runner.py
import uuid
from collections.abc import Awaitable, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    query,
)

from app.confirmation import ConfirmationBridge
from app.risk import is_risky

SendConfirmationPrompt = Callable[[str, str, dict], Awaitable[None]]
OnText = Callable[[str], Awaitable[None]]


def make_can_use_tool(
    confirmation_bridge: ConfirmationBridge,
    send_confirmation_prompt: SendConfirmationPrompt,
):
    async def can_use_tool(
        tool_name: str, input_data: dict, context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        if not is_risky(tool_name, input_data):
            return PermissionResultAllow(updated_input=input_data)

        correlation_id = context.tool_use_id or str(uuid.uuid4())

        async def _send(correlation_id: str) -> None:
            await send_confirmation_prompt(correlation_id, tool_name, input_data)

        approved = await confirmation_bridge.request(correlation_id, _send)
        if approved:
            return PermissionResultAllow(updated_input=input_data)
        return PermissionResultDeny(message="Отклонено пользователем в Telegram")

    return can_use_tool


async def run_turn(
    prompt: str,
    project_path: str,
    session_id: str | None,
    confirmation_bridge: ConfirmationBridge,
    send_confirmation_prompt: SendConfirmationPrompt,
    on_text: OnText,
) -> str:
    """Runs exactly one query() turn against a project and returns the
    session_id to persist for the next call's resume=."""
    options = ClaudeAgentOptions(
        cwd=project_path,
        resume=session_id,
        system_prompt={"type": "preset", "preset": "claude_code"},
        can_use_tool=make_can_use_tool(confirmation_bridge, send_confirmation_prompt),
    )

    new_session_id = session_id or ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    await on_text(block.text)
        elif isinstance(message, ResultMessage):
            new_session_id = message.session_id
    return new_session_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent_runner.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Write the failing test for `run_turn` streaming**

```python
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
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_agent_runner.py -v`
Expected: FAIL — `AssistantMessage`/`ResultMessage` construction may reject unexpected kwargs, or the monkeypatch target doesn't exist yet if `query` wasn't imported by name. Adjust the fake message construction to match the installed `claude_agent_sdk` version's exact required fields if the dataclass rejects extras (`TypeError: __init__() got an unexpected keyword argument`) — drop fields not accepted, keep `subtype`, `is_error`, `session_id`, `result` at minimum since those are what `run_turn` reads.

- [ ] **Step 7: Confirm it passes**

Run: `pytest tests/test_agent_runner.py -v`
Expected: PASS (4 passed)

- [ ] **Step 8: Commit**

```bash
git add app/agent_runner.py tests/test_agent_runner.py
git commit -m "feat: wire Claude Agent SDK query() with risk-gated can_use_tool"
```

---

## Task 7: Telegram bot handlers

**Files:**
- Create: `app/bot/handlers/project.py`
- Create: `app/bot/handlers/confirm.py`
- Create: `app/bot/handlers/chat.py`
- Test: `tests/test_bot_project_handler.py`
- Test: `tests/test_bot_confirm_handler.py`
- Test: `tests/test_bot_chat_handler.py`

### 7a. `/project` and `/projects` commands

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bot_project_handler.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.project import cmd_project, cmd_projects
from app.config import Settings
from app.state import StateStore


def _settings() -> Settings:
    return Settings(
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="k",
        projects={"aleks": "/root/projects/Aleks", "lead-parser": "/root/projects/lead-parser"},
        _env_file=None,
    )


def _update(user_id: int, args: list[str] | None = None):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = args or []
    context.bot_data = {"settings": _settings(), "state": AsyncMock(spec=StateStore)}
    return update, context


@pytest.mark.asyncio
async def test_cmd_projects_lists_configured_projects() -> None:
    update, context = _update(user_id=42)

    await cmd_projects(update, context)

    text = update.message.reply_text.call_args.args[0]
    assert "aleks" in text
    assert "lead-parser" in text


@pytest.mark.asyncio
async def test_cmd_projects_ignores_unauthorized_user() -> None:
    update, context = _update(user_id=999)

    await cmd_projects(update, context)

    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_project_rejects_unknown_name() -> None:
    update, context = _update(user_id=42, args=["not-a-project"])

    await cmd_project(update, context)

    text = update.message.reply_text.call_args.args[0]
    assert "aleks" in text
    context.bot_data["state"].set_active_project.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_project_sets_active_project() -> None:
    update, context = _update(user_id=42, args=["aleks"])

    await cmd_project(update, context)

    context.bot_data["state"].set_active_project.assert_awaited_once_with(42, "aleks")
    text = update.message.reply_text.call_args.args[0]
    assert "aleks" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot_project_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.bot.handlers.project'`

- [ ] **Step 3: Write the implementation**

```python
# app/bot/handlers/project.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import Settings
from app.state import StateStore


def _is_authorized(update: Update, allowed_user_id: int) -> bool:
    user = update.effective_user
    return user is not None and user.id == allowed_user_id


def _project_list_text(settings: Settings) -> str:
    names = "\n".join(f"- {name}" for name in sorted(settings.projects))
    return f"Доступные проекты:\n{names}"


async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _is_authorized(update, settings.allowed_user_id):
        return
    await update.message.reply_text(_project_list_text(settings))


async def cmd_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _is_authorized(update, settings.allowed_user_id):
        return

    args = context.args
    if not args or args[0] not in settings.projects:
        await update.message.reply_text(
            f"Укажи один из доступных проектов:\n{_project_list_text(settings)}"
        )
        return

    project = args[0]
    state: StateStore = context.bot_data["state"]
    await state.set_active_project(update.effective_user.id, project)
    await update.message.reply_text(f"Активный проект: {project}")


def register(app: Application) -> None:
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("project", cmd_project))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bot_project_handler.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/bot/handlers/project.py tests/test_bot_project_handler.py
git commit -m "feat: add /project and /projects Telegram commands"
```

### 7b. Confirmation button callback

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bot_confirm_handler.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.confirm import on_confirmation_callback
from app.confirmation import ConfirmationBridge


def _update(data: str):
    update = MagicMock()
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    context = MagicMock()
    bridge = ConfirmationBridge(timeout_seconds=5)
    context.bot_data = {"confirmation_bridge": bridge}
    return update, context, bridge


@pytest.mark.asyncio
async def test_approve_resolves_bridge_true() -> None:
    update, context, bridge = _update("corr-1:yes")
    future = bridge.pending["corr-1"] = __import__("asyncio").get_event_loop().create_future()

    await on_confirmation_callback(update, context)

    assert future.result() is True
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)


@pytest.mark.asyncio
async def test_reject_resolves_bridge_false() -> None:
    update, context, bridge = _update("corr-2:no")
    future = bridge.pending["corr-2"] = __import__("asyncio").get_event_loop().create_future()

    await on_confirmation_callback(update, context)

    assert future.result() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot_confirm_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.bot.handlers.confirm'`

- [ ] **Step 3: Write the implementation**

```python
# app/bot/handlers/confirm.py
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from app.confirmation import ConfirmationBridge


async def on_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    correlation_id, _, decision = query.data.partition(":")
    bridge: ConfirmationBridge = context.bot_data["confirmation_bridge"]
    bridge.resolve(correlation_id, decision == "yes")
    await query.edit_message_reply_markup(reply_markup=None)


def register(app: Application) -> None:
    app.add_handler(
        CallbackQueryHandler(on_confirmation_callback, pattern=r"^[^:]+:(yes|no)$")
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bot_confirm_handler.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/bot/handlers/confirm.py tests/test_bot_confirm_handler.py
git commit -m "feat: resolve confirmation bridge from Telegram button callback"
```

### 7c. Plain-text message handler (runs one agent turn)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bot_chat_handler.py
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers import chat as chat_module
from app.config import Settings
from app.confirmation import ConfirmationBridge


def _settings() -> Settings:
    return Settings(
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="k",
        projects={"aleks": "/root/projects/Aleks"},
        _env_file=None,
    )


def _update_and_context(text: str = "почини баг", user_id: int = 42):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = 100
    update.message.text = text
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot.send_message = AsyncMock()
    state = AsyncMock()
    state.get_active_project.return_value = "aleks"
    state.get_session_id.return_value = None
    context.bot_data = {
        "settings": _settings(),
        "state": state,
        "confirmation_bridge": ConfirmationBridge(timeout_seconds=5),
        "project_locks": {},
    }
    return update, context, state


@pytest.mark.asyncio
async def test_ignores_unauthorized_user() -> None:
    update, context, _ = _update_and_context(user_id=999)

    await chat_module.on_text_message(update, context)

    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_prompts_to_pick_project_when_none_active() -> None:
    update, context, state = _update_and_context()
    state.get_active_project.return_value = None

    await chat_module.on_text_message(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "/projects" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_replies_busy_when_project_locked() -> None:
    update, context, _ = _update_and_context()
    lock = asyncio.Lock()
    await lock.acquire()
    context.bot_data["project_locks"]["aleks"] = lock

    await chat_module.on_text_message(update, context)

    text = update.message.reply_text.call_args.args[0]
    assert "ещё работаю" in text.lower()


@pytest.mark.asyncio
async def test_happy_path_runs_turn_and_saves_session_id(monkeypatch) -> None:
    update, context, state = _update_and_context()

    async def fake_run_turn(**kwargs):
        await kwargs["on_text"]("Готово")
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    context.bot.send_message.assert_awaited_once_with(chat_id=100, text="Готово")
    state.set_session_id.assert_awaited_once_with("aleks", "session-xyz")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot_chat_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.bot.handlers.chat'`

- [ ] **Step 3: Write the implementation**

```python
# app/bot/handlers/chat.py
import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from app.agent_runner import run_turn
from app.config import Settings
from app.confirmation import ConfirmationBridge
from app.state import StateStore

log = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


def _describe_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "Bash":
        return f"Bash: {tool_input.get('command', '')}"
    if tool_name in ("Write", "Edit"):
        return f"{tool_name}: {tool_input.get('file_path', '')}"
    return f"{tool_name}: {tool_input}"


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    user = update.effective_user
    if user is None or update.message is None or user.id != settings.allowed_user_id:
        return

    state: StateStore = context.bot_data["state"]
    project = await state.get_active_project(user.id)
    if project is None:
        await update.message.reply_text("Сначала выбери проект: /projects")
        return

    locks: dict[str, asyncio.Lock] = context.bot_data["project_locks"]
    lock = locks.setdefault(project, asyncio.Lock())
    if lock.locked():
        await update.message.reply_text(
            f"Ещё работаю над предыдущим запросом для {project}, подожди."
        )
        return

    async with lock:
        bridge: ConfirmationBridge = context.bot_data["confirmation_bridge"]
        chat_id = update.effective_chat.id

        async def send_confirmation_prompt(
            correlation_id: str, tool_name: str, tool_input: dict
        ) -> None:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Разрешить", callback_data=f"{correlation_id}:yes"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"{correlation_id}:no"),
                    ]
                ]
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Подтверди действие:\n{_describe_tool(tool_name, tool_input)}",
                reply_markup=keyboard,
            )

        async def on_text(text: str) -> None:
            for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
                await context.bot.send_message(
                    chat_id=chat_id, text=text[i : i + TELEGRAM_MESSAGE_LIMIT]
                )

        session_id = await state.get_session_id(project)
        project_path = settings.projects[project]

        try:
            new_session_id = await run_turn(
                prompt=update.message.text,
                project_path=project_path,
                session_id=session_id,
                confirmation_bridge=bridge,
                send_confirmation_prompt=send_confirmation_prompt,
                on_text=on_text,
            )
        except Exception:
            log.exception("agent turn failed for project %s", project)
            await update.message.reply_text("Не получилось выполнить запрос, попробуй позже.")
            return

        if new_session_id:
            await state.set_session_id(project, new_session_id)


def register(app: Application) -> None:
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bot_chat_handler.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/bot/handlers/chat.py tests/test_bot_chat_handler.py
git commit -m "feat: run one agent turn per Telegram message with lock + streaming"
```

---

## Task 8: Entrypoint

**Files:**
- Create: `app/main.py`

No new unit test — this task wires already-tested components together; correctness is verified by the Task 9 manual smoke test.

- [ ] **Step 1: Write `app/main.py`**

```python
# app/main.py
import logging
import os

from telegram.ext import Application

from app.bot.handlers import chat as chat_handler
from app.bot.handlers import confirm as confirm_handler
from app.bot.handlers import project as project_handler
from app.config import get_settings
from app.confirmation import ConfirmationBridge
from app.state import StateStore


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    log = logging.getLogger(__name__)

    # claude_agent_sdk reads ANTHROPIC_API_KEY from the process environment.
    os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    state = StateStore(settings.db_path)
    confirmation_bridge = ConfirmationBridge(timeout_seconds=settings.confirmation_timeout_seconds)

    async def post_init(application: Application) -> None:
        await state.init()

    app = Application.builder().token(settings.telegram_bot_token).post_init(post_init).build()
    app.bot_data["settings"] = settings
    app.bot_data["state"] = state
    app.bot_data["confirmation_bridge"] = confirmation_bridge
    app.bot_data["project_locks"] = {}

    project_handler.register(app)
    confirm_handler.register(app)
    chat_handler.register(app)

    log.info("Aleks agent bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sanity-check imports**

Run: `python -c "import app.main"`
Expected: no import errors (this does not start the bot, just verifies wiring compiles).

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add entrypoint wiring bot handlers, state and confirmation bridge"
```

---

## Task 9: Deployment (systemd) + manual smoke test

**Files:**
- Create: `deploy/aleks-agent.service`

- [ ] **Step 1: Write the systemd unit**

```ini
# deploy/aleks-agent.service
[Unit]
Description=Aleks personal coding agent (Telegram bot)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/projects/Aleks
EnvironmentFile=/root/projects/Aleks/.env
ExecStart=/root/projects/Aleks/.venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Commit**

```bash
git add deploy/aleks-agent.service
git commit -m "chore: add systemd unit for VPS deployment"
```

- [ ] **Step 3: Deploy to the VPS (manual, not automated by this plan)**

```bash
# on the VPS, as root
git clone <repo> /root/projects/Aleks   # or scp/rsync if not pushed yet
cd /root/projects/Aleks
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # then fill in real TELEGRAM_BOT_TOKEN, ALLOWED_USER_ID, ANTHROPIC_API_KEY, PROJECTS
cp deploy/aleks-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now aleks-agent
journalctl -u aleks-agent -f
```

- [ ] **Step 4: Run the manual smoke-test checklist from the spec**

From the phone's Telegram app, talk to the bot and verify each:
1. `/projects` → lists configured projects.
2. `/project aleks` → "Активный проект: aleks".
3. Send a safe message (e.g. "покажи содержимое README") → agent responds, no confirmation prompt appears.
4. Send a message that makes the agent run a risky command (e.g. "закоммить и запушь изменение") → ✅/❌ buttons appear; tapping ✅ lets it proceed, tapping ❌ makes the agent explain it couldn't push.
5. Trigger a risky action and don't tap anything for the configured timeout → agent reports the action was cancelled by timeout.
6. `systemctl restart aleks-agent` mid-conversation, then send another message in the same project → agent responds with context from before the restart (via `resume`).
7. `/project lead-parser` then send a message → agent operates in `lead-parser`'s directory, `/project aleks` again → still remembers `aleks`'s prior session.

Expected: all 7 checks pass. Any failure should be diagnosed against `journalctl -u aleks-agent` before touching code further.

---

## Self-Review Notes

- **Spec coverage:** architecture (Task 1, 8), risk classification (Task 2), config incl. `PROJECTS`/`ALLOWED_USER_ID`/timeout (Task 3), state/session persistence (Task 4), confirmation bridge + timeout auto-deny (Task 5), Agent SDK wiring + `can_use_tool` (Task 6), `/project`/`/projects`/callback/text handlers + busy-lock + 4096-char splitting (Task 7), systemd deployment + full smoke-test checklist (Task 9) — every spec section maps to a task.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or an exact command.
- **Type consistency checked:** `ConfirmationBridge.request(correlation_id, send_prompt)` signature matches every call site (Task 5, Task 6, Task 7c); `run_turn(...)` keyword arguments match between `agent_runner.py` and `chat.py`; `StateStore` method names (`get_active_project`, `set_active_project`, `get_session_id`, `set_session_id`) match between Task 4 and Tasks 7a/7c.
- **Known research gap flagged inline:** Task 6, Step 6 calls out that the exact `ResultMessage`/`AssistantMessage` constructor fields should be verified against the installed `claude-agent-sdk` version (fields confirmed via the SDK's public GitHub source at implementation time: `subtype`, `duration_ms`, `duration_api_ms`, `is_error`, `num_turns`, `session_id`, plus optional fields) — if a newer SDK release renames or requires additional fields, adjust the fake message construction in the test, not `run_turn`'s reading of `message.session_id`/`TextBlock.text`.
