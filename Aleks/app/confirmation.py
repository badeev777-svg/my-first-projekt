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
