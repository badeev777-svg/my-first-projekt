import logging
from typing import Protocol

import httpx

log = logging.getLogger("sales_agent.handoff")

REASONS = {
    "client_request": "клиент просит человека",
    "lead_not_delivered": "заявка не доставлена",
    "price_conflict": "конфликт цены",
    "quality_review": "ответ требует проверки",
    "model_request": "бот передал разговор",
}


class HandoffError(Exception):
    pass


class Channel(Protocol):
    def send(self, kind: str, payload: dict, contact: str = "") -> str: ...


class StubChannel:
    """Канал-заглушка: пишет в лог только маскированные данные, полный контакт не сохраняет."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[tuple[str, dict]] = []
        self.contacts: list[str] = []

    def send(self, kind: str, payload: dict, contact: str = "") -> str:
        if self.fail:
            raise HandoffError("stub channel is configured to fail")
        self.sent.append((kind, payload))
        self.contacts.append(contact)
        log.info("handoff %s %s", kind, payload)
        return "sent_stub"


def format_message(kind: str, payload: dict, contact: str = "") -> str:
    # Из VK и Avito клиенту отвечают в том же чате — менеджеру нужно знать, где его искать.
    where = f"Канал: {payload['source']}\n" if payload.get("source") else ""
    if kind == "lead":
        return (f"Новая заявка №{payload['id']}\n{where}"
                f"Контакт: {contact or payload.get('contact_masked', '—')}\n"
                f"Услуга: {payload.get('product_id', 'unknown')}\n"
                f"Задача: {payload.get('need', '')}")
    reason = payload.get("reason", "")
    return (f"Нужен человек, передача №{payload['id']}\n{where}"
            f"Причина: {REASONS.get(reason, reason)}\n"
            f"{payload.get('summary', '')}")


class TelegramChannel:
    """Уведомления менеджеру через Bot API; полный контакт уходит только сюда (на это клиент дал согласие)."""

    def __init__(self, token: str, chat_id: str, http: httpx.Client | None = None):
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id
        self._http = http or httpx.Client(timeout=10)

    def send(self, kind: str, payload: dict, contact: str = "") -> str:
        try:
            r = self._http.post(self._url, json={"chat_id": self._chat_id, "text": format_message(kind, payload, contact)})
            ok = r.status_code == 200 and r.json().get("ok") is True
        except (httpx.HTTPError, ValueError) as e:
            # Текст исключения httpx содержит URL с токеном — в лог уходит только тип ошибки.
            raise HandoffError(f"telegram {type(e).__name__}") from None
        if not ok:
            raise HandoffError(f"telegram status {r.status_code}")
        return "sent"
