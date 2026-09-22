# Skill Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone, scheduled "skill hunter" process to the Aleks project that searches fixed niches for new Claude skills, deduplicates against history, and sends a Telegram digest for manual approval -- with no auto-install and no coupling to `agent_runner.py`'s restricted confirmation-gated configuration.

**Architecture:** New `app/skill_hunter/` package: `models.py` (shared `SkillCandidate`), `history.py` (sync JSON history read/dedup/atomic write with a file lock), `search.py` (async `find_candidates(niche)` via its own `claude_agent_sdk.query()` call with `WebSearch` allowed), `hunter.py` (async orchestrator: per niche, search -> filter -> send -> record, isolating failures per niche), `__main__.py` (systemd-timer entry point that builds its own `telegram.Bot`). A new `/find_skills` command handler reuses `hunter.run()` inside the running bot process via the existing `context.bot`. `app/config.py` gains three new `Settings` fields. Two new systemd units (`skill-hunter.service` oneshot + `skill-hunter.timer`) trigger it weekly.

**Tech Stack:** Python >= 3.11, `claude_agent_sdk`, `python-telegram-bot`, `pydantic`/`pydantic-settings`, `filelock` (new dependency), `pytest`/`pytest-asyncio`/`pytest-mock`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-22-skill-hunter-design.md`

## Global Constraints

- Do not modify or loosen `app/agent_runner.py` (its `setting_sources=[]` and trimmed `system_prompt`) -- per `AGENTS.md`. Skill Hunter's own `search.py` makes its own, separate `claude_agent_sdk.query()` call and never imports from `agent_runner.py`.
- Never feed the aibasis.ru-generated prompt to an agent as instructions -- `search.py`'s system prompt is authored here, from scratch.
- No auto-install of found skills -- `hunter.py` only sends a Telegram message; there is no code path that writes a found skill into any project.
- Python >= 3.11, typed code (pydantic), no blocking calls inside async Telegram handlers -- `history.py`'s synchronous file I/O is always invoked through `asyncio.to_thread()` from async call sites (`hunter.py`).
- Never commit `.env` or `skill_hunter_history.json` (runtime state, not source) -- add to `.gitignore`.

## Review Focus

- **Empty/unavailable WebSearch (network down, rate-limited):** `search.find_candidates()` must catch any exception from `query()` or JSON parsing, log it, and return `[]` rather than raising -- covered by Task 3's failure tests and Task 4's per-niche isolation test.
- **Duplicate candidates across different niches:** the same skill URL surfacing under two niches must be deduplicated by a single global key, not per-(niche, skill) -- covered by Task 2's cross-niche dedup test.
- **Empty result for a niche after filtering:** no Telegram message is sent for a niche with zero fresh candidates (not even an empty digest) -- covered by Task 4's "nothing new" test.
- **Corrupted or missing history file:** first run (no file) or a hand-edited/corrupted `skill_hunter_history.json` must not crash the process -- treated as an empty history -- covered by Task 2's missing/corrupted-file tests.
- **Concurrent runs (weekly timer firing while `/find_skills` is run manually):** two processes writing to the same history file at once must not lose either write -- covered by Task 2's concurrent-write test using a real file lock.

---

### Task 1: Settings for skill hunter (niches, chat id, history path)

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings.skill_hunter_niches: list[str]` (default `[]`), `Settings.skill_hunter_chat_id: int` (defaults to `allowed_user_id` when unset), `Settings.skill_hunter_history_path: str` (default `"skill_hunter_history.json"`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config.py`:

```python
def test_skill_hunter_settings_default_to_empty_niches_and_owner_chat(monkeypatch) -> None:
    monkeypatch.delenv("SKILL_HUNTER_NICHES", raising=False)
    monkeypatch.delenv("SKILL_HUNTER_CHAT_ID", raising=False)
    monkeypatch.delenv("SKILL_HUNTER_HISTORY_PATH", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    settings = Settings(_env_file=None)

    assert settings.skill_hunter_niches == []
    assert settings.skill_hunter_chat_id == 42
    assert settings.skill_hunter_history_path == "skill_hunter_history.json"


def test_skill_hunter_niches_parsed_from_json_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SKILL_HUNTER_NICHES", '["Python/FastAPI", "Telegram-боты"]')

    settings = Settings(_env_file=None)

    assert settings.skill_hunter_niches == ["Python/FastAPI", "Telegram-боты"]


def test_skill_hunter_chat_id_overridable_independent_of_allowed_user(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SKILL_HUNTER_CHAT_ID", "999")

    settings = Settings(_env_file=None)

    assert settings.skill_hunter_chat_id == 999
    assert settings.allowed_user_id == 42
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 new FAIL with `AttributeError: 'Settings' object has no attribute 'skill_hunter_niches'` (or equivalent for the other two fields).

- [ ] **Step 3: Implement the settings fields**

In `app/config.py`, add imports and fields, then a model validator. Full updated file:

```python
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., description="Token from @BotFather")
    allowed_user_id: int = Field(..., ge=1, description="Telegram user id of the owner")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude Agent SDK (direct billing)")
    anthropic_base_url: str = Field(default="", description="Override base URL, e.g. Polza.ai proxy")
    anthropic_auth_token: str = Field(default="", description="Bearer token for anthropic_base_url proxy")
    model: str = Field(
        default="sonnet",
        description="Claude model alias for the Agent SDK (sonnet/opus/haiku). "
        "Left unset the CLI defaults to Opus, which is far more expensive per token.",
    )
    projects: dict[str, str] = Field(
        default_factory=dict,
        description="Project name -> absolute path on the VPS",
    )
    confirmation_timeout_seconds: float = Field(default=600.0, ge=1)
    run_turn_timeout_seconds: float = Field(
        default=1200.0,
        ge=1,
        description="Hard ceiling on a single run_turn() call, so a hung Agent "
        "SDK/subprocess call (e.g. the CLI never starting) can't block a turn "
        "forever with no user-visible feedback. Must stay well above "
        "confirmation_timeout_seconds since confirmation waits happen inside "
        "the same call.",
    )
    db_path: str = Field(default="state.db")
    projects_root: str = Field(
        default="/root/user-projects",
        description="Filesystem root under which dynamically-created projects "
        "(via the 'новый проект' chat trigger) get their own subfolder.",
    )
    log_level: str = Field(default="INFO")
    agent_effort: str | None = Field(
        default=None,
        description="Claude Agent SDK 'effort' level (low/medium/high/xhigh/max). "
        "Left unset the SDK/CLI default applies. Lowering it trims reasoning "
        "tokens on the quick one-shot edits typical of Telegram/phone usage.",
    )
    max_turn_budget_usd: float | None = Field(
        default=None,
        description="Hard USD ceiling per run_turn() call (SDK's max_budget_usd). "
        "Left unset there is no cap, so a runaway turn (e.g. the agent looping "
        "on tool calls) can run up an unbounded bill.",
    )
    skill_hunter_niches: list[str] = Field(
        default_factory=list,
        description="Fixed list of niches/topics Skill Hunter searches for new "
        "Claude skills, e.g. [\"Python/FastAPI\", \"Telegram-боты\"].",
    )
    skill_hunter_chat_id: int | None = Field(
        default=None,
        description="Telegram chat id Skill Hunter sends digests to. Defaults "
        "to allowed_user_id when unset.",
    )
    skill_hunter_history_path: str = Field(default="skill_hunter_history.json")

    @model_validator(mode="after")
    def _default_skill_hunter_chat_id(self) -> "Settings":
        if self.skill_hunter_chat_id is None:
            self.skill_hunter_chat_id = self.allowed_user_id
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: all tests in the file PASS (existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat(skill-hunter): add niches/chat-id/history-path settings"
```

---

### Task 2: History store (models, dedup, atomic write, file lock)

**Files:**
- Create: `app/skill_hunter/__init__.py`
- Create: `app/skill_hunter/models.py`
- Create: `app/skill_hunter/history.py`
- Test: `tests/test_skill_hunter_history.py`
- Modify: `pyproject.toml` (add `filelock` dependency)
- Modify: `.gitignore` (add `skill_hunter_history.json*`)

**Interfaces:**
- Produces:
  - `class SkillCandidate(BaseModel)` with fields `title: str`, `url: str`, `description: str` (`app/skill_hunter/models.py`).
  - `normalize_skill_url(url: str) -> str` (`app/skill_hunter/history.py`).
  - `load_history(path: str) -> dict` -- always returns `{"skills": {...}}`, never raises.
  - `filter_new(history: dict, candidates: list[SkillCandidate]) -> list[SkillCandidate]`.
  - `record(path: str, niche: str, candidates: list[SkillCandidate], now_iso: str) -> None` -- atomic write, file-locked, no-op if `candidates` is empty.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_hunter_history.py`:

```python
import json
import threading

from app.skill_hunter.history import filter_new, load_history, normalize_skill_url, record
from app.skill_hunter.models import SkillCandidate


def _candidate(url: str, title: str = "Some Skill") -> SkillCandidate:
    return SkillCandidate(title=title, url=url, description="desc")


def test_normalize_skill_url_strips_trailing_slash_query_and_case() -> None:
    assert normalize_skill_url("https://GitHub.com/foo/Bar/") == normalize_skill_url(
        "https://github.com/foo/bar"
    )


def test_load_history_missing_file_returns_empty(tmp_path) -> None:
    path = str(tmp_path / "history.json")

    history = load_history(path)

    assert history == {"skills": {}}


def test_load_history_corrupted_file_returns_empty(tmp_path) -> None:
    path = tmp_path / "history.json"
    path.write_text("{not valid json", encoding="utf-8")

    history = load_history(str(path))

    assert history == {"skills": {}}


def test_filter_new_excludes_known_and_within_batch_duplicates() -> None:
    known_url = "https://github.com/foo/known"
    history = {"skills": {normalize_skill_url(known_url): {"first_seen": "x", "niches": ["a"]}}}
    candidates = [
        _candidate(known_url),
        _candidate("https://github.com/foo/new"),
        _candidate("https://github.com/foo/new"),  # duplicate within this batch
    ]

    fresh = filter_new(history, candidates)

    assert [c.url for c in fresh] == ["https://github.com/foo/new"]


def test_record_is_noop_for_empty_candidates(tmp_path) -> None:
    path = str(tmp_path / "history.json")

    record(path, "niche-a", [], now_iso="2026-09-22T00:00:00+00:00")

    assert load_history(path) == {"skills": {}}


def test_record_merges_niches_for_same_skill_across_calls(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    url = "https://github.com/foo/bar"

    record(path, "niche-a", [_candidate(url)], now_iso="2026-09-22T00:00:00+00:00")
    record(path, "niche-b", [_candidate(url)], now_iso="2026-09-23T00:00:00+00:00")

    history = load_history(path)
    entry = history["skills"][normalize_skill_url(url)]
    assert entry["niches"] == ["niche-a", "niche-b"]
    assert entry["first_seen"] == "2026-09-22T00:00:00+00:00"  # unchanged on second call


def test_record_is_dedup_source_for_next_filter_new(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    url = "https://github.com/foo/bar"
    record(path, "niche-a", [_candidate(url)], now_iso="2026-09-22T00:00:00+00:00")

    history = load_history(path)
    fresh = filter_new(history, [_candidate(url)])

    assert fresh == []


def test_record_survives_concurrent_writes_from_two_threads(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    barrier = threading.Barrier(2)

    def write(niche: str, url: str) -> None:
        barrier.wait()
        record(path, niche, [_candidate(url)], now_iso="2026-09-22T00:00:00+00:00")

    t1 = threading.Thread(target=write, args=("niche-a", "https://github.com/foo/one"))
    t2 = threading.Thread(target=write, args=("niche-b", "https://github.com/foo/two"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    history = load_history(path)
    assert len(history["skills"]) == 2  # neither write clobbered the other
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_hunter_history.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.skill_hunter'`.

- [ ] **Step 3: Add the `filelock` dependency**

In `pyproject.toml`, add to `dependencies`:

```toml
    "filelock>=3.13",
```

Run: `uv sync`
Expected: `filelock` installed into the project's venv.

- [ ] **Step 4: Write minimal implementation**

Create `app/skill_hunter/__init__.py` (empty file).

Create `app/skill_hunter/models.py`:

```python
from pydantic import BaseModel


class SkillCandidate(BaseModel):
    title: str
    url: str
    description: str
```

Create `app/skill_hunter/history.py`:

```python
import json
import os
from urllib.parse import urlsplit, urlunsplit

from filelock import FileLock

from app.skill_hunter.models import SkillCandidate


def normalize_skill_url(url: str) -> str:
    parts = urlsplit(url.strip().lower())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def load_history(path: str) -> dict:
    if not os.path.exists(path):
        return {"skills": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"skills": {}}
    if not isinstance(data, dict) or not isinstance(data.get("skills"), dict):
        return {"skills": {}}
    return data


def filter_new(history: dict, candidates: list[SkillCandidate]) -> list[SkillCandidate]:
    known = history.get("skills", {})
    seen_in_batch: set[str] = set()
    fresh: list[SkillCandidate] = []
    for candidate in candidates:
        key = normalize_skill_url(candidate.url)
        if key in known or key in seen_in_batch:
            continue
        seen_in_batch.add(key)
        fresh.append(candidate)
    return fresh


def record(path: str, niche: str, candidates: list[SkillCandidate], now_iso: str) -> None:
    if not candidates:
        return
    lock = FileLock(f"{path}.lock")
    with lock:
        history = load_history(path)
        for candidate in candidates:
            key = normalize_skill_url(candidate.url)
            entry = history["skills"].setdefault(key, {"first_seen": now_iso, "niches": []})
            if niche not in entry["niches"]:
                entry["niches"].append(niche)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
```

Add to `.gitignore`:

```
skill_hunter_history.json*
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_hunter_history.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/skill_hunter/__init__.py app/skill_hunter/models.py app/skill_hunter/history.py \
    tests/test_skill_hunter_history.py pyproject.toml .gitignore
git commit -m "feat(skill-hunter): add history store with cross-niche dedup and file locking"
```

---

### Task 3: Search — find_candidates() via a dedicated claude_agent_sdk call

**Files:**
- Create: `app/skill_hunter/search.py`
- Test: `tests/test_skill_hunter_search.py`

**Interfaces:**
- Consumes: `SkillCandidate` from `app.skill_hunter.models`.
- Produces: `async def find_candidates(niche: str, *, model: str = "sonnet") -> list[SkillCandidate]` -- never raises; returns `[]` on any search or parse failure.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_hunter_search.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_hunter_search.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.skill_hunter.search'`.

- [ ] **Step 3: Write minimal implementation**

Create `app/skill_hunter/search.py`:

```python
import json
import logging

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from app.skill_hunter.models import SkillCandidate

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a research assistant hunting for Claude Code skills (SKILL.md-based "
    "extensions) relevant to a specific niche. Use WebSearch to find real, "
    "existing skills on GitHub or skills.sh/skillsmp.com published in the last "
    "year. Return ONLY a JSON array (no prose, no markdown fences) of up to 5 "
    "objects with keys \"title\", \"url\", \"description\" (one sentence each, "
    "in Russian). If you find nothing relevant, return an empty array []."
)


async def find_candidates(niche: str, *, model: str = "sonnet") -> list[SkillCandidate]:
    options = ClaudeAgentOptions(
        system_prompt=_SYSTEM_PROMPT,
        model=model,
        allowed_tools=["WebSearch"],
        setting_sources=[],
    )

    text_parts: list[str] = []
    try:
        async for message in query(prompt=niche, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_hunter_search.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/skill_hunter/search.py tests/test_skill_hunter_search.py
git commit -m "feat(skill-hunter): search niches via isolated claude_agent_sdk call"
```

---

### Task 4: Orchestrator — hunter.run() (per-niche isolation, digest formatting, recording)

**Files:**
- Create: `app/skill_hunter/hunter.py`
- Test: `tests/test_skill_hunter_hunter.py`

**Interfaces:**
- Consumes: `history.load_history`, `history.filter_new`, `history.record` (`app/skill_hunter/history.py`); `SkillCandidate` (`app/skill_hunter/models.py`); `search.find_candidates` (`app/skill_hunter/search.py`) as the default `find_candidates_fn`.
- Produces: `async def run(niches: list[str], history_path: str, send_message: Callable[[str], Awaitable[None]], *, find_candidates_fn=find_candidates) -> None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_hunter_hunter.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_hunter_hunter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.skill_hunter.hunter'`.

- [ ] **Step 3: Write minimal implementation**

Create `app/skill_hunter/hunter.py`:

```python
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

        await send_message(_format_message(niche, fresh))
        await asyncio.to_thread(history.record, history_path, niche, fresh, now_iso)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_hunter_hunter.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/skill_hunter/hunter.py tests/test_skill_hunter_hunter.py
git commit -m "feat(skill-hunter): orchestrate per-niche search, digest, and recording"
```

---

### Task 5: Telegram `/find_skills` command + standalone timer entry point

**Files:**
- Create: `app/bot/handlers/skill_hunter.py`
- Create: `app/skill_hunter/__main__.py`
- Modify: `app/main.py` (register the new handler)
- Test: `tests/test_bot_skill_hunter_handler.py`

**Interfaces:**
- Consumes: `hunter.run` (`app/skill_hunter/hunter.py`), `Settings` (`app/config.py`), `is_authorized` (`app/bot/auth.py`).
- Produces: `cmd_find_skills(update, context)`, `register(app)` in `app/bot/handlers/skill_hunter.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bot_skill_hunter_handler.py`:

```python
from unittest.mock import AsyncMock

import pytest

from app.bot.handlers.skill_hunter import cmd_find_skills
from app.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="sk-ant-test",
        skill_hunter_niches=["Python/FastAPI"],
        skill_hunter_chat_id=42,
        skill_hunter_history_path="skill_hunter_history.json",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


def _update_and_context(user_id: int):
    update = AsyncMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    context = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot_data = {"settings": _settings()}
    return update, context


@pytest.mark.asyncio
async def test_find_skills_rejects_unauthorized_user(monkeypatch) -> None:
    update, context = _update_and_context(user_id=999)
    called = False

    async def fake_run(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("app.bot.handlers.skill_hunter.run_skill_hunter", fake_run)

    await cmd_find_skills(update, context)

    assert called is False
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_find_skills_rejects_empty_niches_list(monkeypatch) -> None:
    update, context = _update_and_context(user_id=42)
    context.bot_data["settings"] = _settings(skill_hunter_niches=[])
    called = False

    async def fake_run(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("app.bot.handlers.skill_hunter.run_skill_hunter", fake_run)

    await cmd_find_skills(update, context)

    assert called is False
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_find_skills_invokes_hunter_run_for_authorized_user(monkeypatch) -> None:
    update, context = _update_and_context(user_id=42)
    captured = {}

    async def fake_run(niches, history_path, send_message, **kwargs):
        captured["niches"] = niches
        captured["history_path"] = history_path
        await send_message("digest text")

    monkeypatch.setattr("app.bot.handlers.skill_hunter.run_skill_hunter", fake_run)

    await cmd_find_skills(update, context)

    assert captured["niches"] == ["Python/FastAPI"]
    assert captured["history_path"] == "skill_hunter_history.json"
    context.bot.send_message.assert_called_once_with(chat_id=42, text="digest text")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bot_skill_hunter_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.bot.handlers.skill_hunter'`.

- [ ] **Step 3: Write minimal implementation**

Create `app/bot/handlers/skill_hunter.py`:

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.bot.auth import is_authorized
from app.config import Settings
from app.skill_hunter.hunter import run as run_skill_hunter


async def cmd_find_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return

    if not settings.skill_hunter_niches:
        await update.message.reply_text(
            "Список ниш пуст -- задайте SKILL_HUNTER_NICHES в .env"
        )
        return

    await update.message.reply_text("Ищу новые скиллы, это займёт немного времени...")

    async def send_message(text: str) -> None:
        await context.bot.send_message(chat_id=settings.skill_hunter_chat_id, text=text)

    await run_skill_hunter(
        settings.skill_hunter_niches, settings.skill_hunter_history_path, send_message
    )


def register(app: Application) -> None:
    app.add_handler(CommandHandler("find_skills", cmd_find_skills))
```

Create `app/skill_hunter/__main__.py`:

```python
import asyncio

from telegram import Bot

from app.config import get_settings
from app.skill_hunter.hunter import run


async def _main() -> None:
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)

    async def send_message(text: str) -> None:
        await bot.send_message(chat_id=settings.skill_hunter_chat_id, text=text)

    await run(settings.skill_hunter_niches, settings.skill_hunter_history_path, send_message)


if __name__ == "__main__":
    asyncio.run(_main())
```

Modify `app/main.py`: add the import next to the other handler imports and register it. Change:

```python
from app.bot.handlers import chat as chat_handler
from app.bot.handlers import confirm as confirm_handler
from app.bot.handlers import project as project_handler
```

to:

```python
from app.bot.handlers import chat as chat_handler
from app.bot.handlers import confirm as confirm_handler
from app.bot.handlers import project as project_handler
from app.bot.handlers import skill_hunter as skill_hunter_handler
```

and change:

```python
    project_handler.register(app)
    confirm_handler.register(app)
    chat_handler.register(app)
```

to:

```python
    project_handler.register(app)
    confirm_handler.register(app)
    chat_handler.register(app)
    skill_hunter_handler.register(app)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_bot_skill_hunter_handler.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -q`
Expected: all tests PASS (no regressions in existing handler/main wiring).

- [ ] **Step 6: Commit**

```bash
git add app/bot/handlers/skill_hunter.py app/skill_hunter/__main__.py app/main.py \
    tests/test_bot_skill_hunter_handler.py
git commit -m "feat(skill-hunter): add /find_skills command and timer entry point"
```

---

### Task 6: systemd weekly timer + deploy script wiring

**Files:**
- Create: `deploy/skill-hunter.service`
- Create: `deploy/skill-hunter.timer`
- Modify: `deploy/deploy.sh`

**Interfaces:**
- Consumes: `app/skill_hunter/__main__.py` (Task 5) as the unit's `ExecStart` target.
- Produces: two systemd unit files deployable alongside the existing `aleks-agent.service`.

This task has no Python code and no pytest coverage -- systemd units are validated on the VPS at deploy time, not locally on this Windows dev machine. Steps below are direct file edits with manual verification instructions for the next VPS deploy.

- [ ] **Step 1: Create the oneshot service unit**

Create `deploy/skill-hunter.service`:

```ini
# deploy/skill-hunter.service
[Unit]
Description=Aleks skill hunter (one-shot weekly skill search)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/projects/Aleks
EnvironmentFile=/root/projects/Aleks/.env
ExecStart=/root/projects/Aleks/.venv/bin/python -m app.skill_hunter
```

- [ ] **Step 2: Create the weekly timer unit**

Create `deploy/skill-hunter.timer`:

```ini
# deploy/skill-hunter.timer
[Unit]
Description=Weekly trigger for Aleks skill hunter

[Timer]
OnCalendar=Mon 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Wire the units into deploy.sh**

Modify `deploy/deploy.sh`. Change the tar exclude line:

```bash
tar --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
    --exclude='.pytest_cache' --exclude='.env' --exclude='state.db' \
    -czf "$TARBALL" .
```

to also exclude the runtime history file:

```bash
tar --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
    --exclude='.pytest_cache' --exclude='.env' --exclude='state.db' \
    --exclude='skill_hunter_history.json*' \
    -czf "$TARBALL" .
```

Add a new step after the existing "Restarting aleks-agent service" step, before `echo "==> Done"`:

```bash
echo "==> Installing/enabling skill-hunter timer"
ssh "$REMOTE_HOST" "cp $REMOTE_DIR/deploy/skill-hunter.service $REMOTE_DIR/deploy/skill-hunter.timer /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now skill-hunter.timer"
```

- [ ] **Step 4: Manual verification (next VPS deploy)**

Expected, to confirm after the next `./deploy/deploy.sh` run on the VPS: `ssh aleks-agent systemctl list-timers skill-hunter.timer` shows a scheduled `NEXT` run, and `ssh aleks-agent systemctl status skill-hunter.service --no-pager` shows `enabled`/inactive-waiting (oneshot units are idle between runs). This step is recorded here as a manual check since no systemd runtime exists on the local Windows dev machine to verify automatically.

- [ ] **Step 5: Commit**

```bash
git add deploy/skill-hunter.service deploy/skill-hunter.timer deploy/deploy.sh
git commit -m "feat(skill-hunter): add weekly systemd timer and wire into deploy.sh"
```
