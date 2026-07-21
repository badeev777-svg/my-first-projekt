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


@pytest.mark.asyncio
async def test_cmd_project_ignores_unauthorized_user() -> None:
    update, context = _update(user_id=999, args=["aleks"])

    await cmd_project(update, context)

    update.message.reply_text.assert_not_called()
    context.bot_data["state"].set_active_project.assert_not_called()
