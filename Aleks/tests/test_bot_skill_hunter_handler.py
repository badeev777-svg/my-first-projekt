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
