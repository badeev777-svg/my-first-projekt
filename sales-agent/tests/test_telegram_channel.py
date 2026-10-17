import httpx
import pytest

from app.config import Settings
from app.handoff import HandoffError, StubChannel, TelegramChannel, format_message
from app.main import create_app

TOKEN = "123:secret-token"


def channel(handler):
    return TelegramChannel(TOKEN, "42", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_lead_message_carries_full_contact_to_manager():
    seen = {}

    def handler(req):
        seen["url"], seen["body"] = str(req.url), req.read().decode()
        return httpx.Response(200, json={"ok": True})

    status = channel(handler).send("lead", {"id": 7, "contact_masked": "+7*** ***-**-89", "product_id": "tg-bot",
                                            "need": "бот"}, contact="+79123456789")
    assert status == "sent"
    assert seen["url"] == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert "+79123456789" in seen["body"] and '"chat_id":"42"' in seen["body"].replace(" ", "")


def test_handoff_message_names_reason_in_russian():
    text = format_message("handoff", {"id": 3, "reason": "client_request", "summary": "позовите человека"})
    assert "клиент просит человека" in text and "позовите человека" in text


def test_telegram_error_is_handoff_error():
    with pytest.raises(HandoffError):
        channel(lambda req: httpx.Response(400, json={"ok": False})).send("lead", {"id": 1})


def test_network_error_does_not_leak_token():
    def handler(req):
        raise httpx.ConnectError(f"cannot reach {req.url}")

    with pytest.raises(HandoffError) as e:
        channel(handler).send("lead", {"id": 1})
    assert TOKEN not in str(e.value) and e.value.__cause__ is None and e.value.__suppress_context__


def test_app_uses_telegram_only_when_both_settings_given(tmp_path):
    def chosen(**kw):
        return create_app(Settings(db_path=str(tmp_path / "x.db"), **kw)).state.channel

    assert isinstance(chosen(notify_bot_token=TOKEN, notify_chat_id="42"), TelegramChannel)
    assert isinstance(chosen(notify_bot_token=TOKEN), StubChannel)
    assert isinstance(chosen(), StubChannel)
