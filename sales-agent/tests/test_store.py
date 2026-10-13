import sqlite3

import pytest

from app.state import State
from app.store import CLAIM_TTL_SECONDS, AlreadyProcessing, Store


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "db" / "sales.db"))


@pytest.fixture
def clock():
    now = [1000.0]
    return now, (lambda: now[0])


@pytest.fixture
def clocked_store(tmp_path, clock):
    return Store(str(tmp_path / "sales.db"), clock=clock[1])


def lead_kwargs(cid: str, key: str = "lead:x") -> dict:
    return dict(conversation_id=cid, idempotency_key=key, contact_masked="+7*** ***-**-67", contact="",
                consent_status="given", consent_time="2026-10-13T10:00:00+00:00", need="бот",
                product_id="tg-bot", next_step="звонок Александра", delivery_status="demo")


def test_conversation_lifecycle(store):
    conv = store.create_conversation("sess-1")
    assert conv.state is State.NEW and conv.stopped is False
    store.set_state(conv.id, State.OFFER)
    store.set_stopped(conv.id, True)
    store.set_product(conv.id, "tg-bot")
    got = store.get_conversation(conv.id)
    assert got.state is State.OFFER and got.stopped is True and got.session_id == "sess-1"
    assert got.product_id == "tg-bot" and conv.product_id is None
    assert store.get_conversation("nope") is None


def test_claim_then_repeat_returns_saved_response(store):
    cid = store.create_conversation("s").id
    assert store.claim_message(cid, "m1", "привет") is None
    store.save_response(cid, "m1", {"reply": "Здравствуйте"}, reply="Здравствуйте", skill="sales-discovery")
    assert store.claim_message(cid, "m1", "привет") == {"reply": "Здравствуйте"}


def test_claim_is_exclusive(store):
    cid = store.create_conversation("s").id
    assert store.claim_message(cid, "m1", "привет") is None
    with pytest.raises(AlreadyProcessing):
        store.claim_message(cid, "m1", "привет")


def test_release_claim_allows_retry(store):
    cid = store.create_conversation("s").id
    store.claim_message(cid, "m1", "привет")
    store.release_claim(cid, "m1")
    assert store.claim_message(cid, "m1", "привет") is None
    assert store.history(cid) == [("user", "привет")]


def test_same_client_id_in_other_conversation_is_independent(store):
    a = store.create_conversation("s").id
    b = store.create_conversation("s").id
    assert store.claim_message(a, "m1", "x") is None
    assert store.claim_message(b, "m1", "y") is None


def test_history_order_and_limit(store):
    cid = store.create_conversation("s").id
    for i in range(3):
        store.claim_message(cid, f"m{i}", f"вопрос {i}")
        store.save_response(cid, f"m{i}", {}, reply=f"ответ {i}", skill=None)
    assert store.history(cid, limit=2) == [("user", "вопрос 2"), ("assistant", "ответ 2")]
    assert store.history(cid)[0] == ("user", "вопрос 0")


def test_lead_idempotency(store):
    cid = store.create_conversation("s").id
    first = store.create_lead(**lead_kwargs(cid))
    second = store.create_lead(**lead_kwargs(cid))
    assert first[1] is True and second == (first[0], False)
    store.set_lead_delivery(first[0], "failed")
    assert store.get_lead(first[0])["delivery_status"] == "failed"
    assert len(store.list_leads()) == 1


def test_handoff_idempotency(store):
    cid = store.create_conversation("s").id
    kw = dict(conversation_id=cid, idempotency_key="handoff:x:client_request", reason="client_request",
              summary="просит человека", question="позовите менеджера", delivery_status="demo")
    hid, created = store.create_handoff(**kw)
    assert created and store.create_handoff(**kw) == (hid, False)
    store.set_handoff_delivery(hid, "sent_stub")
    assert store.get_handoff(hid)["delivery_status"] == "sent_stub"
    assert [h["id"] for h in store.list_handoffs()] == [hid]


def test_conversations_in_state(store):
    a = store.create_conversation("s")
    store.create_conversation("s")
    store.set_state(a.id, State.HUMAN_PENDING)
    assert [c.id for c in store.conversations_in(State.HUMAN_PENDING)] == [a.id]


def test_data_survives_new_store_instance(tmp_path):
    path = str(tmp_path / "sales.db")
    cid = Store(path).create_conversation("s").id
    assert Store(path).get_conversation(cid) is not None


def test_lead_constraint_violation_raises_and_saves_nothing(store):
    cid = store.create_conversation("s").id
    with pytest.raises(sqlite3.IntegrityError):
        store.create_lead(**{**lead_kwargs(cid), "need": None})
    assert store.list_leads() == []


def test_fresh_claim_conflict_raises(clocked_store, clock):
    now, _ = clock
    cid = clocked_store.create_conversation("s").id
    assert clocked_store.claim_message(cid, "m1", "привет") is None
    now[0] += CLAIM_TTL_SECONDS
    with pytest.raises(AlreadyProcessing):
        clocked_store.claim_message(cid, "m1", "привет")


def test_stale_claim_is_taken_over(clocked_store, clock):
    now, _ = clock
    cid = clocked_store.create_conversation("s").id
    assert clocked_store.claim_message(cid, "m1", "привет") is None
    now[0] += CLAIM_TTL_SECONDS + 1
    assert clocked_store.claim_message(cid, "m1", "привет") is None
    assert clocked_store.history(cid) == [("user", "привет")]
    with pytest.raises(AlreadyProcessing):
        clocked_store.claim_message(cid, "m1", "привет")
