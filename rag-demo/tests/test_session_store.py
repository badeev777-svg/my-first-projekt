import numpy as np

from app.chunker import Chunk
from app.session_store import SessionStore


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_create_and_get():
    store = SessionStore(ttl_seconds=60)
    s = store.create()
    assert len(s.id) >= 32
    assert store.get(s.id) is s
    assert store.get("unknown") is None


def test_expired_session_removed_on_get():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    s = store.create()
    clock.now += 61
    assert store.get(s.id) is None
    assert len(store) == 0


def test_purge_expired_only_removes_old():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    old = store.create()
    clock.now += 30
    fresh = store.create()
    clock.now += 31
    assert store.purge_expired() == 1
    assert store.get(old.id) is None
    assert store.get(fresh.id) is fresh


def test_add_document_appends_vectors():
    store = SessionStore(ttl_seconds=60)
    s = store.create()
    store.add_document(s, "a.pdf", [Chunk("a.pdf", "стр. 1", "x")], np.ones((1, 3), dtype=np.float32))
    store.add_document(s, "b.pdf", [Chunk("b.pdf", "стр. 1", "y")], np.zeros((1, 3), dtype=np.float32))
    assert s.files == ["a.pdf", "b.pdf"]
    assert [c.text for c in s.chunks] == ["x", "y"]
    assert s.vectors.shape == (2, 3)


def test_delete():
    store = SessionStore(ttl_seconds=60)
    s = store.create()
    store.delete(s.id)
    store.delete(s.id)  # повторное удаление не падает
    assert store.get(s.id) is None
