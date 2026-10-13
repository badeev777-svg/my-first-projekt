from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

PriceStatus = Literal["approved", "unapproved", "conflict", "none", "unknown"]

PERIODS = {"one_time", "monthly"}
STATUS_TEXT = {
    "live": "работает",
    "in_dev": "в разработке",
    "paused": "на паузе",
    "unknown": "статус уточняется",
}
PUBLIC = {"yes", "no", "description_only"}


class CatalogError(Exception):
    pass


@dataclass(frozen=True)
class Fact:
    id: str
    text: str


@dataclass(frozen=True)
class Service:
    id: str
    title: str
    description: str
    includes: tuple[str, ...]
    price_from: int | None
    price_to: int | None
    currency: str
    period: str
    duration_note: str
    approved: bool
    source: str


@dataclass(frozen=True)
class Project:
    id: str
    title: str
    description: str
    status: str
    url: str
    public: str
    verified: bool


@dataclass(frozen=True)
class FaqItem:
    q: str
    a: str
    approved: bool


@dataclass(frozen=True)
class Policy:
    tone: str
    recipient: str
    consent_text: str
    consent_approved: bool
    data_rules: tuple[str, ...]


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise CatalogError(f"{path.name}: не удалось прочитать ({e})") from e


def _require(item: dict, keys: list[str], file: str) -> None:
    for key in keys:
        if key not in item:
            raise CatalogError(f"{file}: у записи {item.get('id', item.get('q', '?'))} нет поля {key}")


def _money(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _format_price(s: Service) -> str:
    unit = "₽" if s.currency == "RUB" else s.currency
    suffix = "/мес" if s.period == "monthly" else ""
    if s.price_from is not None and s.price_to is not None and s.price_from != s.price_to:
        return f"от {_money(s.price_from)} до {_money(s.price_to)} {unit}{suffix}"
    if s.price_from is not None and s.price_from == s.price_to:
        return f"{_money(s.price_from)} {unit}{suffix}"
    if s.price_from is not None:
        return f"от {_money(s.price_from)} {unit}{suffix}"
    return f"до {_money(s.price_to)} {unit}{suffix}"  # type: ignore[arg-type]


class Catalog:
    def __init__(self, version: str, role: str, services: list[Service], projects: list[Project],
                 faq: list[FaqItem], policy: Policy):
        self.version = version
        self.role = role
        self.policy = policy
        self._projects = projects
        self._faq = faq
        self._by_id: dict[str, list[Service]] = {}
        for s in services:
            self._by_id.setdefault(s.id, []).append(s)

    @property
    def service_ids(self) -> list[str]:
        return list(self._by_id)

    def title(self, service_id: str) -> str:
        return self._by_id[service_id][0].title

    def price_status(self, service_id: str) -> PriceStatus:
        items = self._by_id.get(service_id)
        if not items:
            return "unknown"
        if len({(s.price_from, s.price_to, s.period) for s in items}) > 1:
            return "conflict"
        first = items[0]
        if first.price_from is None and first.price_to is None:
            return "none"
        return "approved" if all(s.approved for s in items) else "unapproved"

    def price_text(self, service_id: str) -> str | None:
        if self.price_status(service_id) != "approved":
            return None
        return _format_price(self._by_id[service_id][0])

    def facts(self) -> list[Fact]:
        facts: list[Fact] = []
        for sid, items in self._by_id.items():
            s = items[0]
            text = f"Услуга «{s.title}»: {s.description}."
            if s.includes:
                text += " Входит: " + ", ".join(s.includes) + "."
            if s.approved and s.duration_note:
                text += f" Сроки: {s.duration_note}."
            facts.append(Fact(f"service:{sid}", text))
            price = self.price_text(sid)
            if price:
                facts.append(Fact(f"price:{sid}", f"Цена «{s.title}»: {price}."))
            else:
                facts.append(Fact(f"price:{sid}", f"Цена «{s.title}»: не утверждена — уточнит {self.policy.recipient}."))
        for p in self._projects:
            if p.public == "no":
                continue
            text = f"Проект «{p.title}» — {STATUS_TEXT[p.status]}"
            if p.verified and p.description:
                text += f": {p.description}"
            if p.public == "yes" and p.url:
                text += f" ({p.url})"
            facts.append(Fact(f"project:{p.id}", text + "."))
        for n, item in enumerate(self._faq, start=1):
            if item.approved:
                facts.append(Fact(f"faq:{n}", f"Вопрос: {item.q} Ответ: {item.a}"))
        return facts


def _load_services(path: Path) -> list[Service]:
    out: list[Service] = []
    for item in _read_yaml(path) or []:
        _require(item, ["id", "title", "description", "price_from", "price_to", "currency", "period", "approved"],
                 "services.yaml")
        if item["period"] not in PERIODS:
            raise CatalogError(f"services.yaml: {item['id']}: period должен быть one_time или monthly")
        out.append(Service(
            id=str(item["id"]), title=str(item["title"]), description=str(item["description"]),
            includes=tuple(str(x) for x in item.get("includes") or []),
            price_from=item["price_from"], price_to=item["price_to"], currency=str(item["currency"]),
            period=item["period"], duration_note=str(item.get("duration_note") or ""),
            approved=bool(item["approved"]), source=str(item.get("source") or ""),
        ))
    return out


def _load_projects(path: Path) -> list[Project]:
    out: list[Project] = []
    for item in _read_yaml(path) or []:
        _require(item, ["id", "title", "status", "public", "verified"], "projects.yaml")
        if item["status"] not in STATUS_TEXT:
            raise CatalogError(f"projects.yaml: {item['id']}: status должен быть одним из {sorted(STATUS_TEXT)}")
        if item["public"] not in PUBLIC:
            raise CatalogError(f"projects.yaml: {item['id']}: public должен быть yes, no или description_only")
        out.append(Project(
            id=str(item["id"]), title=str(item["title"]), description=str(item.get("description") or ""),
            status=item["status"], url=str(item.get("url") or ""), public=item["public"],
            verified=bool(item["verified"]),
        ))
    return out


def _load_faq(path: Path) -> list[FaqItem]:
    out: list[FaqItem] = []
    for item in _read_yaml(path) or []:
        _require(item, ["q", "a", "approved"], "faq.yaml")
        out.append(FaqItem(q=str(item["q"]), a=str(item["a"]), approved=bool(item["approved"])))
    return out


def _load_policy(path: Path) -> Policy:
    item = _read_yaml(path) or {}
    _require(item, ["tone", "recipient", "consent_text", "consent_approved"], "policy.yaml")
    return Policy(
        tone=str(item["tone"]), recipient=str(item["recipient"]), consent_text=str(item["consent_text"]),
        consent_approved=bool(item["consent_approved"]),
        data_rules=tuple(str(x) for x in item.get("data_rules") or []),
    )


def load_catalog(content_dir: Path) -> Catalog:
    return Catalog(
        version=(content_dir / "VERSION").read_text(encoding="utf-8").strip(),
        role=(content_dir / "role.md").read_text(encoding="utf-8"),
        services=_load_services(content_dir / "services.yaml"),
        projects=_load_projects(content_dir / "projects.yaml"),
        faq=_load_faq(content_dir / "faq.yaml"),
        policy=_load_policy(content_dir / "policy.yaml"),
    )
