import pytest

from app.state import State, can_transition, model_may_set, parse_state

S = State


@pytest.mark.parametrize("src,dst", [
    (S.NEW, S.DISCOVERY), (S.NEW, S.OFFER), (S.DISCOVERY, S.OFFER), (S.OFFER, S.DISCOVERY),
    (S.OFFER, S.CONSENT_PENDING), (S.CONSENT_PENDING, S.LEAD_DRAFT), (S.CONSENT_PENDING, S.OFFER),
    (S.LEAD_DRAFT, S.HUMAN_PENDING), (S.HUMAN_PENDING, S.CLOSED), (S.DISCOVERY, S.DISCOVERY),
    (S.NEW, S.HUMAN_PENDING), (S.OFFER, S.CLOSED),
])
def test_allowed(src, dst):
    assert can_transition(src, dst)


@pytest.mark.parametrize("src,dst", [
    (S.NEW, S.CONSENT_PENDING), (S.NEW, S.LEAD_DRAFT), (S.DISCOVERY, S.LEAD_DRAFT),
    (S.CLOSED, S.DISCOVERY), (S.CLOSED, S.HUMAN_PENDING), (S.HUMAN_PENDING, S.DISCOVERY),
    (S.HUMAN_PENDING, S.OFFER), (S.LEAD_DRAFT, S.OFFER),
])
def test_forbidden(src, dst):
    assert not can_transition(src, dst)


def test_model_cannot_set_code_only_states():
    assert model_may_set(S.DISCOVERY, S.OFFER)
    assert model_may_set(S.OFFER, S.CONSENT_PENDING)
    assert model_may_set(S.DISCOVERY, S.CONSENT_PENDING)  # через offer, как _reachable в pipeline
    assert not model_may_set(S.LEAD_DRAFT, S.CONSENT_PENDING)
    assert not model_may_set(S.CONSENT_PENDING, S.LEAD_DRAFT)
    assert not model_may_set(S.OFFER, S.HUMAN_PENDING)
    assert not model_may_set(S.OFFER, S.CLOSED)


def test_parse_state():
    assert parse_state("offer") is S.OFFER
    assert parse_state("bogus") is None
