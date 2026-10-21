from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.handoff import StubChannel
from app.main import create_app
from app.max_bot import CONTACT_BUTTONS, GREETING, MaxClient, MaxError, adapt_reply, parse_update
from app.pipeline import DEMO_REPLY
from tests.helpers import make_content, service

ROOT = Path(__file__).resolve().parent.parent
SECRET = "test-secret"


class FakeMax:
    def __init__(self):
        self.sent: list[tuple[str, str, list]] = []

    def send(self, user_id: str, text: str, buttons=None) -> None:
        self.sent.append((user_id, text, buttons or []))


def message(text: str, mid: str = "mid-1", user_id: int = 42, chat_type: str = "dialog") -> dict:
    return {"update_type": "message_created", "timestamp": 1,
            "message": {"sender": {"user_id": user_id, "name": "Иван", "is_bot": False},
                        "recipient": {"chat_id": 777, "chat_type": chat_type},
                        "body": {"mid": mid, "text": text}}}


@pytest.fixture
def bot(tmp_path):
    content = make_content(tmp_path / "content", [service()])
    settings = Settings(_env_file=None, cloudru_api_key="", db_path=str(tmp_path / "sales.db"),
                        content_dir=str(content), skills_dir=str(ROOT / "skills"),
                        max_bot_token="tok", max_webhook_secret=SECRET)
    fake = FakeMax()
    app = create_app(settings, channel=StubChannel(), max_client=fake)
    return TestClient(app), fake, app.state.store


def post(http: TestClient, update: dict, secret: str = SECRET) -> httpx.Response:
    return http.post("/api/max/webhook", json=update, headers={"X-Max-Bot-Api-Secret": secret})


def test_message_gets_reply_in_same_dialog(bot):
    http, fake, store = bot
    assert post(http, message("Нужен чат-бот")).json() == {"ok": True}
    assert fake.sent == [("42", DEMO_REPLY, [])]
    conv = store.latest_conversation("max:42")
    assert [role for role, _ in store.history(conv.id)] == ["user", "assistant"]


def test_wrong_secret_is_rejected(bot):
    http, fake, _ = bot
    assert post(http, message("привет"), secret="nope").status_code == 403
    assert fake.sent == []


def test_disabled_without_settings(tmp_path):
    content = make_content(tmp_path / "content", [service()])
    settings = Settings(_env_file=None, cloudru_api_key="", db_path=str(tmp_path / "s.db"),
                        content_dir=str(content), skills_dir=str(ROOT / "skills"))
    http = TestClient(create_app(settings, channel=StubChannel()))
    assert post(http, message("привет")).status_code == 404


def test_redelivery_is_not_answered_twice(bot):
    http, fake, _ = bot
    post(http, message("Нужен чат-бот", mid="m1"))
    post(http, message("Нужен чат-бот", mid="m1"))
    assert len(fake.sent) == 1


def test_start_and_restart_open_new_conversation(bot):
    http, fake, store = bot
    post(http, {"update_type": "bot_started", "chat_id": 777, "user": {"user_id": 42}})
    first = store.latest_conversation("max:42")
    post(http, message("/new", mid="m2"))
    assert store.latest_conversation("max:42").id != first.id
    assert [text for _, text, _ in fake.sent] == [GREETING, GREETING]


def test_group_chats_and_bots_are_ignored(bot):
    http, fake, _ = bot
    post(http, message("привет", chat_type="chat"))
    bot_msg = message("привет")
    bot_msg["message"]["sender"]["is_bot"] = True
    post(http, bot_msg)
    post(http, {"update_type": "message_edited"})
    assert fake.sent == []


def test_users_have_separate_conversations(bot):
    http, _, store = bot
    post(http, message("a", mid="x", user_id=1))
    post(http, message("b", mid="x", user_id=2))
    assert store.latest_conversation("max:1").id != store.latest_conversation("max:2").id


def test_parse_update_needs_text_and_ids():
    assert parse_update(message("  ")) is None
    assert parse_update({"update_type": "bot_started", "user": {}}) is None
    assert parse_update(message("hi")).text == "hi"


def test_adapt_reply_replaces_site_buttons():
    text, buttons = adapt_reply("Напишите в Telegram или MAX (кнопки под чатом).")
    assert "кнопки под чатом" not in text and buttons == CONTACT_BUTTONS
    text, buttons = adapt_reply("Этот диалог ждёт ответа человека (Александр).")
    assert buttons == CONTACT_BUTTONS
    assert adapt_reply("Если понадобится помощь, начните новый диалог.")[0].endswith("«Начать заново».")
    assert adapt_reply("Обычный ответ") == ("Обычный ответ", [])


def test_client_sends_token_in_header_and_buttons():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"message": {}})

    MaxClient("tok", httpx.Client(transport=httpx.MockTransport(handler))).send("42", "x", CONTACT_BUTTONS)
    assert seen["auth"] == "tok" and seen["url"].endswith("/messages?user_id=42")
    assert '"inline_keyboard"' in seen["body"]


def test_client_error_hides_token():
    client = MaxClient("tok", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))))
    with pytest.raises(MaxError) as e:
        client.send("42", "x")
    assert "tok" not in str(e.value)
