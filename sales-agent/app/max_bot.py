import httpx

from app.messenger import Incoming

API = "https://platform-api2.max.ru"
MAX_TEXT = 4000
SESSION_PREFIX = "max:"
CONTACT_BUTTONS = [("MAX", "https://max.ru/u/f9LHodD0cOIRnmiaTLmNbAO_bPk7XetTZURYbnTQTgBeGajyv88HLxyWeT4"),
                   ("Telegram", "https://t.me/CowboyAleksandr")]


class MaxError(Exception):
    pass


def parse_update(body: dict) -> Incoming | None:
    # НЕ ПРОВЕРЕНО: вложенность message/sender/recipient/body в message_created в документации без примера —
    # пересказано по описанию объектов Message; первый живой апдейт сверить по логу «max update skipped».
    kind = body.get("update_type")
    if kind == "bot_started":
        uid = (body.get("user") or {}).get("user_id")
        return Incoming(str(uid), "", None) if uid is not None else None
    if kind != "message_created":
        return None
    msg = body.get("message") or {}
    sender = msg.get("sender") or {}
    # Бот отвечает только в личном диалоге: в групповом чате он видел бы чужие сообщения.
    if sender.get("is_bot") or (msg.get("recipient") or {}).get("chat_type") not in (None, "dialog"):
        return None
    content = msg.get("body") or {}
    text, mid, uid = content.get("text"), content.get("mid"), sender.get("user_id")
    if not isinstance(text, str) or not text.strip() or not mid or uid is None:
        return None
    return Incoming(str(uid), str(mid), text)


def adapt_reply(reply: str) -> tuple[str, list[tuple[str, str]]]:
    # Тексты пайплайна написаны для сайта (кнопки под чатом, новый диалог кнопкой); в MAX — ссылки и команда.
    reply = reply.replace("начните новый диалог", "напишите «Начать заново»")
    if "кнопки под чатом" in reply:
        return reply.replace("кнопки под чатом", "ссылки ниже"), CONTACT_BUTTONS
    if "ждёт ответа человека" in reply:
        return reply + "\nНаписать Александру напрямую — ссылки ниже.", CONTACT_BUTTONS
    return reply, []


class MaxClient:
    def __init__(self, token: str, http: httpx.Client | None = None):
        self._token = token
        self._http = http or httpx.Client(timeout=10)

    def send(self, user_id: str, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
        payload: dict = {"text": text[:MAX_TEXT]}
        if buttons:
            row = [{"type": "link", "text": label, "url": url} for label, url in buttons]
            payload["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": [row]}}]
        try:
            r = self._http.post(API + "/messages", params={"user_id": user_id},
                                headers={"Authorization": self._token}, json=payload)
        except httpx.HTTPError as e:
            raise MaxError(f"max {type(e).__name__}") from None
        if r.status_code >= 400:
            raise MaxError(f"max status {r.status_code}")
