from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from app.avito_bot import AvitoClient, AvitoError
from app.avito_bot import parse_update as parse_avito
from app.config import Settings
from app.handoff import StubChannel, format_message
from app.leads import Outcome
from app.main import create_app
from app.messenger import GREETING, Incoming, adapt_in_chat, channel_label, split_text
from app.pipeline import DEMO_REPLY, _status_key
from app.state import State
from app.vk_bot import VkClient, VkError, parse_event
from tests.helpers import make_content, service

ROOT = Path(__file__).resolve().parent.parent
VK_SECRET = "vk-secret"
AVITO_SECRET = "avito-path"


class FakeMessenger:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.own: set[str] = set()

    def send(self, peer: str, text: str, buttons=None) -> None:
        self.sent.append((peer, text))

    def is_own(self, msg: Incoming) -> bool:
        return msg.mid in self.own


def vk_message(text: str, mid: int = 1, uid: int = 42, peer: int | None = None) -> dict:
    return {"type": "message_new", "secret": VK_SECRET,
            "object": {"message": {"id": mid, "from_id": uid, "peer_id": peer or uid, "text": text}}}


def avito_message(text: str, mid: str = "m1", author: int = 7, chat: str = "c1") -> dict:
    return {"payload": {"type": "message", "value": {"id": mid, "chat_id": chat, "user_id": 100,
                                                     "author_id": author, "type": "text",
                                                     "content": {"text": text}}}}


@pytest.fixture
def bots(tmp_path):
    content = make_content(tmp_path / "content", [service()])
    settings = Settings(_env_file=None, cloudru_api_key="", db_path=str(tmp_path / "sales.db"),
                        content_dir=str(content), skills_dir=str(ROOT / "skills"),
                        vk_secret=VK_SECRET, vk_confirmation="abc123", avito_webhook_secret=AVITO_SECRET)
    vk, avito = FakeMessenger(), FakeMessenger()
    app = create_app(settings, channel=StubChannel(), vk_client=vk, avito_client=avito)
    return TestClient(app), vk, avito, app.state.store


def post_vk(http: TestClient, body: dict) -> httpx.Response:
    return http.post("/api/vk/callback", json=body)


def post_avito(http: TestClient, body: dict, secret: str = AVITO_SECRET) -> httpx.Response:
    return http.post(f"/api/avito/webhook/{secret}", json=body)


def test_vk_confirmation_returns_plain_string(bots):
    http, *_ = bots
    r = post_vk(http, {"type": "confirmation", "group_id": 1, "secret": VK_SECRET})
    assert r.text == "abc123" and r.headers["content-type"].startswith("text/plain")


def test_vk_wrong_secret_is_rejected(bots):
    http, vk, *_ = bots
    body = vk_message("привет")
    body["secret"] = "nope"
    assert post_vk(http, body).status_code == 403
    assert vk.sent == []


def test_vk_message_gets_reply_and_ok(bots):
    http, vk, _, store = bots
    r = post_vk(http, vk_message("Нужен чат-бот"))
    assert r.text == "ok"
    assert vk.sent == [("42", DEMO_REPLY)]
    assert store.latest_conversation("vk:42") is not None


def test_vk_group_chats_are_ignored(bots):
    http, vk, *_ = bots
    post_vk(http, vk_message("привет", peer=2000000001))
    assert vk.sent == []


def test_vk_restart_word_greets(bots):
    http, vk, *_ = bots
    post_vk(http, vk_message("Начать"))
    assert vk.sent == [("42", GREETING)]


def test_owner_reply_pauses_bot_until_restart(bots):
    http, vk, _, store = bots
    post_vk(http, vk_message("Нужен чат-бот", mid=1))
    post_vk(http, {"type": "message_reply", "secret": VK_SECRET,
                   "object": {"id": 2, "peer_id": 42, "from_id": -1, "admin_author_id": 5, "text": "Здравствуйте"}})
    assert store.latest_conversation("vk:42").state is State.HUMAN_PENDING
    post_vk(http, vk_message("ещё вопрос", mid=3))
    assert len(vk.sent) == 1  # пока диалог у человека, бот молчит
    post_vk(http, vk_message("Начать заново", mid=4))
    assert vk.sent[-1] == ("42", GREETING)


def test_vk_disabled_without_settings(tmp_path):
    content = make_content(tmp_path / "content", [service()])
    settings = Settings(_env_file=None, cloudru_api_key="", db_path=str(tmp_path / "s.db"),
                        content_dir=str(content), skills_dir=str(ROOT / "skills"))
    http = TestClient(create_app(settings, channel=StubChannel()))
    assert post_vk(http, vk_message("привет")).status_code == 404
    assert post_avito(http, avito_message("привет")).status_code == 404


def test_avito_message_gets_reply(bots):
    http, _, avito, _ = bots
    assert post_avito(http, avito_message("Нужен чат-бот")).json() == {"ok": True}
    assert avito.sent == [("c1", DEMO_REPLY)]


def test_avito_wrong_path_secret_is_404(bots):
    http, _, avito, _ = bots
    assert post_avito(http, avito_message("привет"), secret="nope").status_code == 404
    assert avito.sent == []


def test_avito_echo_is_ignored_but_manual_reply_pauses(bots):
    http, _, avito, store = bots
    post_avito(http, avito_message("Нужен чат-бот"))
    avito.own.add("echo")
    post_avito(http, avito_message(DEMO_REPLY, mid="echo", author=100))
    assert store.latest_conversation("avito:c1").state is not State.HUMAN_PENDING
    post_avito(http, avito_message("Сейчас посчитаю", mid="manual", author=100))
    assert store.latest_conversation("avito:c1").state is State.HUMAN_PENDING


def test_parse_avito_update():
    assert parse_avito({}) is None
    assert parse_avito(avito_message("  ")) is None
    msg = parse_avito(avito_message("hi", author=100))
    assert msg.from_owner and msg.peer == "c1"
    image = avito_message("")
    image["payload"]["value"]["type"] = "image"
    assert parse_avito(image) is None


def test_in_chat_texts_and_channel_label():
    # _status_key читает у диалога только session_id.
    vk_conv = SimpleNamespace(session_id="vk:1")
    site_conv = SimpleNamespace(session_id="site-sid")
    assert _status_key(Outcome(1, "sent", True), vk_conv) == "sent_in_chat"
    assert _status_key(Outcome(1, "failed", True), vk_conv) == "failed"
    assert _status_key(Outcome(1, "sent", True), site_conv) == "sent"
    assert channel_label("avito:c1") == "Avito" and channel_label("abc") == "сайт"
    assert adapt_in_chat("Если что, начните новый диалог.") == ("Если что, напишите «Начать заново».", [])


def test_format_message_shows_channel():
    text = format_message("lead", {"id": 3, "contact_masked": "x", "source": "ВКонтакте"}, contact="+79990000000")
    assert "Канал: ВКонтакте" in text
    assert "Канал" not in format_message("lead", {"id": 3, "contact_masked": "x"})


def test_split_text_respects_limit():
    parts = split_text("слово " * 400, 1000)
    assert all(len(p) <= 1000 for p in parts) and len(parts) == 3
    assert split_text("коротко", 1000) == ["коротко"]


def test_vk_client_sends_token_in_body_and_hides_it_on_error():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["form"] = parse_qs(request.read().decode())
        return httpx.Response(200, json={"response": 1})

    VkClient("tok", httpx.Client(transport=httpx.MockTransport(handler))).send("42", "x")
    assert "tok" not in seen["url"] and seen["form"]["access_token"] == ["tok"]
    assert seen["form"]["peer_id"] == ["42"]
    bad = VkClient("tok", httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"error": {"error_code": 5, "error_msg": "tok invalid"}}))))
    with pytest.raises(VkError) as e:
        bad.send("42", "x")
    assert "tok" not in str(e.value)


def test_avito_client_caches_token_and_remembers_echo():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/token":
            return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer at"
        return httpx.Response(200, json={"id": "sent-1"})

    client = AvitoClient("id", "secret", "100", httpx.Client(transport=httpx.MockTransport(handler)))
    client.send("c1", "привет")
    client.send("c1", "ещё")
    assert calls.count("/token") == 1
    assert calls[-1] == "/messenger/v1/accounts/100/chats/c1/messages"
    assert client.is_own(Incoming("c1", "sent-1", "", from_owner=True))
    assert client.is_own(Incoming("c1", "other-id", "привет", from_owner=True))
    assert not client.is_own(Incoming("c1", "x", "ручной ответ", from_owner=True))


def test_avito_client_retries_once_on_401_and_hides_secret():
    tokens = iter(["old", "new"])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(200, json={"access_token": next(tokens), "expires_in": 3600})
        ok = request.headers["authorization"] == "Bearer new"
        return httpx.Response(200 if ok else 401, json={})

    AvitoClient("id", "secret", "100", httpx.Client(transport=httpx.MockTransport(handler))).send("c1", "x")
    failing = AvitoClient("id", "secret", "100",
                          httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403))))
    with pytest.raises(AvitoError) as e:
        failing.send("c1", "x")
    assert "secret" not in str(e.value)


def test_access_log_masks_avito_secret():
    import logging
    from app.main import MaskAvitoSecret
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("1.2.3.4:5", "POST", "/api/avito/webhook/topsecret", "1.1", 200), None)
    MaskAvitoSecret().filter(rec)
    assert "topsecret" not in rec.getMessage() and "/api/avito/webhook/***" in rec.getMessage()
