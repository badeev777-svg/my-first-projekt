import re
from pathlib import Path

import pytest

from app.catalog import CatalogError, load_catalog
from tests.helpers import DEFAULT_POLICY, make_content, service

REAL_CONTENT = Path(__file__).resolve().parent.parent / "content"


def test_real_content_loads_and_hides_unapproved_prices():
    cat = load_catalog(REAL_CONTENT)
    assert "ai-agent" in cat.service_ids
    assert cat.price_status("ai-agent") == "unapproved"
    assert cat.price_text("ai-agent") is None
    joined = " ".join(f.text for f in cat.facts())
    assert "200 000" not in joined and "200000" not in joined
    assert "не утверждена" in joined
    assert cat.policy.recipient == "Александр"
    assert cat.version


def test_real_content_has_no_url_for_description_only_projects():
    cat = load_catalog(REAL_CONTENT)
    aleks = [f for f in cat.facts() if f.id == "project:aleks"]
    assert len(aleks) == 1
    assert "http" not in aleks[0].text


def test_approved_range_is_formatted(tmp_path):
    cat = load_catalog(make_content(tmp_path, [service()]))
    assert cat.price_status("ai-agent") == "approved"
    assert cat.price_text("ai-agent") == "от 50 000 до 200 000 ₽"
    assert any(f.id == "price:ai-agent" and "50 000" in f.text for f in cat.facts())


def test_monthly_exact_and_from_only(tmp_path):
    cat = load_catalog(
        make_content(
            tmp_path,
            [
                service("sub", price_from=2499, price_to=2499, period="monthly"),
                service("custom", price_from=80000, price_to=None),
            ],
        )
    )
    assert cat.price_text("sub") == "2 499 ₽/мес"
    assert cat.price_text("custom") == "от 80 000 ₽"


def test_duplicate_id_with_different_price_is_conflict(tmp_path):
    cat = load_catalog(make_content(tmp_path, [service(), service(price_from=70000)]))
    assert cat.price_status("ai-agent") == "conflict"
    assert cat.price_text("ai-agent") is None
    assert cat.service_ids == ["ai-agent"]


def test_no_price_and_unknown_id(tmp_path):
    cat = load_catalog(make_content(tmp_path, [service("rag", price_from=None, price_to=None)]))
    assert cat.price_status("rag") == "none"
    assert cat.price_status("missing") == "unknown"


def test_duration_note_only_when_approved(tmp_path):
    cat = load_catalog(
        make_content(
            tmp_path,
            [
                service("a", duration_note="от 2 недель"),
                service("b", duration_note="от 3 недель", approved=False),
            ],
        )
    )
    texts = {f.id: f.text for f in cat.facts()}
    assert "2 недель" in texts["service:a"]
    assert "3 недель" not in texts["service:b"]


def test_project_visibility_rules(tmp_path):
    projects = [
        {"id": "p1", "title": "Открытый", "description": "Описание один", "status": "live",
         "url": "https://p1.example", "public": "yes", "verified": True},
        {"id": "p2", "title": "Скрытый", "description": "x", "status": "live", "public": "no", "verified": True},
        {"id": "p3", "title": "Только описание", "description": "Умеет многое", "status": "live",
         "url": "https://secret.example", "public": "description_only", "verified": True},
        {"id": "p4", "title": "Непроверенный", "description": "Догадка", "status": "unknown",
         "public": "yes", "verified": False},
    ]
    cat = load_catalog(make_content(tmp_path, [service()], projects=projects))
    texts = {f.id: f.text for f in cat.facts()}
    assert "https://p1.example" in texts["project:p1"]
    assert "project:p2" not in texts
    assert "Умеет многое" in texts["project:p3"] and "secret.example" not in texts["project:p3"]
    assert "Догадка" not in texts["project:p4"] and "статус уточняется" in texts["project:p4"]


def test_unapproved_faq_is_not_a_fact(tmp_path):
    faq = [{"q": "Вопрос А?", "a": "Ответ А", "approved": True}, {"q": "Вопрос Б?", "a": "Ответ Б", "approved": False}]
    cat = load_catalog(make_content(tmp_path, [service()], faq=faq))
    joined = " ".join(f.text for f in cat.facts())
    assert "Ответ А" in joined and "Ответ Б" not in joined


def test_bad_service_names_file_and_id(tmp_path):
    bad = service()
    del bad["title"]
    with pytest.raises(CatalogError, match=r"services\.yaml.*ai-agent.*title"):
        load_catalog(make_content(tmp_path, [bad]))


def test_bad_project_status_rejected(tmp_path):
    projects = [{"id": "p", "title": "P", "description": "", "status": "soon", "public": "yes", "verified": False}]
    with pytest.raises(CatalogError, match="status"):
        load_catalog(make_content(tmp_path, [service()], projects=projects))


def test_facts_have_no_secret_like_values():
    cat = load_catalog(REAL_CONTENT)
    for f in cat.facts():
        assert not re.search(r"(?i)api[_-]?key|password|пароль|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", f.text)


@pytest.mark.parametrize("value", ["false", "no", 0, None])
def test_non_bool_approved_rejected(tmp_path, value):
    with pytest.raises(CatalogError, match=r"services\.yaml.*ai-agent.*approved"):
        load_catalog(make_content(tmp_path, [service(approved=value)]))


def test_non_bool_project_verified_rejected(tmp_path):
    projects = [{"id": "p", "title": "P", "description": "d", "status": "live", "public": "yes", "verified": "no"}]
    with pytest.raises(CatalogError, match=r"projects\.yaml.*p.*verified"):
        load_catalog(make_content(tmp_path, [service()], projects=projects))


def test_non_bool_faq_approved_rejected(tmp_path):
    faq = [{"q": "Вопрос?", "a": "Ответ", "approved": "yes"}]
    with pytest.raises(CatalogError, match=r"faq\.yaml.*approved"):
        load_catalog(make_content(tmp_path, [service()], faq=faq))


def test_non_bool_consent_approved_rejected(tmp_path):
    policy = {**DEFAULT_POLICY, "consent_approved": "no"}
    with pytest.raises(CatalogError, match=r"policy\.yaml.*consent_approved"):
        load_catalog(make_content(tmp_path, [service()], policy=policy))


@pytest.mark.parametrize("value", ["50000", True, 1.5])
def test_non_int_price_rejected(tmp_path, value):
    with pytest.raises(CatalogError, match=r"services\.yaml.*ai-agent.*price_from"):
        load_catalog(make_content(tmp_path, [service(price_from=value)]))


def test_bool_price_to_rejected(tmp_path):
    with pytest.raises(CatalogError, match=r"price_to"):
        load_catalog(make_content(tmp_path, [service(price_to=True)]))


def test_price_from_above_price_to_rejected(tmp_path):
    with pytest.raises(CatalogError, match=r"ai-agent.*price_from больше price_to"):
        load_catalog(make_content(tmp_path, [service(price_from=300000, price_to=100000)]))


def test_open_ended_prices_are_accepted(tmp_path):
    cat = load_catalog(make_content(tmp_path, [service("a", price_from=None, price_to=90000),
                                               service("b", price_from=80000, price_to=None)]))
    assert cat.price_text("a") == "до 90 000 ₽"
    assert cat.price_text("b") == "от 80 000 ₽"
