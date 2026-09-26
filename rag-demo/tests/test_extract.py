import pytest

from app.extract import ExtractError, NoTextLayer, UnsupportedFormat, extract
from tests.helpers import make_docx, make_pdf


def test_pdf_pages_numbered_and_blank_pages_skipped():
    units = extract("a.pdf", make_pdf(["Page one text", "", "Page three text"]))
    assert [(u.file, u.kind, u.num) for u in units] == [("a.pdf", "стр.", 1), ("a.pdf", "стр.", 3)]
    assert "Page three text" in units[1].text


def test_pdf_without_text_is_reported_as_scan():
    with pytest.raises(NoTextLayer, match="скан"):
        extract("scan.pdf", make_pdf(["", ""]))


def test_docx_cyrillic_paragraphs():
    units = extract("Регламент.docx", make_docx(["Отпуск 28 дней", "", "Рабочий день с 9 до 18"]))
    assert [(u.file, u.kind, u.num) for u in units] == [
        ("Регламент.docx", "абз.", 1),
        ("Регламент.docx", "абз.", 3),
    ]
    assert units[0].text == "Отпуск 28 дней"


def test_empty_docx_rejected():
    with pytest.raises(NoTextLayer):
        extract("empty.docx", make_docx(["", "  "]))


def test_unsupported_format():
    with pytest.raises(UnsupportedFormat, match="Поддерживаются PDF и DOCX."):
        extract("notes.txt", b"hello")


def test_extension_case_insensitive():
    assert extract("A.PDF", make_pdf(["Hi"]))[0].kind == "стр."


@pytest.mark.parametrize("name", ["broken.pdf", "broken.docx"])
def test_corrupted_file(name):
    with pytest.raises(ExtractError, match="Не удалось прочитать"):
        extract(name, b"definitely not a document")
