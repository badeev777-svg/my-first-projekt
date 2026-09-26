from dataclasses import dataclass
from io import BytesIO

import docx
from pypdf import PdfReader


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
        if reader.is_encrypted:
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
    units = [
        Unit(filename, "абз.", i, text)
        for i, p in enumerate(document.paragraphs, start=1)
        if (text := p.text.strip())
    ]
    if not units:
        raise NoTextLayer(f"В файле «{filename}» нет текста.")
    return units
