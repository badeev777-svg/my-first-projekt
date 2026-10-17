import json
import re
from pathlib import Path

import yaml

DEFAULT_POLICY = {
    "tone": "Обращайтесь на «вы», коротко.",
    "recipient": "Александр",
    "consent_text": "Оставьте телефон или e-mail — передадим нашему менеджеру для ответа по вашей задаче.",
    "consent_approved": True,
    "data_rules": [],
}


def service(id: str = "ai-agent", **overrides) -> dict:
    base = {
        "id": id,
        "title": "AI-агент под заказ",
        "description": "Агент под задачу клиента",
        "includes": [],
        "price_from": 50000,
        "price_to": 200000,
        "currency": "RUB",
        "period": "one_time",
        "duration_note": "",
        "approved": True,
        "source": "test",
    }
    base.update(overrides)
    return base


def _dump(path: Path, data) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def make_content(
    root: Path,
    services: list[dict],
    projects: list[dict] | None = None,
    faq: list[dict] | None = None,
    policy: dict | None = None,
    role: str = "Ты — AI-помощник по продажам проекта Test.",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _dump(root / "services.yaml", services)
    _dump(root / "projects.yaml", projects or [])
    _dump(root / "faq.yaml", faq or [])
    _dump(root / "policy.yaml", policy or DEFAULT_POLICY)
    (root / "role.md").write_text(role, encoding="utf-8")
    (root / "VERSION").write_text("test\n", encoding="utf-8")
    return root


def contract(reply: str, next_state: str = "discovery", action: str = "none", review: str = "ok",
             facts: list[str] | None = None) -> str:
    return json.dumps({"reply": reply, "facts_used": facts or [], "missing_fields": [], "next_state": next_state,
                       "proposed_action": action, "review_status": review}, ensure_ascii=False)


class Script:
    """Тестовая модель: различает классификатор, контроль качества и навык по маркерам в системном промпте.

    replies — очередь ответов навыка; последний повторяется. Элемент-исключение бросается.
    fail — если задано, бросается на любом вызове.
    """

    def __init__(self, intent: str = "need", service_id: str | None = None, replies: list | None = None,
                 verdict: str = "pass", fail: Exception | None = None):
        self.intent = intent
        self.service_id = service_id
        self.replies = list(replies or [contract("Расскажите, пожалуйста, о задаче.")])
        self.verdict = verdict
        self.fail = fail
        self.skills: list[str] = []

    def __call__(self, system: str, user: str) -> str:
        if self.fail is not None:
            raise self.fail
        if system.startswith("Ты — классификатор намерений"):
            return json.dumps({"intent": self.intent, "service_id": self.service_id})
        if "name: sales-quality-check" in system:
            return json.dumps({"verdict": self.verdict})
        m = re.search(r"^name: (sales-[a-z-]+)$", system, re.M)
        self.skills.append(m.group(1) if m else "?")
        item = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(item, Exception):
            raise item
        return item
