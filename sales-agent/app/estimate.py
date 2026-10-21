"""Ориентир цены по формуле калькулятора AI-проектов: часы × ставка, вилка в пределах прайса услуги.

Параметры проекта из диалога извлекает модель, считает и пишет текст только код: так цифры ориентира
не проходят через модель и валидатор чисел им не нужен.
"""
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.llm_client import LLM
from app.skills import build_user, extract_json

NOTE = "Не оферта, точную цену назовёт {recipient}."
OVER_NOTE = "По описанию задача объёмнее прайса — точную цену назовёт {recipient}."
MARKER = "Ориентир"


@dataclass(frozen=True)
class Option:
    value: float
    label: str


@dataclass(frozen=True)
class Params:
    scope: str
    stage: str
    modules: tuple[str, ...] = ()
    integrations: int = 0
    data: str = "ready"
    risk: str = "low"


@dataclass(frozen=True)
class Estimate:
    low: int
    high: int
    hours: int
    over_price: bool
    parts: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class Estimator:
    rate: int
    reserve_percent: float
    one_time: int
    services: frozenset[str]
    scope: dict[str, Option]
    stage: dict[str, Option]
    modules: dict[str, Option]
    integration_hours: float
    max_integrations: int
    data: dict[str, Option]
    risk: dict[str, Option]
    defaults: dict[str, str]

    def hours(self, p: Params) -> int:
        raw = (self.scope[p.scope].value + sum(self.modules[m].value for m in p.modules)
               + p.integrations * self.integration_hours + self.data[p.data].value + self.risk[p.risk].value)
        # round() убирает хвост float: 88 × 1.0 не должно стать 89 часами.
        return math.ceil(round(raw * self.stage[p.stage].value, 6))

    def estimate(self, p: Params, price_from: int | None, price_to: int | None) -> Estimate:
        hours = self.hours(p)
        total = hours * self.rate * (1 + self.reserve_percent / 100) + self.one_time
        if p.data == "raw" or p.risk == "critical":
            spread = 0.3
        elif p.data == "partial" or p.risk == "sensitive":
            spread = 0.22
        else:
            spread = 0.15
        low, high = _round1000(total * (1 - spread / 2)), _round1000(total * (1 + spread))
        over = price_to is not None and high > price_to
        # Решение владельца 2026-10-21: ориентир не выходит за утверждённый прайс.
        lo_cap, hi_cap = price_from or 0, price_to if price_to is not None else math.inf
        low, high = min(max(low, lo_cap), hi_cap), min(max(high, lo_cap), hi_cap)
        return Estimate(int(low), int(high), hours, over, self.parts(p))

    def parts(self, p: Params) -> tuple[str, ...]:
        out = [self.scope[p.scope].label, *(self.modules[m].label for m in p.modules)]
        if p.integrations:
            out.append(f"интеграций: {p.integrations}")
        out += [self.data[p.data].label, self.risk[p.risk].label, self.stage[p.stage].label]
        return tuple(x for x in out if x)


def _round1000(x: float) -> int:
    return int(round(x / 1000) * 1000)


def _money(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def render(e: Estimate, recipient: str) -> str:
    amount = f"{_money(e.low)} ₽" if e.low == e.high else f"{_money(e.low)} – {_money(e.high)} ₽"
    text = f"{MARKER} {amount}"
    if e.parts:
        text += ": " + ", ".join(e.parts)
    text += ". " + (OVER_NOTE if e.over_price else NOTE).format(recipient=recipient)
    return text


def _options(data: Any, key: str, value_key: str) -> dict[str, Option]:
    if not isinstance(data, dict) or not data:
        raise ValueError(f"estimator.yaml: {key} должен быть словарём вариантов")
    out: dict[str, Option] = {}
    for name, item in data.items():
        if not isinstance(item, dict) or not isinstance(item.get(value_key), (int, float)) \
                or isinstance(item.get(value_key), bool):
            raise ValueError(f"estimator.yaml: {key}.{name}: нужно число {value_key}")
        out[str(name)] = Option(float(item[value_key]), str(item.get("label") or ""))
    return out


def _number(data: dict, key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"estimator.yaml: {key} должно быть неотрицательным числом")
    return value


def load_estimator(path: Path) -> Estimator | None:
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("estimator.yaml: ожидается словарь настроек")
    est = Estimator(
        rate=int(_number(data, "rate")),
        reserve_percent=_number(data, "reserve_percent"),
        one_time=int(_number(data, "one_time")),
        services=frozenset(str(s) for s in data.get("services") or []),
        scope=_options(data.get("scope"), "scope", "hours"),
        stage=_options(data.get("stage"), "stage", "factor"),
        modules=_options(data.get("modules"), "modules", "hours"),
        integration_hours=_number(data, "integration_hours"),
        max_integrations=int(_number(data, "max_integrations")),
        data=_options(data.get("data"), "data", "hours"),
        risk=_options(data.get("risk"), "risk", "hours"),
        defaults={str(k): str(v) for k, v in (data.get("defaults") or {}).items()},
    )
    for key in ("stage", "data", "risk"):
        if est.defaults.get(key) not in getattr(est, key):
            raise ValueError(f"estimator.yaml: defaults.{key} должен быть одним из {sorted(getattr(est, key))}")
    return est


EXTRACT_SYSTEM = """Ты — оценщик параметров ИИ-проекта по диалогу продаж. Определи по словам клиента (history и client_message), что ему нужно. Не додумывай: чего клиент не говорил — null.
- scope: для кого решение — {scope} (personal — для себя, team — для сотрудников, client — для клиентов компании, product — продукт на продажу)
- stage: {stage} (demo — проверить идею, pilot — рабочая первая версия, launch — полноценный запуск с нагрузкой)
- modules: список из {modules} (knowledge — ответы по базе знаний, interface — свой интерфейс/кабинет, documents — разбор документов, actions — действия во внешних системах: CRM, запись, оплата, analytics — отчёты и аналитика, access — роли и доступы)
- integrations: сколько внешних систем и мессенджеров подключить (число от 0 до {max_integrations})
- data: {data} (ready — материалы готовы, partial — частично, raw — собирать с нуля)
- risk: {risk} (low — без личных данных, sensitive — личные данные клиентов, critical — деньги, медицина, юридически значимое)
Ответь ТОЛЬКО JSON: {{"scope": ..., "stage": ..., "modules": [...], "integrations": ..., "data": ..., "risk": ...}}"""


def extract_params(llm: LLM, est: Estimator, text: str, history: list[tuple[str, str]]) -> Params | None:
    """Без масштаба задачи ориентир не считаем: тогда клиент видит обычный прайс."""
    system = EXTRACT_SYSTEM.format(
        scope=" | ".join(est.scope), stage=" | ".join(est.stage), modules=", ".join(est.modules),
        max_integrations=est.max_integrations, data=" | ".join(est.data), risk=" | ".join(est.risk))
    data = extract_json(llm.chat(system, build_user(history[-8:], text))) or {}
    scope = data.get("scope")
    if scope not in est.scope:
        return None

    def pick(key: str, options: dict[str, Option]) -> str:
        value = data.get(key)
        return value if isinstance(value, str) and value in options else est.defaults[key]

    raw_modules = data.get("modules")
    modules = tuple(dict.fromkeys(m for m in raw_modules if isinstance(m, str) and m in est.modules)) \
        if isinstance(raw_modules, list) else ()
    n = data.get("integrations")
    integrations = min(max(n, 0), est.max_integrations) if isinstance(n, int) and not isinstance(n, bool) else 0
    return Params(scope=scope, stage=pick("stage", est.stage), modules=modules, integrations=integrations,
                  data=pick("data", est.data), risk=pick("risk", est.risk))
