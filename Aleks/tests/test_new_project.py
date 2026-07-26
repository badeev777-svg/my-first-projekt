# tests/test_new_project.py
import os
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.new_project import handle_new_project
from app.new_project import slugify
from app.new_project import parse_new_project_trigger


def test_slugify_transliterates_cyrillic() -> None:
    assert slugify("Эпоксидка Лендинг") == "epoksidka-lending"


def test_slugify_collapses_punctuation_and_spaces() -> None:
    assert slugify("  столы, табуретки!!  часы  ") == "stoly-taburetki-chasy"


def test_slugify_empty_input_returns_empty_string() -> None:
    assert slugify("   ") == ""
    assert slugify("!!!") == ""


def test_slugify_truncates_to_max_length() -> None:
    long_name = "а" * 100
    result = slugify(long_name)
    assert len(result) <= 40
    assert not result.endswith("-")


def test_slugify_keeps_latin_and_digits_as_is() -> None:
    assert slugify("Project 2") == "project-2"


def test_trigger_bare_phrase() -> None:
    assert parse_new_project_trigger("новый проект эпоксидка") == "эпоксидка"


def test_trigger_delaem_variant() -> None:
    assert parse_new_project_trigger("Делаем новый проект: столы из смолы") == "столы из смолы"


def test_trigger_sozdat_variant() -> None:
    assert parse_new_project_trigger("создать новый проект лендинг") == "лендинг"


def test_trigger_sozday_variant() -> None:
    assert parse_new_project_trigger("создай новый проект лендинг") == "лендинг"


def test_trigger_nachnem_variants() -> None:
    assert parse_new_project_trigger("начнём новый проект часы") == "часы"
    assert parse_new_project_trigger("начнем новый проект часы") == "часы"


def test_trigger_case_insensitive() -> None:
    assert parse_new_project_trigger("НОВЫЙ ПРОЕКТ Часы") == "Часы"


def test_trigger_no_match_returns_none() -> None:
    assert parse_new_project_trigger("почини баг в проекте") is None
    assert parse_new_project_trigger("хочу обсудить новый проект") is None
    assert parse_new_project_trigger("у меня новый проект уже есть") is None


def test_trigger_phrase_without_name_returns_empty_string() -> None:
    assert parse_new_project_trigger("новый проект") == ""


def test_trigger_rejects_inflected_word_after_proekt() -> None:
    assert parse_new_project_trigger("новый проекты появились") is None
    assert parse_new_project_trigger("новый проектах пусто") is None
    assert parse_new_project_trigger("Новый проектище") is None


def test_trigger_allows_irregular_whitespace() -> None:
    assert parse_new_project_trigger("новый  проект часы") == "часы"


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="k",
        projects={"aleks": "/root/projects/Aleks"},
        projects_root=str(tmp_path / "user-projects"),
        _env_file=None,
        **overrides,
    )


def _state(existing: dict[str, str] | None = None) -> AsyncMock:
    state = AsyncMock()
    state.list_all_projects.return_value = dict(existing or {})
    return state


@pytest.mark.asyncio
async def test_handle_new_project_creates_folder_and_activates(tmp_path) -> None:
    settings = _settings(tmp_path)
    state = _state()

    reply = await handle_new_project("Эпоксидка Лендинг", user_id=42, settings=settings, state=state)

    expected_path = os.path.join(settings.projects_root, "epoksidka-lending")
    assert os.path.isdir(expected_path)
    state.add_dynamic_project.assert_awaited_once_with("epoksidka-lending", expected_path)
    state.set_active_project.assert_awaited_once_with(42, "epoksidka-lending")
    assert "epoksidka-lending" in reply
    assert expected_path in reply


@pytest.mark.asyncio
async def test_handle_new_project_empty_name_replies_with_prompt(tmp_path) -> None:
    settings = _settings(tmp_path)
    state = _state()

    reply = await handle_new_project("   ", user_id=42, settings=settings, state=state)

    assert "название" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_new_project_static_name_collision_rejected(tmp_path) -> None:
    settings = _settings(tmp_path)
    state = _state()

    reply = await handle_new_project("aleks", user_id=42, settings=settings, state=state)

    assert "занято" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_new_project_existing_dynamic_switches_without_recreating(tmp_path) -> None:
    settings = _settings(tmp_path)
    existing_path = str(tmp_path / "user-projects" / "epoksidka")
    state = _state(existing={"epoksidka": existing_path})

    reply = await handle_new_project("эпоксидка", user_id=42, settings=settings, state=state)

    assert "уже существует" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_awaited_once_with(42, "epoksidka")


@pytest.mark.asyncio
async def test_handle_new_project_makedirs_failure_reports_error_and_registers_nothing(
    tmp_path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    state = _state()

    def boom(*args, **kwargs):
        raise OSError(13, "Permission denied", "/root/user-projects/chasy")

    monkeypatch.setattr("app.new_project.os.makedirs", boom)

    reply = await handle_new_project("часы", user_id=42, settings=settings, state=state)

    assert "не получилось" in reply.lower()
    state.add_dynamic_project.assert_not_awaited()
    state.set_active_project.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_new_project_makedirs_failure_does_not_leak_details_and_logs(
    tmp_path, monkeypatch, caplog
) -> None:
    settings = _settings(tmp_path)
    state = _state()

    def boom(*args, **kwargs):
        raise OSError(13, "Permission denied", "/root/user-projects/chasy")

    monkeypatch.setattr("app.new_project.os.makedirs", boom)

    with caplog.at_level("ERROR", logger="app.new_project"):
        reply = await handle_new_project("часы", user_id=42, settings=settings, state=state)

    assert "/root/user-projects/chasy" not in reply
    assert "Permission denied" not in reply
    assert "13" not in reply
    assert any(record.exc_info for record in caplog.records)
