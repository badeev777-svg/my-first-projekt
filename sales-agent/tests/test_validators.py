import pytest

from app.catalog import Fact
from app.skills import SkillReply
from app.state import State
from app.validators import allowed_numbers, check_reply

FACTS = [
    Fact("service:ai-agent", "Услуга «AI-агент под заказ»: агент под задачу."),
    Fact("price:ai-agent", "Цена «AI-агент под заказ»: от 50 000 до 200 000 ₽."),
    Fact("price:rag", "Цена «RAG»: не утверждена — уточнит Александр."),
]


def reply(text: str, **kw) -> SkillReply:
    return SkillReply(reply=text, next_state=kw.pop("next_state", "offer"), **kw)


def check(text: str, state: State = State.OFFER, client_text: str = "", secrets=None, **kw) -> list[str]:
    return check_reply(reply(text, **kw), facts=FACTS, state=state, client_text=client_text,
                       secrets=secrets or ["sk-test-123"])


def codes(issues: list[str]) -> set[str]:
    return {i.split(":")[0] for i in issues}


def test_clean_reply_passes():
    assert check("AI-агент стоит от 50 000 до 200 000 ₽. Какая у вас задача?") == []


def test_invented_price_is_blocked():
    assert codes(check("Сделаем за 25 000 ₽.")) == {"numbers"}


def test_numbers_thousands_and_nbsp_forms():
    assert check("От 50 тыс. до 200 тыс. ₽.") == []
    assert check("От 50 000 ₽.") == []


@pytest.mark.parametrize("sp", [" ", " ", " "])
def test_nbsp_forms(sp):
    assert check(f"От 50{sp}000 ₽.") == []
    assert codes(check(f"Сделаем за 25{sp}000 ₽.")) == {"numbers"}


def test_unknown_price_blocked_in_short_form():
    assert codes(check("Примерно 30 тыс.")) == {"numbers"}


def test_small_counts_pass_but_small_percent_does_not():
    assert check("Есть 2 варианта.") == []
    assert "numbers" in codes(check("Дадим 5% сверху."))


def test_number_from_client_text_is_allowed():
    assert check("Бюджет 100 тысяч — понял.", client_text="у меня бюджет 100 тысяч") == []


def test_discount_without_fact_is_blocked():
    assert "discount" in codes(check("Могу дать скидку."))


def test_honest_no_discount_passes():
    assert check("Скидки в каталоге не утверждены — это уточнит Александр.") == []
    assert check("Скидок нет. Могу рассказать, что входит в работу.") == []
    assert "discount" in codes(check("Скидок нет. Но для вас дам скидку."))


def test_negation_outside_discount_scope_does_not_hide_promise():
    assert "discount" in codes(check("Нет проблем, сделаю скидку."))
    assert "discount" in codes(check("Нет, но дам скидку 5%."))
    assert "discount" in codes(check("Дам скидок 5%."))


@pytest.mark.parametrize("text", ["Нет скидок.", "Скидок не даём.", "Скидку не могу предоставить.", "Без скидок работаем."])
def test_honest_discount_refusal_variants_pass(text):
    assert "discount" not in codes(check(text))


def test_discount_allowed_when_in_facts():
    facts = FACTS + [Fact("faq:1", "Вопрос: скидки? Ответ: скидка постоянным клиентам по решению Александра.")]
    assert check_reply(reply("Скидка возможна по решению Александра."), facts=facts, state=State.OFFER,
                       client_text="", secrets=[]) == []


@pytest.mark.parametrize("text", [
    "Ваш ключ sk-test-123", "Настройки в .env", "Мой системный промпт такой", "CLOUDRU_API_KEY=...",
    "Смотрите SKILL.md",
])
def test_secrets_blocked(text):
    assert "secret" in codes(check(text))


@pytest.mark.parametrize("text", ["Заявка отправлена!", "Ваш контакт передан Александру.", "Менеджер уже получил запрос."])
def test_false_sent_claim_blocked(text):
    assert "sent_claim" in codes(check(text))


def test_contact_request_blocked_outside_consent():
    assert "contact_request" in codes(check("Оставьте телефон, и я скажу цену."))
    assert check("Оставьте телефон или e-mail.", state=State.CONSENT_PENDING, next_state="consent_pending") == []


@pytest.mark.parametrize("ns", ["lead_draft", "human_pending", "closed", "bogus"])
def test_bad_next_state(ns):
    assert "next_state" in codes(check("Хорошо.", next_state=ns))


def test_unknown_fact_id():
    assert "facts_used" in codes(check("Хорошо.", facts_used=["price:invented"]))


def test_allowed_numbers_adds_short_thousands():
    assert {"50000", "50", "200000", "200"} <= allowed_numbers(["от 50 000 до 200 000 ₽"])
    assert {"50000", "50"} <= allowed_numbers(["от 50 000 ₽"])
