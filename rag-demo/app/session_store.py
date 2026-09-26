import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from app.chunker import Chunk


@dataclass
class Session:
    id: str
    created_at: float
    files: list[str] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    vectors: np.ndarray | None = None
    questions: int = 0


class SessionStore:
    # Синхронные эндпоинты FastAPI выполняются в пуле потоков — нужен лок.
    def __init__(self, ttl_seconds: int, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def _expired(self, s: Session) -> bool:
        return self._clock() - s.created_at > self._ttl

    def create(self) -> Session:
        s = Session(id=secrets.token_urlsafe(32), created_at=self._clock())
        with self._lock:
            self._sessions[s.id] = s
        return s

    def get(self, sid: str) -> Session | None:
        with self._lock:
            s = self._sessions.get(sid)
            if s is not None and self._expired(s):
                del self._sessions[sid]
                return None
            return s

    def add_document(self, session: Session, filename: str, chunks: list[Chunk], vectors: np.ndarray) -> None:
        with self._lock:
            session.files.append(filename)
            session.chunks.extend(chunks)
            session.vectors = vectors if session.vectors is None else np.vstack([session.vectors, vectors])

    def delete(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)

    def purge_expired(self) -> int:
        with self._lock:
            dead = [sid for sid, s in self._sessions.items() if self._expired(s)]
            for sid in dead:
                del self._sessions[sid]
            return len(dead)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
