from enum import StrEnum


class State(StrEnum):
    NEW = "new"
    DISCOVERY = "discovery"
    OFFER = "offer"
    CONSENT_PENDING = "consent_pending"
    LEAD_DRAFT = "lead_draft"
    HUMAN_PENDING = "human_pending"
    CLOSED = "closed"


_FORWARD: dict[State, set[State]] = {
    State.NEW: {State.DISCOVERY, State.OFFER},
    State.DISCOVERY: {State.DISCOVERY, State.OFFER},
    State.OFFER: {State.OFFER, State.DISCOVERY, State.CONSENT_PENDING},
    State.CONSENT_PENDING: {State.CONSENT_PENDING, State.OFFER, State.DISCOVERY, State.LEAD_DRAFT},
    State.LEAD_DRAFT: {State.LEAD_DRAFT},
    State.HUMAN_PENDING: {State.HUMAN_PENDING},
    State.CLOSED: {State.CLOSED},
}

# Заявку, передачу человеку и закрытие делает только код.
_MODEL_STATES = {State.DISCOVERY, State.OFFER, State.CONSENT_PENDING}


def can_transition(src: State, dst: State) -> bool:
    if src is State.CLOSED:
        return dst is State.CLOSED
    if dst in (State.HUMAN_PENDING, State.CLOSED):
        return True
    return dst in _FORWARD[src]


def model_may_set(src: State, dst: State) -> bool:
    return (dst is src or dst in _MODEL_STATES) and can_transition(src, dst)


def parse_state(value: str) -> State | None:
    try:
        return State(value)
    except ValueError:
        return None
