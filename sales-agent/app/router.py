import re
from dataclasses import dataclass
from typing import Literal

from app.llm_client import LLM
from app.skills import build_user, extract_json
from app.state import State
from app.store import Conversation

INTENTS = ("question", "need", "price", "objection", "agree", "refuse", "human", "other")
RouteKind = Literal["stopped", "human_pending", "closed", "injection", "handoff", "contact_refused", "refuse"]

_INJECTION = re.compile(
    r"игнорир\w*[^.!?]{0,30}(правил|инструкц)|забуд\w*[^.!?]{0,20}(правил|инструкц)"
    r"|ignore\s+(all|previous|the|your)|system\s*prompt|developer\s+mode|режим\w*\s+разработчика|ты\s+теперь\s+(не|друг)"
    r"|api[\s_-]?(key|ключ)"
    # Секрет = глагол раскрытия с границей слова + прямая цепочка притяжательных/«системный» перед существительным;
    # «расскажите про промпт-инжиниринг», «подскажите, как хранить пароль» — продажи, не раскрытие.
    r"|\b(покаж|выведи|раскро|скаж|напиш|дай|сообщ|повтор)\w*[^.!?]{0,25}?"
    r"\b(?:(?:ваш|свой|свои|твой|твои|системн|секретн|скрыт|внутренн|мне)\w*\s+)+"
    r"(промпт|токен|пароль|(?<!под )ключ(?:и|а|ом|у)?\b)"
    r"|\b(покаж|выведи|раскро|скаж|повтор)\w*[^.!?]{0,25}?"
    r"\b(?:(?:ваш|свой|свои|твой|твои|системн|секретн|скрыт|внутренн|мне)\w*\s+)+инструкци",
    re.I,
)
# Контакт-глагол обязателен: «для 100 человек» и «заменит менеджера» — не просьба о человеке.
# «поговорим о сайте для менеджеров» — нет «с» перед целью, не совпадает.
_HUMAN = re.compile(
    r"(соедин|переключ|свяж|связа|позов)\w*[^.!?]{0,25}?(человек|менеджер|оператор|специалист|александр)"
    r"|(поговор|пообщ|общат)\w*\s+(?:с|со)\s+(?:живым\s+|живой\s+|настоящим\s+)?(человек|менеджер|оператор|специалист|александр)"
    r"|(?:с|со)\s+(человек|менеджер|оператор|александр)\w*\s+(поговор|пообщ|связ)"
    r"|(живой|живым|настоящ\w*)\s+(человек|оператор|менеджер)"
    r"|передай\w*[^.!?]{0,30}(менеджер|александр|оператор|специалист)"
    r"|(перевед|переключ)\w*\s+(?:\S+\s+)?на\s+(человек|менеджер|оператор|специалист|александр)"
    r"|^\s*(нужен|можно|дайте|позовите)\s+(живого\s+)?(человек|менеджер|оператор)\w*\s*[?!.]*\s*$",
    re.I,
)
# «Вы человек или бот?» — вопрос о помощнике, а не просьба позвать человека (живая проверка 2026-10-20).
_ASKS_IF_BOT = re.compile(
    r"\b(?:человек|бот|робот|ии)\s+или\s+(?:человек|бот|робот|ии|нейросеть)\b"
    r"|^\W*(?:а\s+)?(?:вы|ты|это)\s+(?:\w+\s+)?(?:бот|робот|ии|нейросеть)\W*$",
    re.I,
)
# Отказ от отдачи своих контактов; «без контактной формы» и «на почту» (о боте) — не отказ.
_CONTACT_REFUSED = re.compile(
    r"не\s+(?:хочу|буду|дам|оставлю|готов\w*)\s+"
    r"(?:(?:оставить|оставлять|давать|дать|делиться|сообщать|писать)\s+)?"
    r"(?:(?:вам|свой|свои|мой|мои|свою|мою|свое|моё)\s+)?"
    r"(?:телефон\w*|номер\w*|контактн\w+\s+данн\w+|контакт(?:ы|ов)?|почт\w*|e-?mail)\b"
    r"|без\s+контакт(?:ов|а|ы)?\b",
    re.I,
)
# Узко: «мне не нужно сложное…» — это не отказ, закрывать диалог по нему нельзя.
_REFUSE = re.compile(
    r"^\W*(нет[,.!\s]*)?(спасибо[,.!\s]*)?(мне\s+)?(это\s+)?(не\s+интересно|не\s+интересует|неинтересно|не\s+надо|не\s+нужно)\W*$"
    r"|(?<!не )(?:отказываюсь|откажусь)|отстаньте|не\s+пишите\s+мне|больше\s+не\s+пишите",
    re.I,
)

CLASSIFIER_SYSTEM = """Ты — классификатор намерений клиента в чате продаж. Определи намерение последнего сообщения клиента (client_message).
intent — одно из:
- question: вопрос о компании, услугах, проектах, порядке работы
- need: клиент описывает свою задачу или потребность
- price: спрашивает цену или стоимость
- objection: сомнение или возражение (дорого, не уверен, а если не получится)
- agree: согласен на предложенный следующий шаг
- refuse: отказывается от общения или покупки
- human: просит живого человека (вопрос «вы человек или бот?» — это question)
- other: всё остальное
service_id — id услуги из списка (id — название), о которой идёт речь, иначе null.
Услуги:
{services}
Ответь ТОЛЬКО JSON: {{"intent": "...", "service_id": "..." или null}}"""


@dataclass(frozen=True)
class Classification:
    intent: str
    service_id: str | None


def priority_route(text: str, conv: Conversation) -> RouteKind | None:
    if conv.stopped:
        return "stopped"
    if conv.state is State.HUMAN_PENDING:
        return "human_pending"
    if conv.state is State.CLOSED:
        return "closed"
    if _INJECTION.search(text):
        return "injection"
    if _HUMAN.search(text) and not _ASKS_IF_BOT.search(text):
        return "handoff"
    if _CONTACT_REFUSED.search(text):
        return "contact_refused"
    if _REFUSE.search(text):
        return "refuse"
    return None


def classify(llm: LLM, text: str, history: list[tuple[str, str]], services: dict[str, str]) -> Classification:
    # Одних id мало: «ответы по регламентам» без названий уходили в ai-agent вместо rag-docs (живая проверка 2026-10-15).
    system = CLASSIFIER_SYSTEM.format(services="\n".join(f"- {sid} — {title}" for sid, title in services.items()))
    data = extract_json(llm.chat(system, build_user(history[-4:], text))) or {}
    intent = data.get("intent")
    if intent == "human" and _ASKS_IF_BOT.search(text):
        intent = "question"
    service_id = data.get("service_id")
    return Classification(
        intent=intent if intent in INTENTS else "other",
        service_id=service_id if service_id in services else None,
    )


_ADMISSION: dict[tuple[State, str], str] = {}
for _st in (State.NEW, State.DISCOVERY, State.OFFER, State.CONSENT_PENDING):
    _ADMISSION[(_st, "question")] = "sales-product-match"
    _ADMISSION[(_st, "price")] = "sales-product-match"
    _ADMISSION[(_st, "need")] = "sales-discovery"
    _ADMISSION[(_st, "objection")] = "sales-objections"
    _ADMISSION[(_st, "human")] = "sales-human-handoff"
_ADMISSION[(State.OFFER, "need")] = "sales-product-match"
_ADMISSION[(State.OFFER, "agree")] = "sales-lead-capture"
_ADMISSION[(State.CONSENT_PENDING, "agree")] = "sales-lead-capture"
for _intent in INTENTS:
    # Заявка не дошла — дальше разговор ведёт человек.
    _ADMISSION[(State.LEAD_DRAFT, _intent)] = "sales-human-handoff"


def admit(state: State, intent: str, product_known: bool = False) -> str:
    # Модель может не перевести диалог в offer, хотя услуга уже ясна; согласие клиента тогда всё равно ведёт к заявке.
    if state is State.DISCOVERY and intent == "agree" and product_known:
        return "sales-lead-capture"
    return _ADMISSION.get((state, intent), "sales-discovery")
