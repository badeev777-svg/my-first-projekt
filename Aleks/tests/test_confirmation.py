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


@pytest.mark.asyncio
async def test_on_timeout_called_on_timeout() -> None:
    bridge = ConfirmationBridge(timeout_seconds=0.05)
    timeout_calls: list[str] = []

    async def send_prompt(correlation_id: str) -> None:
        return None  # user never answers

    async def on_timeout(correlation_id: str) -> None:
        timeout_calls.append(correlation_id)

    approved = await bridge.request("corr-4", send_prompt, on_timeout)

    assert approved is False
    assert timeout_calls == ["corr-4"]


@pytest.mark.asyncio
async def test_on_timeout_not_called_when_resolved_before_timeout() -> None:
    bridge = ConfirmationBridge(timeout_seconds=5)
    timeout_calls: list[str] = []

    async def send_prompt(correlation_id: str) -> None:
        bridge.resolve(correlation_id, True)

    async def on_timeout(correlation_id: str) -> None:
        timeout_calls.append(correlation_id)

    approved = await bridge.request("corr-5", send_prompt, on_timeout)

    assert approved is True
    assert timeout_calls == []
