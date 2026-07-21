# tests/test_state.py
import pytest

from app.state import StateStore


@pytest.mark.asyncio
async def test_active_project_roundtrip(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()

    assert await store.get_active_project(user_id=1) is None

    await store.set_active_project(user_id=1, project="aleks")
    assert await store.get_active_project(user_id=1) == "aleks"

    await store.set_active_project(user_id=1, project="lead-parser")
    assert await store.get_active_project(user_id=1) == "lead-parser"


@pytest.mark.asyncio
async def test_session_id_roundtrip(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()

    assert await store.get_session_id("aleks") is None

    await store.set_session_id("aleks", "session-a")
    assert await store.get_session_id("aleks") == "session-a"

    await store.set_session_id("aleks", "session-b")
    assert await store.get_session_id("aleks") == "session-b"
