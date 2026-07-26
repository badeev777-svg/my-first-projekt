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


@pytest.mark.asyncio
async def test_add_and_list_dynamic_project(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()

    await store.add_dynamic_project("epoksidka", "/root/user-projects/epoksidka")

    merged = await store.list_all_projects({"aleks": "/root/projects/Aleks"})
    assert merged == {
        "aleks": "/root/projects/Aleks",
        "epoksidka": "/root/user-projects/epoksidka",
    }


@pytest.mark.asyncio
async def test_list_all_projects_static_wins_on_name_collision(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()
    await store.add_dynamic_project("aleks", "/root/user-projects/aleks")

    merged = await store.list_all_projects({"aleks": "/root/projects/Aleks"})

    assert merged["aleks"] == "/root/projects/Aleks"


@pytest.mark.asyncio
async def test_add_dynamic_project_duplicate_name_raises(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    await store.init()
    await store.add_dynamic_project("epoksidka", "/root/user-projects/epoksidka")

    with pytest.raises(Exception):
        await store.add_dynamic_project("epoksidka", "/root/user-projects/epoksidka-2")
