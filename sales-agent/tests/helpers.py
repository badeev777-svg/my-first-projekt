from pathlib import Path

import yaml

DEFAULT_POLICY = {
    "tone": "Обращайтесь на «вы», коротко.",
    "recipient": "Александр",
    "consent_text": "Оставьте телефон или e-mail — передадим только Александру для ответа по вашей задаче.",
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
