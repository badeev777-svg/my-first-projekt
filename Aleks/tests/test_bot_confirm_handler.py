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
