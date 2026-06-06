import re
from app.settings_store import load_settings


def is_profile_or_resume(text: str) -> bool:
    lower = text.lower()
    profile_keywords = [
        "мой профиль", "портфолио", "опыт работы", "мои услуги",
        "фрилансер", "специалист", "резюме", "я разработчик",
        "я дизайнер", "я маркетолог", "я верстальщик", "я программист",
    ]
    return any(kw in lower for kw in profile_keywords)


def matches_keywords(text: str) -> bool:
    settings = load_settings()
    keywords = [k.lower() for k in settings.get("keywords", [])]
    stack = [s.lower() for s in settings.get("stack", [])]
    combined = keywords + stack

    if not combined:
        return True
    lower = text.lower()
    return any(kw in lower for kw in combined)


_BUDGET_RE = re.compile(r"(\d[\d\s]*)\s*(тыс|к\b|руб|₽|rub)", re.IGNORECASE)


def extract_budget(text: str) -> int | None:
    for m in _BUDGET_RE.finditer(text):
        digits = re.sub(r"\s", "", m.group(1))
        try:
            amount = int(digits)
            if "тыс" in m.group(2).lower() or "к" in m.group(2).lower():
                amount *= 1000
            return amount
        except ValueError:
            continue
    return None


def passes_budget(budget: int | None) -> bool:
    settings = load_settings()
    min_b = settings.get("min_budget", 0)
    max_b = settings.get("max_budget", 0)

    if min_b == 0 and max_b == 0:
        return True
    if budget is None:
        return True  # don't discard leads without explicit budget
    if min_b > 0 and budget < min_b:
        return False
    if max_b > 0 and budget > max_b:
        return False
    return True
