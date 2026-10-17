import logging
from typing import Protocol

log = logging.getLogger("sales_agent.handoff")


class HandoffError(Exception):
    pass


class Channel(Protocol):
    def send(self, kind: str, payload: dict) -> str: ...


class StubChannel:
    """Канал-заглушка до выбора владельцем реального канала (v1): пишет в лог только маскированные данные."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[tuple[str, dict]] = []

    def send(self, kind: str, payload: dict) -> str:
        if self.fail:
            raise HandoffError("stub channel is configured to fail")
        self.sent.append((kind, payload))
        log.info("handoff %s %s", kind, payload)
        return "sent_stub"
