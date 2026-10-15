import re
from dataclasses import dataclass
from itertools import groupby

from app.extract import Unit


@dataclass(frozen=True)
class Chunk:
    file: str
    loc: str
    text: str


def chunk_units(units: list[Unit], size: int = 800, overlap: int = 150) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("overlap must be in [0, size)")
    chunks: list[Chunk] = []
    # Фрагмент не пересекает границу файла — иначе ссылка на источник будет неверной.
    for _, group in groupby(units, key=lambda x: x.file):
        chunks.extend(_chunk_file(list(group), size, overlap))
    return chunks


def _loc(kind: str, first: int, last: int) -> str:
    return f"{kind} {first}" if first == last else f"{kind} {first}–{last}"


_SPACE = re.compile(r"\s+")
_SENTENCE_GAP = re.compile(r"(?<=[.!?…])\s+")


def _windows(text: str, size: int, overlap: int) -> list[str]:
    # Режем по границам слов: цитата источника показывается пользователю и не должна начинаться с обрубка слова.
    out: list[str] = []
    start = 0
    while len(text) - start > size:
        gaps = [m for m in _SPACE.finditer(text, start, start + size + 1) if m.start() > start]
        end = gaps[-1].start() if gaps else start + size  # слово длиннее size режем как есть
        out.append(text[start:end])
        lo = max(end - overlap, start + 1)
        nxt = _first_gap_end(_SENTENCE_GAP, text, lo, end) or _first_gap_end(_SPACE, text, lo, end)
        if nxt is None:  # в зоне перекрытия нет пробела: без перекрытия, но с целого слова
            nxt = gaps[-1].end() if gaps else max(end - overlap, start + 1)
        start = nxt
    out.append(text[start:])
    return out


def _first_gap_end(pattern: re.Pattern[str], text: str, lo: int, hi: int) -> int | None:
    m = pattern.search(text, lo, hi)
    return m.end() if m else None


def _chunk_file(units: list[Unit], size: int, overlap: int) -> list[Chunk]:
    out: list[Chunk] = []
    buf: list[Unit] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            out.append(
                Chunk(buf[0].file, _loc(buf[0].kind, buf[0].num, buf[-1].num), "\n".join(x.text for x in buf))
            )
            buf, buf_len = [], 0

    for unit in units:
        if len(unit.text) > size:
            flush()
            out.extend(
                Chunk(unit.file, _loc(unit.kind, unit.num, unit.num), piece)
                for piece in _windows(unit.text, size, overlap)
            )
            continue
        extra = len(unit.text) + (1 if buf else 0)
        if buf and buf_len + extra > size:
            flush()
            extra = len(unit.text)
        buf.append(unit)
        buf_len += extra
    flush()
    return out
