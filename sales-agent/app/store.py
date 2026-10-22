import json
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.state import State

# Худший ход: до 5 вызовов модели (классификатор, навык, проверка качества, повтор навыка, повторная проверка),
# каждый — 2 попытки по 20 с + 1 с паузы: 5 × (2×20 + 1) = 205 с. Живой запрос не должен быть перехвачен повтором.
CLAIM_TTL_SECONDS = 240

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations(
    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, state TEXT NOT NULL,
    stopped INTEGER NOT NULL DEFAULT 0, product_id TEXT, created_at TEXT NOT NULL,
    epoch INTEGER NOT NULL DEFAULT 0, owner_at REAL);
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL, client_message_id TEXT,
    role TEXT NOT NULL, text TEXT NOT NULL, skill TEXT, created_at TEXT NOT NULL, claimed_at REAL,
    UNIQUE(conversation_id, client_message_id));
CREATE TABLE IF NOT EXISTS responses(
    conversation_id TEXT NOT NULL, client_message_id TEXT NOT NULL, body TEXT NOT NULL,
    PRIMARY KEY(conversation_id, client_message_id));
CREATE TABLE IF NOT EXISTS leads(
    id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE, contact_masked TEXT NOT NULL, contact TEXT NOT NULL,
    consent_status TEXT NOT NULL, consent_time TEXT, need TEXT NOT NULL, product_id TEXT NOT NULL,
    next_step TEXT NOT NULL, delivery_status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handoffs(
    id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE, reason TEXT NOT NULL, summary TEXT NOT NULL,
    question TEXT NOT NULL, delivery_status TEXT NOT NULL, created_at TEXT NOT NULL);
"""


class AlreadyProcessing(Exception):
    pass


@dataclass(frozen=True)
class Conversation:
    id: str
    session_id: str
    state: State
    stopped: bool
    product_id: str | None = None
    epoch: int = 0
    owner_at: float | None = None  # когда Александр последний раз писал клиенту в чате мессенджера


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _conv(row: sqlite3.Row) -> Conversation:
    return Conversation(row["id"], row["session_id"], State(row["state"]), bool(row["stopped"]), row["product_id"],
                        row["epoch"], row["owner_at"])


class Store:
    def __init__(self, path: str, clock: Callable[[], float] = time.time):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._clock = clock
        with self._conn() as c:
            c.executescript(SCHEMA)
            cols = {r["name"] for r in c.execute("PRAGMA table_info(conversations)")}
            if "epoch" not in cols:
                c.execute("ALTER TABLE conversations ADD COLUMN epoch INTEGER NOT NULL DEFAULT 0")
            if "owner_at" not in cols:
                c.execute("ALTER TABLE conversations ADD COLUMN owner_at REAL")

    def now(self) -> float:
        return self._clock()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def create_conversation(self, session_id: str) -> Conversation:
        cid = uuid.uuid4().hex
        with self._conn() as c:
            c.execute("INSERT INTO conversations(id, session_id, state, created_at) VALUES (?,?,?,?)",
                      (cid, session_id, State.NEW.value, _iso(self._clock())))
        return Conversation(cid, session_id, State.NEW, False)

    def get_conversation(self, cid: str) -> Conversation | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        return _conv(row) if row else None

    def latest_conversation(self, session_id: str) -> Conversation | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM conversations WHERE session_id=? ORDER BY rowid DESC LIMIT 1",
                            (session_id,)).fetchone()
        return _conv(row) if row else None

    def set_state(self, cid: str, state: State) -> None:
        with self._conn() as c:
            c.execute("UPDATE conversations SET state=? WHERE id=?", (state.value, cid))

    def mark_owner_reply(self, cid: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE conversations SET state=?, owner_at=? WHERE id=?",
                      (State.HUMAN_PENDING.value, self._clock(), cid))

    def bump_epoch(self, cid: str) -> None:
        # Новая эпоха = новые ключи идемпотентности заявок/передач после возврата диалога боту.
        with self._conn() as c:
            c.execute("UPDATE conversations SET epoch=epoch+1 WHERE id=?", (cid,))

    def set_stopped(self, cid: str, stopped: bool) -> None:
        with self._conn() as c:
            c.execute("UPDATE conversations SET stopped=? WHERE id=?", (int(stopped), cid))

    def set_product(self, cid: str, product_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE conversations SET product_id=? WHERE id=?", (product_id, cid))

    def conversations_in(self, state: State) -> list[Conversation]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM conversations WHERE state=? ORDER BY created_at", (state.value,)).fetchall()
        return [_conv(r) for r in rows]

    def claim_message(self, cid: str, client_message_id: str, text: str) -> dict | None:
        # Вставка с UNIQUE — это и есть захват: два одновременных запроса не обработают одно сообщение дважды.
        now = self._clock()
        with self._conn() as c:
            if self._insert_claim(c, cid, client_message_id, text, now):
                return None
            row = c.execute("SELECT body FROM responses WHERE conversation_id=? AND client_message_id=?",
                            (cid, client_message_id)).fetchone()
            if row:
                return json.loads(row["body"])
            # Захват умер до ответа (процесс упал): забираем его, только если он старше TTL.
            # Условный DELETE по claimed_at не даёт двум повторам захватить один и тот же устаревший захват.
            stale = c.execute("SELECT claimed_at FROM messages WHERE conversation_id=? AND client_message_id=? "
                              "AND role='user'", (cid, client_message_id)).fetchone()
            if stale is None or stale["claimed_at"] is None or now - stale["claimed_at"] <= CLAIM_TTL_SECONDS:
                raise AlreadyProcessing(client_message_id)
            taken = c.execute("DELETE FROM messages WHERE conversation_id=? AND client_message_id=? "
                              "AND role='user' AND claimed_at=?",
                              (cid, client_message_id, stale["claimed_at"])).rowcount
            if taken == 0 or not self._insert_claim(c, cid, client_message_id, text, now):
                raise AlreadyProcessing(client_message_id)
            return None

    def _insert_claim(self, c: sqlite3.Connection, cid: str, client_message_id: str, text: str,
                      now: float) -> bool:
        try:
            c.execute(
                "INSERT INTO messages(conversation_id, client_message_id, role, text, created_at, claimed_at) "
                "VALUES (?,?,?,?,?,?)",
                (cid, client_message_id, "user", text, _iso(now), now),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def saved_response(self, cid: str, client_message_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT body FROM responses WHERE conversation_id=? AND client_message_id=?",
                            (cid, client_message_id)).fetchone()
        return json.loads(row["body"]) if row else None

    def release_claim(self, cid: str, client_message_id: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM messages WHERE conversation_id=? AND client_message_id=? AND role='user'",
                      (cid, client_message_id))

    def save_response(self, cid: str, client_message_id: str, body: dict, reply: str | None, skill: str | None) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO responses(conversation_id, client_message_id, body) VALUES (?,?,?)",
                      (cid, client_message_id, json.dumps(body, ensure_ascii=False)))
            if reply:
                c.execute("INSERT INTO messages(conversation_id, role, text, skill, created_at) VALUES (?,?,?,?,?)",
                          (cid, "assistant", reply, skill, _iso(self._clock())))

    def history(self, cid: str, limit: int = 10) -> list[tuple[str, str]]:
        with self._conn() as c:
            rows = c.execute("SELECT role, text FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                             (cid, limit)).fetchall()
        return [(r["role"], r["text"]) for r in reversed(rows)]

    def _insert_once(self, table: str, fields: dict) -> tuple[int, bool]:
        fields = {**fields, "created_at": _iso(self._clock())}
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        with self._conn() as c:
            # Только конфликт по ключу идемпотентности гасится; NOT NULL и прочие нарушения должны подниматься.
            cur = c.execute(f"INSERT INTO {table}({cols}) VALUES ({marks}) "
                            "ON CONFLICT(idempotency_key) DO NOTHING", tuple(fields.values()))
            created = cur.rowcount == 1
            row = c.execute(f"SELECT id FROM {table} WHERE idempotency_key=?", (fields["idempotency_key"],)).fetchone()
        return row["id"], created

    def _get(self, table: str, row_id: int) -> dict:
        with self._conn() as c:
            return dict(c.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone())

    def _set_delivery(self, table: str, row_id: int, status: str) -> None:
        with self._conn() as c:
            c.execute(f"UPDATE {table} SET delivery_status=? WHERE id=?", (status, row_id))

    def _list(self, table: str) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()]

    def create_lead(self, *, conversation_id: str, idempotency_key: str, contact_masked: str, contact: str,
                    consent_status: str, consent_time: str | None, need: str, product_id: str, next_step: str,
                    delivery_status: str) -> tuple[int, bool]:
        return self._insert_once("leads", dict(
            conversation_id=conversation_id, idempotency_key=idempotency_key, contact_masked=contact_masked,
            contact=contact, consent_status=consent_status, consent_time=consent_time, need=need,
            product_id=product_id, next_step=next_step, delivery_status=delivery_status))

    def get_lead(self, lead_id: int) -> dict:
        return self._get("leads", lead_id)

    def set_lead_delivery(self, lead_id: int, status: str) -> None:
        self._set_delivery("leads", lead_id, status)

    def list_leads(self) -> list[dict]:
        return self._list("leads")

    def create_handoff(self, *, conversation_id: str, idempotency_key: str, reason: str, summary: str,
                       question: str, delivery_status: str) -> tuple[int, bool]:
        return self._insert_once("handoffs", dict(
            conversation_id=conversation_id, idempotency_key=idempotency_key, reason=reason, summary=summary,
            question=question, delivery_status=delivery_status))

    def get_handoff(self, handoff_id: int) -> dict:
        return self._get("handoffs", handoff_id)

    def set_handoff_delivery(self, handoff_id: int, status: str) -> None:
        self._set_delivery("handoffs", handoff_id, status)

    def list_handoffs(self) -> list[dict]:
        return self._list("handoffs")

    def purge_expired(self, *, plain_days: int, contact_days: int) -> int:
        # Сроки из политики конфиденциальности сайта: считаются от последнего сообщения диалога.
        # Передача человеку приравнена к заявке — в её сводке могут быть данные клиента.
        now = self._clock()
        plain_cut, contact_cut = _iso(now - plain_days * 86400), _iso(now - contact_days * 86400)
        with self._conn() as c:
            ids = [r["id"] for r in c.execute(
                "SELECT c.id, COALESCE((SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id=c.id),"
                " c.created_at) AS last_at,"
                " EXISTS(SELECT 1 FROM leads l WHERE l.conversation_id=c.id)"
                " OR EXISTS(SELECT 1 FROM handoffs h WHERE h.conversation_id=c.id) AS has_contact "
                "FROM conversations c").fetchall()
                if r["last_at"] < (contact_cut if r["has_contact"] else plain_cut)]
            for table, col in (("messages", "conversation_id"), ("responses", "conversation_id"),
                               ("leads", "conversation_id"), ("handoffs", "conversation_id"), ("conversations", "id")):
                c.executemany(f"DELETE FROM {table} WHERE {col}=?", [(i,) for i in ids])
        return len(ids)
