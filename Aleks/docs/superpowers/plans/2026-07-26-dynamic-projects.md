# Dynamic Project Creation from Telegram Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user create and switch to a new project from a Telegram chat message (fixed trigger phrases), with the folder created and registered by deterministic Python code in the bot process -- never via Claude's own tool-use loop.

**Architecture:** A new `app/new_project.py` module owns trigger-phrase matching, name slugification, and the create-or-switch orchestration (`os.makedirs` + `StateStore` writes). `chat.py` checks the trigger before the existing active-project flow and short-circuits before `run_turn` is ever called. `StateStore` gains a `dynamic_projects` table and `list_all_projects()` merge method; `config.py` gains a `projects_root` setting; `project.py`'s `/projects` and `/project` commands switch from the static-only `settings.projects` dict to the merged list.

**Tech Stack:** Python, `aiosqlite`, `pydantic_settings`, `python-telegram-bot`, `pytest` + `pytest-asyncio`.

---

## Task 1: `projects_root` config setting

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_projects_root_defaults_to_root_user_projects(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    settings = Settings(_env_file=None)

    assert settings.projects_root == "/root/user-projects"


def test_projects_root_overridable_via_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("PROJECTS_ROOT", "/srv/user-projects")
    settings = Settings(_env_file=None)

    assert settings.projects_root == "/srv/user-projects"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -k projects_root -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'projects_root'`

- [ ] **Step 3: Write minimal implementation**

In `app/config.py`, add after the `db_path` field (around line 39):

```python
    projects_root: str = Field(
        default="/root/user-projects",
        description="Filesystem root under which dynamically-created projects "
        "(via the 'новый проект' chat trigger) get their own subfolder.",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -k projects_root -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat(config): add projects_root setting for dynamic projects"
```

---

## Task 2: `StateStore` dynamic projects table + methods

**Files:**
- Modify: `app/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_state.py` (following the existing `tmp_path` + `pytest.mark.asyncio` pattern in that file):

```python
@pytest.mark.asyncio
async def test_add_and_list_dynamic_project(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()

    await store.add_dynamic_project("epoksidka", "/root/user-projects/epoksidka")

    merged = await store.list_all_projects({"aleks": "/root/projects/Aleks"})
    assert merged == {
        "aleks": "/root/projects/Aleks",
        "epoksidka": "/root/user-projects/epoksidka",
    }


@pytest.mark.asyncio
async def test_list_all_projects_static_wins_on_name_collision(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()
    await store.add_dynamic_project("aleks", "/root/user-projects/aleks")

    merged = await store.list_all_projects({"aleks": "/root/projects/Aleks"})

    assert merged["aleks"] == "/root/projects/Aleks"


@pytest.mark.asyncio
async def test_add_dynamic_project_duplicate_name_raises(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()
    await store.add_dynamic_project("epoksidka", "/root/user-projects/epoksidka")

    with pytest.raises(Exception):
        await store.add_dynamic_project("epoksidka", "/root/user-projects/epoksidka-2")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state.py -k dynamic_project -v`
Expected: FAIL with `AttributeError: 'StateStore' object has no attribute 'add_dynamic_project'`

- [ ] **Step 3: Write minimal implementation**

In `app/state.py`, add the table to `init()` (inside the `async with aiosqlite.connect(...)` block, after the existing `CREATE TABLE` calls, before `await db.commit()`):

```python
                await db.execute(
                    "CREATE TABLE IF NOT EXISTS dynamic_projects ("
                    "name TEXT PRIMARY KEY, path TEXT NOT NULL, created_at TEXT NOT NULL)"
                )
```

Add these methods to the `StateStore` class (add `from datetime import datetime, timezone` to the imports at the top of the file):

```python
    async def add_dynamic_project(self, name: str, path: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO dynamic_projects (name, path, created_at) VALUES (?, ?, ?)",
                (name, path, datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()

    async def list_all_projects(self, static_projects: dict[str, str]) -> dict[str, str]:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT name, path FROM dynamic_projects")
            rows = await cursor.fetchall()
        merged = dict(static_projects)
        for name, path in rows:
            merged.setdefault(name, path)
        return merged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: PASS (all tests, including pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add app/state.py tests/test_state.py
git commit -m "feat(state): add dynamic_projects table and list_all_projects merge"
```

---

## Task 3: `slugify()` in `app/new_project.py`

**Files:**
- Create: `app/new_project.py`
- Test: Create `tests/test_new_project.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_new_project.py`:

```python
# tests/test_new_project.py
from app.new_project import slugify


def test_slugify_transliterates_cyrillic() -> None:
    assert slugify("Эпоксидка Лендинг") == "epoksidka-lending"


def test_slugify_collapses_punctuation_and_spaces() -> None:
    assert slugify("  столы, табуретки!!  часы  ") == "stoly-taburetki-chasy"


def test_slugify_empty_input_returns_empty_string() -> None:
    assert slugify("   ") == ""
    assert slugify("!!!") == ""


def test_slugify_truncates_to_max_length() -> None:
    long_name = "а" * 100
    result = slugify(long_name)
    assert len(result) <= 40
    assert not result.endswith("-")


def test_slugify_keeps_latin_and_digits_as_is() -> None:
    assert slugify("Project 2") == "project-2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_new_project.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.new_project'`

- [ ] **Step 3: Write minimal implementation**

Create `app/new_project.py`:

```python
# app/new_project.py
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")

SLUG_MAX_LENGTH = 40


def slugify(text: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    lowered = text.strip().lower()
    transliterated = "".join(_TRANSLIT.get(ch, ch) for ch in lowered)
    slug = _NON_SLUG_CHARS.sub("-", transliterated).strip("-")
    return slug[:max_length].strip("-")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_new_project.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/new_project.py tests/test_new_project.py
git commit -m "feat(new-project): add slugify() for project name normalization"
```

---

## Task 4: Trigger phrase matching

**Files:**
- Modify: `app/new_project.py`
- Test: Modify `tests/test_new_project.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_new_project.py`:

```python
from app.new_project import parse_new_project_trigger


def test_trigger_bare_phrase() -> None:
    assert parse_new_project_trigger("новый проект эпоксидка") == "эпоксидка"


def test_trigger_delaem_variant() -> None:
    assert parse_new_project_trigger("Делаем новый проект: столы из смолы") == "столы из смолы"


def test_trigger_sozdat_variant() -> None:
    assert parse_new_project_trigger("создать новый проект лендинг") == "лендинг"


def test_trigger_sozday_variant() -> None:
    assert parse_new_project_trigger("создай новый проект лендинг") == "лендинг"


def test_trigger_nachnem_variants() -> None:
    assert parse_new_project_trigger("начнём новый проект часы") == "часы"
    assert parse_new_project_trigger("начнем новый проект часы") == "часы"


def test_trigger_case_insensitive() -> None:
    assert parse_new_project_trigger("НОВЫЙ ПРОЕКТ Часы") == "Часы"


def test_trigger_no_match_returns_none() -> None:
    assert parse_new_project_trigger("почини баг в проекте") is None
    assert parse_new_project_trigger("хочу обсудить новый проект") is None
    assert parse_new_project_trigger("у меня новый проект уже есть") is None


def test_trigger_phrase_without_name_returns_empty_string() -> None:
    assert parse_new_project_trigger("новый проект") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_new_project.py -k trigger -v`
Expected: FAIL with `ImportError: cannot import name 'parse_new_project_trigger'`

- [ ] **Step 3: Write minimal implementation**

Add to `app/new_project.py`:

```python
_TRIGGER_RE = re.compile(
    r"^(?:делаем|создай|создать|начн[её]м)?\s*новый проект[:\s]*(.*)$",
    re.IGNORECASE | re.DOTALL,
)


def parse_new_project_trigger(text: str) -> str | None:
    match = _TRIGGER_RE.match(text.strip())
    if match is None:
        return None
    return match.group(1).strip()
```

Note: `test_trigger_no_match_returns_none` requires the `^` anchor -- "хочу обсудить новый проект" and "у меня новый проект уже есть" don't start with the trigger phrase (optionally prefixed only by one of the four verbs), so `re.match` correctly rejects them.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_new_project.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add app/new_project.py tests/test_new_project.py
git commit -m "feat(new-project): add fixed-phrase trigger detection"
```

---

## Task 5: `handle_new_project()` orchestration

**Files:**
- Modify: `app/new_project.py`
- Test: Modify `tests/test_new_project.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_new_project.py`:

```python
import os
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.new_project import handle_new_project


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="k",
        projects={"aleks": "/root/projects/Aleks"},
        projects_root=str(tmp_path / "user-projects"),
        _env_file=None,
        **overrides,
    )


def _state(existing: dict[str, str] | None = None) -> AsyncMock:
    state = AsyncMock()
    state.list_all_projects.return_value = dict(existing or {})
    return state


@pytest.mark.asyncio
async def test_handle_new_project_creates_folder_and_activates(tmp_path) -> None:
    settings = _settings(tmp_path)
    state = _state()

    reply = await handle_new_project("Эпоксидка Лендинг", user_id=42, settings=settings, state=state)

    expected_path = os.path.join(settings.projects_root, "epoksidka-lending")
    assert os.path.isdir(expected_path)
    state.add_dynamic_project.assert_awaited_once_with("epoksidka-lending", expected_path)
    state.set_active_project.assert_awaited_once_with(42, "epoksidka-lending")
    assert "epoksidka-lending" in reply
    assert expected_path in reply


@pytest.mark.asyncio
async def test_handle_new_project_empty_name_asks_for_name() -> None:
    settings = _settings.__wrapped__ if False else None  # placeholder removed below


@pytest.mark.asyncio
async def test_handle_new_project_empty_name_replies_with_prompt(tmp_path) -> None:
    settings = _settings(tmp_path)
    state = _state()

    reply = await handle_new_project("   ", user_id=42, settings=settings, state=state)

    assert "название" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_new_project_static_name_collision_rejected(tmp_path) -> None:
    settings = _settings(tmp_path)
    state = _state()

    reply = await handle_new_project("aleks", user_id=42, settings=settings, state=state)

    assert "занято" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_new_project_existing_dynamic_switches_without_recreating(tmp_path) -> None:
    settings = _settings(tmp_path)
    existing_path = str(tmp_path / "user-projects" / "epoksidka")
    state = _state(existing={"epoksidka": existing_path})

    reply = await handle_new_project("эпоксидка", user_id=42, settings=settings, state=state)

    assert "уже существует" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_awaited_once_with(42, "epoksidka")


@pytest.mark.asyncio
async def test_handle_new_project_makedirs_failure_reports_error_and_registers_nothing(
    tmp_path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    state = _state()

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("app.new_project.os.makedirs", boom)

    reply = await handle_new_project("часы", user_id=42, settings=settings, state=state)

    assert "не получилось" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_not_awaited()
```

Remove the stray placeholder test (`test_handle_new_project_empty_name_asks_for_name`) -- it was written and replaced by the real one in the same step; do not leave both in the file. Only `test_handle_new_project_empty_name_replies_with_prompt` should remain.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_new_project.py -k handle_new_project -v`
Expected: FAIL with `ImportError: cannot import name 'handle_new_project'`

- [ ] **Step 3: Write minimal implementation**

Add to `app/new_project.py` (add `import os` at the top, plus `TYPE_CHECKING` imports for type hints):

```python
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import StateStore


async def handle_new_project(
    raw_name: str, user_id: int, settings: "Settings", state: "StateStore"
) -> str:
    slug = slugify(raw_name)
    if not slug:
        return "Укажи название проекта в этом же сообщении: «новый проект <название>»"

    if slug in settings.projects:
        return f"Имя «{slug}» занято системным проектом, выбери другое"

    existing = await state.list_all_projects(settings.projects)
    if slug in existing:
        await state.set_active_project(user_id, slug)
        return f"Проект «{slug}» уже существует, переключился на него"

    project_path = os.path.join(settings.projects_root, slug)
    try:
        os.makedirs(settings.projects_root, exist_ok=True)
        os.makedirs(project_path, exist_ok=False)
    except OSError as exc:
        return f"Не получилось создать проект: {exc}"

    await state.add_dynamic_project(slug, project_path)
    await state.set_active_project(user_id, slug)
    return f"Новый проект «{slug}» создан: {project_path}\nАктивный проект переключён на него."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_new_project.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add app/new_project.py tests/test_new_project.py
git commit -m "feat(new-project): add handle_new_project orchestration"
```

---

## Task 6: Wire trigger into `chat.py`

**Files:**
- Modify: `app/bot/handlers/chat.py`
- Modify: `tests/test_bot_chat_handler.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_bot_chat_handler.py`:

```python
@pytest.mark.asyncio
async def test_new_project_trigger_short_circuits_before_run_turn(monkeypatch) -> None:
    update, context, state = _update_and_context(text="новый проект эпоксидка")
    state.list_all_projects.return_value = {}

    called = False

    async def fake_run_turn(**kwargs):
        nonlocal called
        called = True
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    assert called is False
    state.add_dynamic_project.assert_awaited_once()
    state.set_active_project.assert_awaited_once_with(42, "epoksidka")
    update.message.reply_text.assert_awaited_once()
    assert "epoksidka" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_new_project_trigger_works_even_with_no_active_project(monkeypatch) -> None:
    update, context, state = _update_and_context(text="создай новый проект часы")
    state.get_active_project.return_value = None
    state.list_all_projects.return_value = {}

    await chat_module.on_text_message(update, context)

    state.set_active_project.assert_awaited_once_with(42, "chasy")


@pytest.mark.asyncio
async def test_non_trigger_message_uses_merged_project_path(monkeypatch) -> None:
    update, context, state = _update_and_context()
    state.list_all_projects.return_value = {"aleks": "/root/projects/Aleks"}

    async def fake_run_turn(**kwargs):
        assert kwargs["project_path"] == "/root/projects/Aleks"
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    state.list_all_projects.assert_awaited_once_with({"aleks": "/root/projects/Aleks"})
```

The `_settings()`/`_update_and_context()` helpers in this file already build `state` as `AsyncMock()`, so `state.list_all_projects` and `state.add_dynamic_project` are auto-mocked -- no helper changes needed. `_update_and_context()`'s `settings` uses `projects={"aleks": "/root/projects/Aleks"}` with the default `projects_root`; since these tests use `tmp_path`-free dirs, add a `monkeypatch` to point `projects_root` somewhere writable for the first two tests:

Replace the two new trigger tests' first lines to also patch a real temp root, since `handle_new_project` calls real `os.makedirs`:

```python
@pytest.mark.asyncio
async def test_new_project_trigger_short_circuits_before_run_turn(monkeypatch, tmp_path) -> None:
    update, context, state = _update_and_context(text="новый проект эпоксидка")
    context.bot_data["settings"].projects_root = str(tmp_path)
    state.list_all_projects.return_value = {}
    ...
```

(Apply the same `context.bot_data["settings"].projects_root = str(tmp_path)` line, with `tmp_path` added as a fixture parameter, to `test_new_project_trigger_works_even_with_no_active_project` as well.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bot_chat_handler.py -k "new_project or merged" -v`
Expected: FAIL -- trigger test fails because `run_turn` still gets called (no short-circuit yet); `merged_project_path` test fails because `chat.py` still reads `settings.projects.get(project)` directly, so `state.list_all_projects` is never awaited.

- [ ] **Step 3: Write minimal implementation**

In `app/bot/handlers/chat.py`, add the import (near the other `app.*` imports):

```python
from app.new_project import handle_new_project, parse_new_project_trigger
```

Replace the start of `on_text_message` (lines 63-73) with:

```python
async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if update.message is None or not is_authorized(update, settings.allowed_user_id):
        return
    user = update.effective_user

    state: StateStore = context.bot_data["state"]

    new_project_name = parse_new_project_trigger(update.message.text)
    if new_project_name is not None:
        reply = await handle_new_project(new_project_name, user.id, settings, state)
        await update.message.reply_text(reply)
        return

    project = await state.get_active_project(user.id)
    if project is None:
        await update.message.reply_text("Сначала выбери проект: /projects")
        return
```

Replace line 120 (`project_path = settings.projects.get(project)`) with:

```python
        merged_projects = await state.list_all_projects(settings.projects)
        project_path = merged_projects.get(project)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bot_chat_handler.py -v`
Expected: PASS (all tests in the file, including pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add app/bot/handlers/chat.py tests/test_bot_chat_handler.py
git commit -m "feat(chat): wire new-project trigger ahead of the existing turn flow"
```

---

## Task 7: `/projects` and `/project` use the merged list

**Files:**
- Modify: `app/bot/handlers/project.py`
- Test: `tests/test_bot_project_handler.py`

- [ ] **Step 1: Read current handler to confirm exact signatures**

Read `app/bot/handlers/project.py` in full before editing -- it was read earlier in this session but re-check `_project_list_text`, `cmd_projects`, and `cmd_project`'s exact bodies since this task depends on their current signatures matching what's below. If the actual code differs from the snippets in Step 3, adapt Step 3 to match the real structure (same behavior: replace every direct use of `settings.projects` with the awaited merged dict).

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_bot_project_handler.py` (following that file's existing `_settings()`/`_update()` helper pattern):

```python
@pytest.mark.asyncio
async def test_cmd_projects_lists_dynamic_projects_too() -> None:
    settings = _settings()
    update = _update()
    context = MagicMock()
    state = AsyncMock()
    state.list_all_projects.return_value = {
        "aleks": "/root/projects/Aleks",
        "epoksidka": "/root/user-projects/epoksidka",
    }
    context.bot_data = {"settings": settings, "state": state}

    await project_module.cmd_projects(update, context)

    text = update.message.reply_text.call_args.args[0]
    assert "aleks" in text
    assert "epoksidka" in text


@pytest.mark.asyncio
async def test_cmd_project_switches_to_dynamic_project() -> None:
    settings = _settings()
    update = _update(args=["epoksidka"])
    context = MagicMock()
    context.args = ["epoksidka"]
    state = AsyncMock()
    state.list_all_projects.return_value = {
        "aleks": "/root/projects/Aleks",
        "epoksidka": "/root/user-projects/epoksidka",
    }
    context.bot_data = {"settings": settings, "state": state}

    await project_module.cmd_project(update, context)

    state.set_active_project.assert_awaited_once()
```

Adjust these two tests' argument-passing (`context.args`, `update` construction) to match whatever `_update()`/existing tests in `tests/test_bot_project_handler.py` actually use -- copy the pattern from the existing `test_cmd_projects_*` / `test_cmd_project_*` tests in that file rather than guessing field names.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_bot_project_handler.py -k dynamic -v`
Expected: FAIL -- `state.list_all_projects` never awaited because the handler still reads `settings.projects` directly, so listed/switched projects don't include `epoksidka`.

- [ ] **Step 4: Write minimal implementation**

In `app/bot/handlers/project.py`, change `_project_list_text` to accept a plain `dict[str, str]` of names instead of `Settings`, and update both `cmd_projects` and `cmd_project` to build that dict via `await state.list_all_projects(settings.projects)` before calling it or looking up a name. Every place the handler currently does `settings.projects` (membership check, iteration, `.get(name)`) must instead use this merged dict. Keep `state: StateStore = context.bot_data["state"]` consistent with how `chat.py` already reads it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_bot_project_handler.py -v`
Expected: PASS (all tests in the file, including pre-existing ones)

- [ ] **Step 6: Commit**

```bash
git add app/bot/handlers/project.py tests/test_bot_project_handler.py
git commit -m "feat(project): list and switch to dynamically-created projects"
```

---

## Task 8: Document `PROJECTS_ROOT` in `.env.example`

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add the new variable**

In `.env.example`, after the `PROJECTS=...` line (line 8), add:

```
# Root folder for projects created from Telegram via the "новый проект <name>"
# trigger phrase (see docs/superpowers/specs/2026-07-26-dynamic-projects-design.md).
# Defaults to /root/user-projects if unset.
PROJECTS_ROOT=/root/user-projects
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: document PROJECTS_ROOT env var"
```

---

## Task 9: Full test suite + deploy note

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: PASS, all tests (pre-existing + all added in Tasks 1-7)

- [ ] **Step 2: Remind the user about the production `.env`**

The deployed bot's `.env` on the VPS (`aleks-agent`) does not yet have `PROJECTS_ROOT` set. Since Task 1 gives it a default (`/root/user-projects`), the bot will work without any server change, but flag to the user that they may want to set `PROJECTS_ROOT` explicitly in the server's `.env` if they'd prefer a different location before this is deployed there. This step is a reminder for the human, not an automated action -- do not edit the production `.env` or restart the service as part of this plan.

---

## Self-Review

**Spec coverage:**
- Trigger phrases (5 variants) + negative-match guard → Task 4 ✅
- `slugify()` (translit, punctuation, empty input, 40-char truncation) → Task 3 ✅
- Handler bypasses Claude entirely on trigger match → Task 6 (`assert called is False` in `test_new_project_trigger_short_circuits_before_run_turn`) ✅
- `dynamic_projects` table + `add_dynamic_project`/`list_all_projects` with static-wins merge → Task 2 ✅
- Static-name collision rejected → Task 5 ✅
- Existing-dynamic-project switches without recreating → Task 5 ✅
- `PROJECTS_ROOT` config + `os.makedirs` with `exist_ok=True` for the root, `exist_ok=False` for the project dir → Task 1, Task 5 ✅
- `os.makedirs` failure → chat error, nothing registered → Task 5 (`test_handle_new_project_makedirs_failure_reports_error_and_registers_nothing`) ✅
- Empty/missing name after trigger → prompt to supply one → Task 5 (`test_handle_new_project_empty_name_replies_with_prompt`) ✅
- `/projects` and `/project <name>` use merged list → Task 7 ✅
- No path traversal by construction (whitelist-only slug chars) → guaranteed structurally by `slugify()`'s `_NON_SLUG_CHARS` regex in Task 3; no separate test needed since it's a property of the character whitelist, not a runtime branch.

**Placeholder scan:** No TBD/TODO markers. Task 7 Step 1 asks the implementer to re-read the actual current file before editing (since this plan's author read it in a prior session and the exact line numbers/snippet may have drifted) rather than blindly pasting unverified code -- this is a verification step, not a placeholder; the required behavior change is stated concretely ("every place ... must instead use this merged dict").

**Type consistency:** `handle_new_project(raw_name: str, user_id: int, settings: Settings, state: StateStore) -> str` used identically in Task 5 (definition) and Task 6 (call site in `chat.py`). `parse_new_project_trigger(text: str) -> str | None` used identically in Task 4 (definition) and Task 6 (call site). `StateStore.list_all_projects(static_projects: dict[str, str]) -> dict[str, str]` used identically in Task 2 (definition), Task 6 (`chat.py`), and Task 7 (`project.py`). `StateStore.add_dynamic_project(name: str, path: str) -> None` used identically in Task 2 and Task 5.
