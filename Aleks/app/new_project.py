# app/new_project.py
import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import StateStore

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
    r"^(?:(?:делаем|создай|создать|начн[её]м)\s+)?новый\s+проект\b[:\s]*(.*)$",
    re.IGNORECASE | re.DOTALL,
)


def parse_new_project_trigger(text: str) -> str | None:
    match = _TRIGGER_RE.match(text.strip())
    if match is None:
        return None
    return match.group(1).strip()


async def handle_new_project(
    raw_name: str, user_id: int, settings: "Settings", state: "StateStore"
) -> str:
    slug = slugify(raw_name)
    if not slug:
        return "Укажи название проекта в этом же сообщении: «новый проект <название>»"

    if slug in settings.projects:
        return f"Имя «{slug}» занято системным проектом, выбери другое"

    existing = await state.list_all_projects(settings.projects)
    if slug in existing:
        await state.set_active_project(user_id, slug)
        return f"Проект «{slug}» уже существует, переключился на него"

    project_path = os.path.join(settings.projects_root, slug)
    try:
        os.makedirs(settings.projects_root, exist_ok=True)
        os.makedirs(project_path, exist_ok=False)
    except OSError as exc:
        return f"Не получилось создать проект: {exc}"

    await state.add_dynamic_project(slug, project_path)
    await state.set_active_project(user_id, slug)
    return f"Новый проект «{slug}» создан: {project_path}\nАктивный проект переключён на него."
