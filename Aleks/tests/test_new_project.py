# tests/test_new_project.py
from app.new_project import slugify


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
