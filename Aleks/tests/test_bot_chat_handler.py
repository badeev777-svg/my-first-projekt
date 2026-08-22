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
    state.list_all_projects.return_value = {"aleks": "/root/projects/Aleks"}
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
async def test_replies_gracefully_when_active_project_config_missing() -> None:
    """The stored active_project can point at a project that no longer
    exists in settings.projects (renamed/removed from config). This must
    not raise an unhandled KeyError inside `async with lock:` -- the user
    should get a message telling them to pick a project again."""
    update, context, state = _update_and_context()
    state.get_active_project.return_value = "renamed-or-gone"

    await chat_module.on_text_message(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "/projects" in update.message.reply_text.call_args.args[0]
    assert context.bot_data["project_locks"]["renamed-or-gone"].locked() is False


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


@pytest.mark.asyncio
async def test_exception_from_run_turn_replies_error_and_releases_lock(monkeypatch) -> None:
    update, context, _ = _update_and_context()

    async def fake_run_turn(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "Не получилось выполнить запрос, попробуй позже."
    )
    assert context.bot_data["project_locks"]["aleks"].locked() is False


@pytest.mark.asyncio
async def test_run_turn_retries_on_transient_failure_then_succeeds(monkeypatch) -> None:
    update, context, state = _update_and_context()
    attempts = 0

    async def flaky_run_turn(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RuntimeError("transient network error")
        await kwargs["on_text"]("Готово")
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", flaky_run_turn)
    monkeypatch.setattr(chat_module, "_RETRY_WAIT_SECONDS", 0)

    await chat_module.on_text_message(update, context)

    assert attempts == 2
    context.bot.send_message.assert_awaited_once_with(chat_id=100, text="Готово")
    state.set_session_id.assert_awaited_once_with("aleks", "session-xyz")
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_run_turn_gives_up_after_max_attempts(monkeypatch) -> None:
    update, context, _ = _update_and_context()
    attempts = 0

    async def always_fails(**kwargs):
        nonlocal attempts
        attempts += 1
        raise RuntimeError("still broken")

    monkeypatch.setattr(chat_module, "run_turn", always_fails)
    monkeypatch.setattr(chat_module, "_RETRY_WAIT_SECONDS", 0)

    await chat_module.on_text_message(update, context)

    assert attempts == chat_module._RETRY_ATTEMPTS
    update.message.reply_text.assert_awaited_once_with(
        "Не получилось выполнить запрос, попробуй позже."
    )
    assert context.bot_data["project_locks"]["aleks"].locked() is False


@pytest.mark.asyncio
async def test_session_id_persisted_immediately_when_learned_mid_turn(monkeypatch) -> None:
    """If run_turn learns a session_id (via on_session_id) but then raises
    before returning, that session_id must be persisted right away -- not
    only after the whole retrying block succeeds -- so a subsequent retry
    (or the next message, if retries are exhausted) can resume instead of
    restarting the conversation from scratch."""
    update, context, state = _update_and_context()

    async def fake_run_turn(**kwargs):
        await kwargs["on_session_id"]("sess-mid-turn")
        raise RuntimeError("Stream closed")

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)
    monkeypatch.setattr(chat_module, "_RETRY_WAIT_SECONDS", 0)

    await chat_module.on_text_message(update, context)

    state.set_session_id.assert_any_await("aleks", "sess-mid-turn")


@pytest.mark.asyncio
async def test_retry_resumes_from_session_id_learned_in_earlier_attempt(monkeypatch) -> None:
    """Regression test for the actual incident: session_id used to be read
    once from StateStore before the tenacity retry loop started and passed
    as a fixed kwarg, so every retry attempt reused the same (stale) value
    even after an earlier attempt had already learned a fresh one --
    forcing each retry to re-explore the whole project from scratch."""
    update, context, state = _update_and_context()
    seen_session_ids: list[str | None] = []
    attempts = 0

    async def flaky_run_turn(**kwargs):
        nonlocal attempts
        attempts += 1
        seen_session_ids.append(kwargs["session_id"])
        if attempts == 1:
            await kwargs["on_session_id"]("sess-mid-turn")
            raise RuntimeError("transient network error")
        await kwargs["on_text"]("Готово")
        return "sess-final"

    monkeypatch.setattr(chat_module, "run_turn", flaky_run_turn)
    monkeypatch.setattr(chat_module, "_RETRY_WAIT_SECONDS", 0)

    await chat_module.on_text_message(update, context)

    assert seen_session_ids == [None, "sess-mid-turn"]
    state.set_session_id.assert_awaited_with("aleks", "sess-final")


@pytest.mark.asyncio
async def test_billing_error_is_not_retried(monkeypatch) -> None:
    update, context, _ = _update_and_context()
    attempts = 0

    async def billing_failure(**kwargs):
        nonlocal attempts
        attempts += 1
        raise RuntimeError("API Error: 402 Недостаточно средств")

    monkeypatch.setattr(chat_module, "run_turn", billing_failure)
    monkeypatch.setattr(chat_module, "_RETRY_WAIT_SECONDS", 0)

    await chat_module.on_text_message(update, context)

    assert attempts == 1
    update.message.reply_text.assert_awaited_once_with(
        "Не получилось выполнить запрос, попробуй позже."
    )


@pytest.mark.asyncio
async def test_hung_run_turn_times_out_and_gives_up(monkeypatch) -> None:
    update, context, _ = _update_and_context()
    context.bot_data["settings"].run_turn_timeout_seconds = 0.01
    attempts = 0

    async def hangs_forever(**kwargs):
        nonlocal attempts
        attempts += 1
        await asyncio.sleep(10)

    monkeypatch.setattr(chat_module, "run_turn", hangs_forever)
    monkeypatch.setattr(chat_module, "_RETRY_WAIT_SECONDS", 0)

    await chat_module.on_text_message(update, context)

    assert attempts == chat_module._RETRY_ATTEMPTS
    update.message.reply_text.assert_awaited_once_with(
        "Не получилось выполнить запрос, попробуй позже."
    )


@pytest.mark.asyncio
async def test_send_confirmation_prompt_builds_keyboard_with_correlation_id(monkeypatch) -> None:
    update, context, _ = _update_and_context()

    async def fake_run_turn(**kwargs):
        await kwargs["send_confirmation_prompt"]("corr-1", "Bash", {"command": "git push"})
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    context.bot.send_message.assert_awaited_once()
    call_kwargs = context.bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == 100
    buttons = call_kwargs["reply_markup"].inline_keyboard[0]
    assert buttons[0].callback_data == "corr-1:yes"
    assert buttons[1].callback_data == "corr-1:no"


@pytest.mark.asyncio
async def test_lock_released_after_successful_turn(monkeypatch) -> None:
    update, context, _ = _update_and_context()

    async def fake_run_turn(**kwargs):
        await kwargs["on_text"]("Готово")
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    assert context.bot_data["project_locks"]["aleks"].locked() is False


@pytest.mark.asyncio
async def test_confirmation_timeout_sends_notice(monkeypatch) -> None:
    update, context, _ = _update_and_context()

    async def fake_run_turn(**kwargs):
        await kwargs["on_confirmation_timeout"]()
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    context.bot.send_message.assert_awaited_once_with(
        chat_id=100, text="Действие отменено по таймауту ожидания подтверждения."
    )


@pytest.mark.asyncio
async def test_new_project_trigger_short_circuits_before_run_turn(monkeypatch, tmp_path) -> None:
    update, context, state = _update_and_context(text="новый проект эпоксидка")
    context.bot_data["settings"].projects_root = str(tmp_path)
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
async def test_new_project_trigger_works_even_with_no_active_project(monkeypatch, tmp_path) -> None:
    update, context, state = _update_and_context(text="создай новый проект часы")
    context.bot_data["settings"].projects_root = str(tmp_path)
    state.get_active_project.return_value = None
    state.list_all_projects.return_value = {}

    await chat_module.on_text_message(update, context)

    state.set_active_project.assert_awaited_once_with(42, "chasy")


@pytest.mark.asyncio
async def test_new_project_trigger_failure_replies_gracefully(monkeypatch, tmp_path) -> None:
    update, context, state = _update_and_context(text="новый проект часы")
    context.bot_data["settings"].projects_root = str(tmp_path)
    state.list_all_projects.return_value = {}
    state.add_dynamic_project.side_effect = RuntimeError("db locked")

    await chat_module.on_text_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "Не получилось выполнить запрос, попробуй позже."
    )


@pytest.mark.asyncio
async def test_run_turn_receives_effort_and_budget_from_settings(monkeypatch) -> None:
    update, context, _ = _update_and_context()
    context.bot_data["settings"].agent_effort = "low"
    context.bot_data["settings"].max_turn_budget_usd = 1.5
    captured_kwargs = {}

    async def fake_run_turn(**kwargs):
        captured_kwargs.update(kwargs)
        return "session-xyz"

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    await chat_module.on_text_message(update, context)

    assert captured_kwargs["effort"] == "low"
    assert captured_kwargs["max_budget_usd"] == 1.5


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
