import threading
import time
from collections import deque
from collections.abc import Callable

import httpx

from app.messenger import Incoming, split_text

API = "https://api.avito.ru"
MAX_TEXT = 1000
SESSION_PREFIX = "avito:"


class AvitoError(Exception):
    pass


def parse_update(body: dict) -> Incoming | None:
    payload = body.get("payload") or {}
    if payload.get("type") != "message":
        return None  # в т.ч. проверочный {} при регистрации вебхука
    v = payload.get("value") or {}
    chat, mid = v.get("chat_id"), v.get("id")
    if not chat or not mid:
        return None
    text = (v.get("content") or {}).get("text")
    text = text if isinstance(text, str) else ""
    if str(v.get("author_id")) == str(v.get("user_id")):
        # Пишет аккаунт бизнеса: эхо ответа бота или Александр вручную — различает AvitoClient.is_own.
        return Incoming(str(chat), str(mid), text, from_owner=True)
    if v.get("type") != "text" or not text.strip():
        return None
    return Incoming(str(chat), str(mid), text)


class AvitoClient:
    def __init__(self, client_id: str, client_secret: str, user_id: str, http: httpx.Client | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_id = user_id
        self._http = http or httpx.Client(timeout=10)
        self._clock = clock
        self._token: tuple[str, float] | None = None
        self._sent: deque[tuple[str, str]] = deque(maxlen=500)
        self._lock = threading.Lock()

    def is_own(self, msg: Incoming) -> bool:
        # НЕ ПРОВЕРЕНО, совпадает ли id эха с id из ответа на отправку, поэтому сверяем и id, и текст.
        with self._lock:
            return (msg.peer, msg.mid) in self._sent or (msg.peer, msg.text.strip()) in self._sent

    def _remember(self, chat_id: str, key: str) -> None:
        with self._lock:
            self._sent.append((chat_id, key))

    def _access_token(self) -> str:
        if self._token and self._token[1] > self._clock():
            return self._token[0]
        try:
            # НЕ ПРОВЕРЕНО: client_id/client_secret полями формы (не Basic-auth).
            r = self._http.post(f"{API}/token", data={"grant_type": "client_credentials",
                                                      "client_id": self._client_id,
                                                      "client_secret": self._client_secret})
            data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise AvitoError(f"avito token {type(e).__name__}") from None
        if r.status_code >= 400 or not isinstance(data, dict) or "access_token" not in data:
            raise AvitoError(f"avito token status {r.status_code}")
        # Запас 60 с, чтобы токен не истёк посреди запроса.
        self._token = (data["access_token"], self._clock() + int(data.get("expires_in", 3600)) - 60)
        return self._token[0]

    def _post(self, what: str, path: str, payload: dict) -> dict:
        for attempt in (1, 2):
            try:
                r = self._http.post(API + path, json=payload,
                                    headers={"Authorization": f"Bearer {self._access_token()}"})
            except httpx.HTTPError as e:
                raise AvitoError(f"avito {what} {type(e).__name__}") from None
            if r.status_code == 401 and attempt == 1:
                self._token = None  # токен отозван раньше срока — берём новый
                continue
            if r.status_code >= 400:
                raise AvitoError(f"avito {what} status {r.status_code}")
            try:
                data = r.json()
            except ValueError:
                return {}
            return data if isinstance(data, dict) else {}
        raise AvitoError(f"avito {what} status 401")

    def send(self, chat_id: str, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
        for part in split_text(text, MAX_TEXT):
            # Текст запоминаем до отправки: эхо может прийти раньше, чем ответ на запрос.
            self._remember(chat_id, part.strip())
            data = self._post("send", f"/messenger/v1/accounts/{self._user_id}/chats/{chat_id}/messages",
                              {"type": "text", "message": {"text": part}})
            if data.get("id"):
                self._remember(chat_id, str(data["id"]))

    def subscribe(self, url: str) -> None:
        self._post("webhook", "/messenger/v3/webhook", {"url": url})
