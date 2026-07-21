# tests/test_bot_confirm_handler.py
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import BadRequest

from app.bot.handlers.confirm import on_confirmation_callback
from app.config import Settings
from app.confirmation import ConfirmationBridge

AUTHORIZED_USER_ID = 42


def _settings() -> Settings:
    return Settings(
        telegram_bot_token="t",
        allowed_user_id=AUTHORIZED_USER_ID,
        anthropic_api_key="k",
        _env_file=None,
    )


def _update(data: str, user_id: int = AUTHORIZED_USER_ID):
    update = MagicMock()
    update.effective_user.id = user_id
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    context = MagicMock()
    bridge = ConfirmationBridge(timeout_seconds=5)
    context.bot_data = {"confirmation_bridge": bridge, "settings": _settings()}
    return update, context, bridge


@pytest.mark.asyncio
async def test_approve_resolves_bridge_true() -> None:
    update, context, bridge = _update("corr-1:yes")
    future = bridge.pending["corr-1"] = asyncio.get_event_loop().create_future()

    await on_confirmation_callback(update, context)

    assert future.result() is True
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)


@pytest.mark.asyncio
async def test_reject_resolves_bridge_false() -> None:
    update, context, bridge = _update("corr-2:no")
    future = bridge.pending["corr-2"] = asyncio.get_event_loop().create_future()

    await on_confirmation_callback(update, context)

    assert future.result() is False


@pytest.mark.asyncio
async def test_ignores_unauthorized_user() -> None:
    update, context, bridge = _update("corr-3:yes", user_id=999)
    future = bridge.pending["corr-3"] = asyncio.get_event_loop().create_future()

    await on_confirmation_callback(update, context)

    assert not future.done()
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_reply_markup.assert_not_awaited()


@pytest.mark.asyncio
async def test_double_tap_does_not_raise() -> None:
    update, context, bridge = _update("corr-4:yes")
    future = bridge.pending["corr-4"] = asyncio.get_event_loop().create_future()

    await on_confirmation_callback(update, context)
    assert future.result() is True

    update.callback_query.edit_message_reply_markup = AsyncMock(
        side_effect=BadRequest("Message is not modified")
    )

    await on_confirmation_callback(update, context)
