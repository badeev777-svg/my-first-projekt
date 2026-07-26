# tests/test_new_project.py
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
