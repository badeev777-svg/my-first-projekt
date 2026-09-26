from dataclasses import dataclass
from io import BytesIO

import docx
from pypdf import PasswordType, PdfReader


class ExtractError(Exception):
    """Сообщение показывается пользователю как есть."""


class UnsupportedFormat(ExtractError):
    pass


class NoTextLayer(ExtractError):
    pass


@dataclass(frozen=True)
class Unit:
    file: str
    kind: str  # "стр." для PDF, "абз." для DOCX — в DOCX нет страниц
    num: int
    text: str


def extract(filename: str, data: bytes) -> list[Unit]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return _pdf(filename, data)
    if ext == "docx":
        return _docx(filename, data)
    raise UnsupportedFormat("Поддерживаются PDF и DOCX.")


def _pdf(filename: str, data: bytes) -> list[Unit]:
    try:
        reader = PdfReader(BytesIO(data))
        # Пароль только на правку/печать открывается пустым паролем — такие PDF читаем.
        if reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED:
            raise ExtractError(f"Файл «{filename}» защищён паролем.")
        units = [
            Unit(filename, "стр.", i, text)
            for i, page in enumerate(reader.pages, start=1)
            if (text := (page.extract_text() or "").strip())
        ]
    except ExtractError:
        raise
    except Exception as e:
        raise ExtractError(f"Не удалось прочитать файл «{filename}».") from e
    if not units:
        raise NoTextLayer("Похоже, это скан. Распознавание сканов появится в следующей версии.")
    return units


def _docx(filename: str, data: bytes) -> list[Unit]:
    try:
        document = docx.Document(BytesIO(data))
    except Exception as e:
        raise ExtractError(f"Не удалось прочитать файл «{filename}».") from e
    texts = [p.text for p in document.paragraphs] + [
        _row_text(row) for table in document.tables for row in table.rows
    ]
    units = [Unit(filename, "абз.", i, text) for i, t in enumerate(texts, start=1) if (text := t.strip())]
    if not units:
        raise NoTextLayer(f"В файле «{filename}» нет текста.")
    return units


def _row_text(row) -> str:
    cells: list[str] = []
    for cell in row.cells:
        text = cell.text.strip()
        # Объединённые ячейки python-docx отдаёт повторно.
        if text and (not cells or cells[-1] != text):
            cells.append(text)
    return " | ".join(cells)
