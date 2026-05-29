import re
from app.config import KEYWORDS, MIN_BUDGET


def is_profile_or_resume(text: str) -> bool:
    """Detect if text is a freelancer profile/resume instead of a job order."""
    lower = text.lower()
    profile_keywords = [
        "мой профиль",
        "портфолио",
        "опыт работы",
        "мои услуги",
        "фрилансер",
        "специалист",
        "резюме",
        "я разработчик",
        "я дизайнер",
        "я маркетолог",
        "я верстальщик",
        "я программист",
    ]
    return any(kw in lower for kw in profile_keywords)


def matches_keywords(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


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
    if MIN_BUDGET == 0:
        return True
    if budget is None:
        return True  # не отбрасываем заявки без явного бюджета
    return budget >= MIN_BUDGET
