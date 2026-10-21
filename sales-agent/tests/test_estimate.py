from pathlib import Path

import pytest

from app.estimate import Params, extract_params, load_estimator, render
from app.llm_client import FakeLLM
from tests.helpers import Script, contract

ROOT = Path(__file__).resolve().parent.parent
EST = load_estimator(ROOT / "content" / "estimator.yaml")
TYPICAL = Params(scope="team", stage="pilot", modules=("knowledge",), integrations=2, data="partial", risk="sensitive")


def test_real_estimator_covers_only_ai_services():
    assert EST.rate == 1600
    assert EST.services == {"ai-consultant-gigachat", "ai-agent", "tg-bot", "rag-docs", "automation"}


def test_formula_matches_calculator():
    # 32 + 12 + 2×10 + 10 + 14 = 88 ч × 1600 = 140 800; разброс 0.22 → −11% / +22%, округление до тысяч.
    e = EST.estimate(TYPICAL, 50000, 200000)
    assert (e.hours, e.low, e.high, e.over_price) == (88, 125000, 172000, False)


def test_stage_factor_rounds_hours_up():
    assert EST.hours(Params(scope="personal", stage="demo")) == 13  # 18 × 0.7 = 12.6


def test_range_is_capped_by_price_list():
    e = EST.estimate(TYPICAL, 50000, 150000)
    assert (e.low, e.high, e.over_price) == (125000, 150000, True)


def test_small_task_shows_price_floor():
    e = EST.estimate(Params(scope="personal", stage="demo"), 50000, 200000)
    assert (e.low, e.high, e.over_price) == (50000, 50000, False)
    assert render(e, "Александр").startswith("Ориентир 50 000 ₽: для одного человека, демо.")


def test_huge_task_is_price_ceiling_with_note():
    p = Params(scope="product", stage="launch", modules=tuple(EST.modules), integrations=10, data="raw", risk="critical")
    text = render(EST.estimate(p, 70000, 200000), "Александр")
    assert text.startswith("Ориентир 200 000 ₽")
    assert "точную цену назовёт Александр" in text and "объёмнее прайса" in text


def test_render_lists_parts():
    text = render(EST.estimate(TYPICAL, 50000, 200000), "Александр")
    assert text == ("Ориентир 125 000 – 172 000 ₽: для команды, база знаний, интеграций: 2, данные нужно доработать, "
                    "работа с личными данными. Не оферта, точную цену назовёт Александр.")


def test_extract_without_scope_gives_nothing():
    assert extract_params(FakeLLM(Script(estimate={"scope": None, "modules": ["knowledge"]})), EST, "Сколько?", []) is None


def test_extract_cleans_model_output():
    script = Script(estimate={"scope": "client", "stage": "что-то", "modules": ["knowledge", "x", "knowledge"],
                              "integrations": 99, "data": None, "risk": "sensitive"})
    p = extract_params(FakeLLM(script), EST, "Бот для клиентов", [])
    assert p == Params(scope="client", stage="pilot", modules=("knowledge",), integrations=10, data="ready",
                       risk="sensitive")


def test_bool_is_not_integration_count():
    p = extract_params(FakeLLM(Script(estimate={"scope": "team", "integrations": True})), EST, "x", [])
    assert p.integrations == 0


def test_missing_file_disables_estimator(tmp_path):
    assert load_estimator(tmp_path / "estimator.yaml") is None


def test_bad_default_rejected(tmp_path):
    path = tmp_path / "estimator.yaml"
    path.write_text((ROOT / "content" / "estimator.yaml").read_text(encoding="utf-8")
                    .replace("defaults: {stage: pilot", "defaults: {stage: fast"), encoding="utf-8")
    with pytest.raises(ValueError, match="defaults.stage"):
        load_estimator(path)


TEAM_BOT = {"scope": "team", "stage": "pilot", "modules": ["knowledge"], "integrations": 2, "data": "partial",
            "risk": "sensitive"}


def test_chat_shows_estimate_instead_of_price_line(make_client):
    h = make_client(Script(intent="price", service_id="ai-agent", estimate=TEAM_BOT), estimator=True)
    body = h.say(h.start(), "Сколько будет стоить бот для сотрудников с базой знаний в Telegram и CRM?").json()
    assert "Ориентир 125 000 – 172 000 ₽: для команды" in body["reply"]
    assert "Цена «AI-агент под заказ»" not in body["reply"]


def test_chat_falls_back_to_price_without_scope(make_client):
    h = make_client(Script(intent="price", service_id="ai-agent", estimate={"scope": None}), estimator=True)
    body = h.say(h.start(), "Сколько стоит?").json()
    assert "Цена «AI-агент под заказ»: " in body["reply"] and "Ориентир" not in body["reply"]


def test_service_outside_estimator_keeps_price_line(make_client):
    from tests.helpers import service
    h = make_client(Script(intent="price", service_id="landing", estimate=TEAM_BOT),
                    services=[service(), service("landing", title="Лендинг")], estimator=True)
    body = h.say(h.start(), "Сколько стоит лендинг?").json()
    assert "Цена «Лендинг»: " in body["reply"] and "Ориентир" not in body["reply"]


def test_model_may_repeat_estimate_next_turn(make_client):
    script = Script(intent="price", service_id="ai-agent", estimate=TEAM_BOT,
                    replies=[contract("Посчитал."), contract("Да, ориентир 125 000 – 172 000 ₽.")])
    h = make_client(script, estimator=True)
    cid = h.start()
    h.say(cid, "Сколько будет стоить бот для сотрудников?")
    script.intent = "question"
    body = h.say(cid, "Повторите сумму?").json()
    assert body["fallback"] is False and "125 000 – 172 000" in body["reply"]


def test_unknown_service_in_estimator_fails_startup(make_client, tmp_path):
    from app.config import Settings
    from app.main import create_app
    from tests.helpers import make_content, service
    content = make_content(tmp_path / "c", [service()])
    (content / "estimator.yaml").write_text((ROOT / "content" / "estimator.yaml").read_text(encoding="utf-8"),
                                            encoding="utf-8")
    settings = Settings(_env_file=None, cloudru_api_key="", db_path=str(tmp_path / "s.db"),
                        content_dir=str(content), skills_dir=str(ROOT / "skills"))
    with pytest.raises(ValueError, match="таких услуг нет"):
        create_app(settings)
