# app/new_project.py
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")

SLUG_MAX_LENGTH = 40


def slugify(text: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    lowered = text.strip().lower()
    transliterated = "".join(_TRANSLIT.get(ch, ch) for ch in lowered)
    slug = _NON_SLUG_CHARS.sub("-", transliterated).strip("-")
    return slug[:max_length].strip("-")


_TRIGGER_RE = re.compile(
    r"^(?:делаем|создай|создать|начн[её]м)?\s*новый проект[:\s]*(.*)$",
    re.IGNORECASE | re.DOTALL,
)


def parse_new_project_trigger(text: str) -> str | None:
    match = _TRIGGER_RE.match(text.strip())
    if match is None:
        return None
    return match.group(1).strip()
