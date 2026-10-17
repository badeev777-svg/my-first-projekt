import pytest

from app.catalog import Policy
from app.handoff import StubChannel
from app.leads import create_handoff, create_lead, extract_contact, mask_contact, mask_text
from app.store import Store

APPROVED = Policy("на вы", "Александр", "согласие", True, ())
UNAPPROVED = Policy("на вы", "Александр", "согласие", False, ())


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "sales.db"))


@pytest.mark.parametrize("text,expected", [
    ("мой номер +7 (912) 345-67-89", "+79123456789"),
    ("звоните 89123456789", "+79123456789"),
    ("пишите на ivan.petrov@example.com", "ivan.petrov@example.com"),
    ("контакта не будет", None),
    ("7 912 345 67 89", "+79123456789"),
    ("8.912.345.67.89", "+79123456789"),
    ("9123456789", "+79123456789"),
    ("артикул 812345678901", None),
    ("итого 8 000 000 00 00", None),
    ("в 2024 году", None),
    ("цена 50 000 ₽", None),
])
def test_extract_contact(text, expected):
    assert extract_contact(text) == expected


def test_masks():
    assert mask_contact("+79123456789") == "+7*** ***-**-89"
    assert mask_contact("ivan@example.com") == "i***@example.com"
    assert "345-67-89" not in mask_text("тел +7 912 345-67-89, спасибо")


@pytest.mark.parametrize("text", ["тел 7 912 345 67 89", "тел 8.912.345.67.89", "тел 9123456789"])
def test_mask_text_masks_bare_and_dotted_phones(text):
    masked = mask_text(text)
    assert "912 345" not in masked and "345 67" not in masked and "9123456789" not in masked
    assert "+7*** ***-**-89" in masked


@pytest.mark.parametrize("text", ["артикул 812345678901", "итого 8 000 000 00 00", "в 2024 году", "цена 50 000 ₽"])
def test_mask_text_leaves_non_phones_untouched(text):
    assert mask_text(text) == text


def test_lead_payload_from_bare_phone_has_no_digits_leak(store):
    text = "перезвоните 7 912 345 67 89"
    ch = StubChannel()
    create_lead(store, ch, conversation_id=store.create_conversation("s").id, contact=extract_contact(text),
                need=text, product_id="tg-bot", policy=APPROVED, demo=False)
    payload = str(ch.sent[0][1])
    assert "912345" not in payload and "345 67" not in payload and "+79123456789" not in payload


def lead(store, channel, policy=APPROVED, demo=False, cid=None):
    cid = cid or store.create_conversation("s").id
    return cid, create_lead(store, channel, conversation_id=cid, contact="+79123456789", need="бот для записи",
                            product_id="tg-bot", policy=policy, demo=demo)


def test_unapproved_consent_is_demo_and_not_sent(store):
    ch = StubChannel()
    _, out = lead(store, ch, policy=UNAPPROVED)
    row = store.get_lead(out.id)
    assert out.delivery_status == "demo" and ch.sent == []
    assert row["contact"] == "" and row["contact_masked"] == "+7*** ***-**-89"
    assert row["consent_status"] == "demo" and row["consent_time"] is None


def test_demo_mode_is_demo_even_with_approved_consent(store):
    ch = StubChannel()
    _, out = lead(store, ch, demo=True)
    row = store.get_lead(out.id)
    assert out.delivery_status == "demo" and ch.sent == []
    assert row["consent_status"] == "demo" and row["consent_time"] is None


def test_approved_lead_is_sent_with_masked_payload(store):
    ch = StubChannel()
    _, out = lead(store, ch)
    row = store.get_lead(out.id)
    assert out.delivery_status == "sent_stub" and out.created
    assert row["contact"] == "+79123456789"
    assert row["consent_status"] == "given" and row["consent_time"] is not None
    kind, payload = ch.sent[0]
    assert kind == "lead" and "+79123456789" not in str(payload)
    assert ch.contacts == ["+79123456789"]


def test_repeat_returns_same_lead_without_resend(store):
    ch = StubChannel()
    cid, first = lead(store, ch)
    _, second = lead(store, ch, cid=cid)
    assert second.id == first.id and second.created is False
    assert len(ch.sent) == 1


def test_channel_failure_is_failed_not_sent(store):
    ch = StubChannel(fail=True)
    cid, out = lead(store, ch)
    assert out.delivery_status == "failed"
    assert store.get_lead(out.id)["delivery_status"] == "failed"
    _, again = lead(store, ch, cid=cid)
    assert again.delivery_status == "failed" and again.id == out.id


def test_handoff_idempotent_per_reason(store):
    ch = StubChannel()
    cid = store.create_conversation("s").id
    kw = dict(conversation_id=cid, summary="клиент +79123456789 просит человека", question="позовите", demo=False)
    a = create_handoff(store, ch, reason="client_request", **kw)
    b = create_handoff(store, ch, reason="client_request", **kw)
    c = create_handoff(store, ch, reason="price_conflict", **kw)
    assert a.id == b.id and c.id != a.id and len(ch.sent) == 2
    assert "+79123456789" not in store.get_handoff(a.id)["summary"]
