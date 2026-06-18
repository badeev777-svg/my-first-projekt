import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "sessions.db"


async def init() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                ip          TEXT DEFAULT '',
                started_at  TEXT NOT NULL,
                finished_at TEXT,
                finished    INTEGER DEFAULT 0,
                msg_count   INTEGER DEFAULT 0,
                report_text TEXT,
                utm_source  TEXT DEFAULT '',
                utm_medium  TEXT DEFAULT '',
                utm_campaign TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages (session_id);
            CREATE TABLE IF NOT EXISTS leads (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL UNIQUE,
                business_name   TEXT,
                niche           TEXT,
                pain_points     TEXT,
                status          TEXT DEFAULT 'new',
                notes           TEXT,
                utm_source      TEXT,
                utm_medium      TEXT,
                utm_campaign    TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()
    await _migrate()


async def _migrate() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for col, definition in [
            ("report_text", "TEXT"),
            ("utm_source", "TEXT DEFAULT ''"),
            ("utm_medium", "TEXT DEFAULT ''"),
            ("utm_campaign", "TEXT DEFAULT ''"),
        ]:
            try:
                await db.execute(f"ALTER TABLE sessions ADD COLUMN {col} {definition}")
                await db.commit()
            except Exception:
                pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(
    session_id: str,
    ip: str = "",
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO sessions
               (session_id, ip, started_at, utm_source, utm_medium, utm_campaign)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, ip, _now(), utm_source or "", utm_medium or "", utm_campaign or ""),
        )
        await db.commit()


async def finish_session(
    session_id: str, msg_count: int, report_text: str | None
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE sessions
               SET finished=1, finished_at=?, msg_count=?, report_text=?
               WHERE session_id=?""",
            (_now(), msg_count, report_text, session_id),
        )
        await db.commit()


async def update_msg_count(session_id: str, msg_count: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET msg_count=? WHERE session_id=?",
            (msg_count, session_id),
        )
        await db.commit()


async def log_message(session_id: str, role: str, content: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, _now()),
        )
        await db.commit()


async def get_session_utm(session_id: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT utm_source, utm_medium, utm_campaign FROM sessions WHERE session_id=?",
            (session_id,),
        )).fetchone()
        if row:
            return {
                "utm_source": row["utm_source"] or "",
                "utm_medium": row["utm_medium"] or "",
                "utm_campaign": row["utm_campaign"] or "",
            }
        return {"utm_source": "", "utm_medium": "", "utm_campaign": ""}


async def save_lead(
    session_id: str,
    business_name: str = "",
    niche: str = "",
    pain_points: str = "",
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT OR IGNORE INTO leads
               (session_id, business_name, niche, pain_points,
                utm_source, utm_medium, utm_campaign)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, business_name, niche, pain_points,
             utm_source, utm_medium, utm_campaign),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def update_lead_status(lead_id: int, status: str, notes: str | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if notes is not None:
            await db.execute(
                "UPDATE leads SET status=?, notes=? WHERE id=?",
                (status, notes, lead_id),
            )
        else:
            await db.execute("UPDATE leads SET status=? WHERE id=?", (status, lead_id))
        await db.commit()


async def get_all_leads() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """SELECT id, session_id, business_name, niche, pain_points,
                      status, utm_source, utm_medium, utm_campaign, created_at
               FROM leads
               ORDER BY created_at DESC"""
        )).fetchall()
        return [dict(r) for r in rows]


async def get_lead_by_id(lead_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM leads WHERE id=?", (lead_id,)
        )).fetchone()
        return dict(row) if row else None


async def get_messages_by_session(session_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        )).fetchall()
        return [dict(r) for r in rows]


async def get_report_text(session_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT report_text FROM sessions WHERE session_id=?",
            (session_id,),
        )).fetchone()
        return row["report_text"] if row else None


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        row = await (await db.execute("SELECT COUNT(*) as total FROM sessions")).fetchone()
        total = row["total"]

        row = await (await db.execute(
            "SELECT COUNT(*) as n FROM sessions WHERE finished=1"
        )).fetchone()
        finished = row["n"]

        rows = await (await db.execute(
            """SELECT date(started_at) as day, COUNT(*) as n
               FROM sessions
               GROUP BY day
               ORDER BY day DESC
               LIMIT 30"""
        )).fetchall()
        by_day = [{"day": r["day"], "sessions": r["n"]} for r in rows]

        row = await (await db.execute(
            "SELECT AVG(msg_count) as avg FROM sessions WHERE finished=1"
        )).fetchone()
        avg_msgs = round(row["avg"] or 0, 1)

    return {
        "total_sessions": total,
        "finished_sessions": finished,
        "completion_rate": round(finished / total * 100, 1) if total else 0,
        "avg_messages_finished": avg_msgs,
        "by_day": by_day,
    }
