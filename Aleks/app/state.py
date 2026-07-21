# app/state.py
import aiosqlite


class StateStore:
    """Persists the active project per Telegram user and the resumable
    Claude Agent SDK session_id per project, so context survives restarts."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS active_project ("
                "user_id INTEGER PRIMARY KEY, project TEXT NOT NULL)"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS project_session ("
                "project TEXT PRIMARY KEY, session_id TEXT NOT NULL)"
            )
            await db.commit()

    async def get_active_project(self, user_id: int) -> str | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT project FROM active_project WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_active_project(self, user_id: int, project: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO active_project (user_id, project) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET project = excluded.project",
                (user_id, project),
            )
            await db.commit()

    async def get_session_id(self, project: str) -> str | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT session_id FROM project_session WHERE project = ?", (project,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_session_id(self, project: str, session_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO project_session (project, session_id) VALUES (?, ?) "
                "ON CONFLICT(project) DO UPDATE SET session_id = excluded.session_id",
                (project, session_id),
            )
            await db.commit()
