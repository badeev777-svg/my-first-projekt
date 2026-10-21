import secrets

import httpx

from app.messenger import Incoming, split_text

API = "https://api.vk.com/method"
VERSION = "5.199"
MAX_TEXT = 4000
SESSION_PREFIX = "vk:"


class VkError(Exception):
    pass


def parse_event(body: dict) -> Incoming | None:
    kind = body.get("type")
    obj = body.get("object") or {}
    if kind == "message_new":
        m = obj.get("message") or {}
        uid, text, mid = m.get("from_id"), m.get("text"), m.get("id") or m.get("conversation_message_id")
        # Только личный диалог с сообществом: в беседе peer_id (> 2e9) не совпадает с автором.
        if not isinstance(uid, int) or uid <= 0 or m.get("peer_id") != uid:
            return None
        if not isinstance(text, str) or not text.strip() or not mid:
            return None
        return Incoming(str(uid), str(mid), text)
    if kind == "message_reply" and obj.get("admin_author_id") and obj.get("peer_id"):
        # НЕ ПРОВЕРЕНО: admin_author_id есть только у ответа, написанного админом вручную, у сообщений бота его нет.
        # Если поля не окажется, бот просто не замолчит — сверить на живом сообществе.
        return Incoming(str(obj["peer_id"]), str(obj.get("id") or ""), None, from_owner=True)
    return None


class VkClient:
    def __init__(self, token: str, http: httpx.Client | None = None):
        self._token = token
        self._http = http or httpx.Client(timeout=10)

    def send(self, user_id: str, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
        for part in split_text(text, MAX_TEXT):
            # Токен в теле, а не в URL: URL попадает в логи и тексты исключений.
            data = {"peer_id": user_id, "message": part, "random_id": secrets.randbelow(2**31),
                    "access_token": self._token, "v": VERSION}
            try:
                r = self._http.post(f"{API}/messages.send", data=data)
                body = r.json()
            except (httpx.HTTPError, ValueError) as e:
                raise VkError(f"vk {type(e).__name__}") from None
            if r.status_code >= 400 or "error" in body:
                raise VkError(f"vk error {(body.get('error') or {}).get('error_code', r.status_code)}")
