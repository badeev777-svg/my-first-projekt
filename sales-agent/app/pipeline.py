import logging
import re
from dataclasses import dataclass

from app.catalog import Catalog, Fact
from app.estimate import MARKER, Estimator, extract_params, render
from app.handoff import Channel
from app.leads import Outcome, create_handoff, create_lead, extract_contact, mask_text
from app.llm_client import LLM
from app.messenger import channel_label, in_chat
from app.router import Classification, admit, classify, priority_route
from app.skills import SkillReply, quality_check, run_skill
from app.state import State, can_transition, parse_state
from app.store import Conversation, Store
from app.validators import check_reply, mentions_price, strip_consent_questions, strip_contact_asks

log = logging.getLogger("sales_agent.pipeline")

INJECTION_REPLY = ("Я ИИ-менеджер по продажам и не меняю свои правила по просьбе в чате, служебные данные "
                   "не показываю. Расскажите, какая у вас задача?")
HUMAN_PENDING_REPLY = "Этот диалог ждёт ответа человека ({recipient}). Автоматические ответы остановлены."
CLOSED_REPLY = "Хорошо, больше ничего предлагать не буду. Если понадобится помощь, начните новый диалог."
CONTACT_REFUSED_REPLY = "Хорошо, контакт не нужен. Можем продолжить здесь: спрашивайте, что важно для решения."
DEMO_REPLY = ("Демо-режим: модель не подключена, поэтому это шаблонный ответ, а не работа ИИ-продажника. "
              "В рабочем режиме помощник уточнит задачу и подберёт услугу из каталога.")
FALLBACK_REPLY = ("Не получилось подготовить точный ответ. Уточните, пожалуйста, вопрос — или напишите "
                  "«позовите человека», и к разговору подключится {recipient}.")
CONTACT_BEFORE_CONSENT_REPLY = ("Спасибо! Контакт я пока не сохранил: сначала прочитайте, кому и зачем он передаётся. "
                                "Если согласны, отправьте его ещё раз.")
ASK_CONTACT_REPLY = "Спасибо! Напишите, пожалуйста, телефон или e-mail — {recipient} свяжется с вами."
_AGREE_WORDS = {"да", "ага", "угу", "ок", "окей", "ok", "хорошо", "конечно", "давайте", "давай", "можно", "ну",
                "я", "согласна", "согласен", "согласны", "согласие", "передавайте", "отлично", "супер"}
_AGREE_MARKERS = _AGREE_WORDS - {"ну", "я"}
CONFLICT_PREFIX ="В каталоге указаны две разные цены на «{title}», поэтому называть цену не буду. "
LEAD_REPLY = {
    "demo": ("Заявка №{id} сохранена локально в демо-режиме и никому не отправлена. Это не заказ и не оплата. "
             "Автоответы в этом диалоге остановлены."),
    "sent_stub": ("Заявка №{id} передана в тестовый канал (заглушка), получатель — {recipient}. "
                  "Это не заказ и не оплата. "
                  "Пока заявка у человека, автоответы остановлены."),
    "sent": ("Заявка передана — {recipient} свяжется с вами по оставленному контакту. "
             "Это ещё не заказ и не оплата. Если захотите что-то добавить, напишите в Telegram или MAX "
             "— кнопки под чатом."),
    "sent_in_chat": ("Заявка передана — {recipient} ответит вам здесь, в этом чате. "
                     "Это ещё не заказ и не оплата."),
    "failed": ("Не удалось подтвердить передачу заявки №{id}. Она сохранена во внутреннем списке; "
               "отправлять контакт ещё раз не нужно."),
}
HANDOFF_REPLY = {
    "demo": ("Демо-режим: запрос №{id} на связь с человеком ({recipient}) сохранён локально и никому не отправлен. "
             "Автоответы в этом диалоге остановлены."),
    "sent_stub": ("Передаю разговор человеку ({recipient}): запрос №{id} записан в тестовый канал (заглушка). "
                  "Пока диалог у человека, автоответы остановлены."),
    # Контакт в запрос не попадает (маска), поэтому направляем клиента написать самому.
    "sent": ("{recipient} получил ваш запрос. Ваших контактов у него нет, поэтому быстрее всего — "
             "написать в Telegram или MAX (кнопки под чатом)."),
    "sent_in_chat": "{recipient} получил ваш запрос и ответит вам здесь, в этом чате.",
    "failed": ("Не удалось подтвердить передачу запроса №{id} человеку. Он сохранён во внутреннем списке. "
               "Автоответы в этом диалоге остановлены."),
}


@dataclass(frozen=True)
class Turn:
    reply: str | None
    state: State
    skill: str | None = None
    fallback: bool = False
    lead: Outcome | None = None
    handoff: Outcome | None = None
    product: str | None = None


def _outcome(o: Outcome | None) -> dict | None:
    return {"id": o.id, "delivery_status": o.delivery_status} if o else None


def _status_key(o: Outcome, conv: Conversation) -> str:
    return "sent_in_chat" if o.delivery_status == "sent" and in_chat(conv.session_id) else o.delivery_status


def _reachable(src: State, dst: State) -> bool:
    # Прямой переход или через offer: discovery → offer → consent_pending.
    return can_transition(src, dst) or (can_transition(src, State.OFFER) and can_transition(State.OFFER, dst))


def _is_agreement(text: str) -> bool:
    # Только короткое «да/согласна» целиком: «да, но сначала про сроки» — уже вопрос для модели.
    words = re.findall(r"[a-zа-яё]+", text.lower())
    return 0 < len(words) <= 4 and set(words) <= _AGREE_WORDS and bool(set(words) & _AGREE_MARKERS)


def _last_estimate(history: list[tuple[str, str]]) -> list[Fact]:
    # Ориентир дописал код, в фактах его нет: без этого повтор суммы в следующем ответе отклонял валидатор чисел.
    for role, text in reversed(history):
        if role != "user" and (start := text.find(MARKER + " ")) >= 0:
            return [Fact("estimate:last", "Уже названный клиенту " + text[start:].split("\n")[0])]
    return []


def _codes(issues: list[str]) -> list[str]:
    return [i.split(":")[0] for i in issues]


class Pipeline:
    def __init__(self, store: Store, catalog: Catalog, skills: dict[str, str], llm: LLM | None,
                 channel: Channel, secrets: list[str], estimator: Estimator | None = None):
        self._estimator = estimator
        self._store = store
        self._catalog = catalog
        self._skills = skills
        self._llm = llm
        self._channel = channel
        self._secrets = secrets

    @property
    def demo(self) -> bool:
        return self._llm is None

    @property
    def _recipient(self) -> str:
        return self._catalog.policy.recipient

    def handle(self, conv: Conversation, client_message_id: str, text: str) -> dict:
        history = self._store.history(conv.id)  # до захвата: текущая реплика не должна попасть в историю дважды
        # В историю (и значит в модель) полный контакт не попадает никогда; заявка берёт его из text в памяти.
        saved = self._store.claim_message(conv.id, client_message_id, mask_text(text))
        if saved is not None:
            return saved
        try:
            turn = self._process(conv, text, history)
        except Exception:
            # Без снятия захвата «Повторить» с тем же id навсегда получал бы 409.
            self._store.release_claim(conv.id, client_message_id)
            raise
        if turn.product and turn.product != conv.product_id:
            self._store.set_product(conv.id, turn.product)
        if turn.state is not conv.state:
            self._store.set_state(conv.id, turn.state)
        reply = mask_text(turn.reply) if turn.reply else turn.reply
        body = {
            "reply": reply, "state": turn.state.value, "skill": turn.skill, "demo": self.demo,
            "stopped": conv.stopped, "fallback": turn.fallback,
            "lead": _outcome(turn.lead), "handoff": _outcome(turn.handoff),
        }
        self._store.save_response(conv.id, client_message_id, body, reply, turn.skill)
        log.info("turn conv=%s skill=%s state=%s->%s fallback=%s", conv.id, turn.skill, conv.state.value,
                 turn.state.value, turn.fallback)
        return body

    def _process(self, conv: Conversation, text: str, history: list[tuple[str, str]]) -> Turn:
        route = priority_route(text, conv)
        if route == "stopped":
            return Turn(None, conv.state)
        if route == "human_pending":
            return Turn(HUMAN_PENDING_REPLY.format(recipient=self._recipient), conv.state)
        if route in ("closed", "refuse"):
            return Turn(CLOSED_REPLY, State.CLOSED)
        if route == "injection":
            return Turn(INJECTION_REPLY, conv.state)
        if route == "handoff":
            return self._handoff(conv, "client_request", text, history)
        if route == "contact_refused":
            return Turn(CONTACT_REFUSED_REPLY, State.OFFER if conv.state is State.CONSENT_PENDING else conv.state)

        contact = extract_contact(text)
        if contact and conv.state in (State.CONSENT_PENDING, State.LEAD_DRAFT):
            return self._lead(conv, contact, text, history)
        if conv.state is State.LEAD_DRAFT:
            return self._handoff(conv, "lead_not_delivered", text, history)
        if conv.state is State.CONSENT_PENDING and _is_agreement(text):
            # Без готового ответа модель на «Согласна» писала «заявка передана» → заглушка (живой тест VK 2026-10-22).
            return Turn(ASK_CONTACT_REPLY.format(recipient=self._recipient), conv.state, skill="sales-lead-capture")
        if contact and _reachable(conv.state, State.CONSENT_PENDING):
            # Контакт без согласия не сохраняем: показываем условия передачи, клиент пришлёт контакт повторно.
            reply = CONTACT_BEFORE_CONSENT_REPLY + "\n\n" + self._catalog.policy.consent_text
            return Turn(reply, State.CONSENT_PENDING)
        if self._llm is None:
            return Turn(DEMO_REPLY, State.DISCOVERY if conv.state is State.NEW else conv.state)
        return self._model_turn(self._llm, conv, mask_text(text), history)

    def _lead(self, conv: Conversation, contact: str, text: str, history: list[tuple[str, str]]) -> Turn:
        need = " | ".join(t for role, t in history if role == "user")[-500:] or text
        out = create_lead(self._store, self._channel, conversation_id=conv.id, contact=contact, need=need,
                          product_id=conv.product_id, policy=self._catalog.policy, demo=self.demo,
                          epoch=conv.epoch, source=channel_label(conv.session_id))
        reply = LEAD_REPLY.get(_status_key(out, conv), LEAD_REPLY["failed"]).format(
            id=out.id, recipient=self._recipient)
        state = State.LEAD_DRAFT if out.delivery_status == "failed" else State.HUMAN_PENDING
        return Turn(reply, state, skill="sales-lead-capture", lead=out)

    def _handoff(self, conv: Conversation, reason: str, text: str, history: list[tuple[str, str]],
                 prefix: str = "", product: str | None = None) -> Turn:
        summary = " | ".join(t for role, t in history[-6:] if role == "user") or text
        out = create_handoff(self._store, self._channel, conversation_id=conv.id, reason=reason, summary=summary,
                             question=text, demo=self.demo, epoch=conv.epoch,
                             source=channel_label(conv.session_id))
        reply = HANDOFF_REPLY.get(_status_key(out, conv), HANDOFF_REPLY["failed"]).format(
            id=out.id, recipient=self._recipient)
        return Turn(prefix + reply, State.HUMAN_PENDING, skill="sales-human-handoff", handoff=out, product=product)

    def _model_turn(self, llm: LLM, conv: Conversation, text: str, history: list[tuple[str, str]]) -> Turn:
        cls = classify(llm, text, history, {sid: self._catalog.title(sid) for sid in self._catalog.service_ids})
        product = cls.service_id or conv.product_id
        if cls.intent == "refuse":
            return Turn(CLOSED_REPLY, State.CLOSED)
        if cls.intent == "price" and product and self._catalog.price_status(product) == "conflict":
            prefix = CONFLICT_PREFIX.format(title=self._catalog.title(product))
            return self._handoff(conv, "price_conflict", text, history, prefix, product)
        skill = admit(conv.state, cls.intent, product_known=product is not None)
        if skill == "sales-human-handoff":
            return self._handoff(conv, "client_request", text, history, product=product)

        facts = self._catalog.facts() + _last_estimate(history)
        draft = run_skill(llm, self._skills[skill], self._catalog, facts, conv.state, history, text)
        verdict, issues = self._vet(llm, draft, facts, conv.state, text)
        if verdict == "revise":
            log.info("revise conv=%s skill=%s issues=%s", conv.id, skill, _codes(issues))
            draft = run_skill(llm, self._skills[skill], self._catalog, facts, conv.state, history, text, issues)
            verdict, issues = self._vet(llm, draft, facts, conv.state, text)
        if verdict == "human":
            return self._handoff(conv, "quality_review", text, history, product=product)
        if verdict != "ok" or draft is None:
            log.warning("fallback conv=%s skill=%s issues=%s", conv.id, skill, _codes(issues))
            return Turn(FALLBACK_REPLY.format(recipient=self._recipient), conv.state, skill=skill, fallback=True, product=product)
        return self._finish(llm, conv, cls, product, skill, draft, text, history)

    def _vet(self, llm: LLM, draft: SkillReply | None, facts: list, state: State,
             text: str) -> tuple[str, list[str]]:
        if draft is None:
            return "revise", ["format: ответ не соответствует JSON-контракту"]
        if state is not State.CONSENT_PENDING and (rest := strip_contact_asks(draft.reply)):
            # Объект изменяется на месте: дальше в _finish уходит уже очищенный ответ.
            draft.reply = rest
        issues = check_reply(draft, facts=facts, state=state, client_text=text, secrets=self._secrets)
        if issues:
            return "revise", issues
        if draft.review_status == "needs_review":
            verdict = quality_check(llm, self._skills["sales-quality-check"], draft, facts)
            if verdict == "human_review":
                return "human", []
            if verdict != "pass":
                return "revise", ["quality: проверка качества вернула ответ на доработку"]
        return "ok", []

    def _estimate(self, llm: LLM, product: str, text: str, history: list[tuple[str, str]]) -> str | None:
        est = self._estimator
        bounds = self._catalog.price_range(product)
        if est is None or product not in est.services or bounds is None:
            return None
        params = extract_params(llm, est, text, history)
        if params is None:
            return None
        e = est.estimate(params, *bounds)
        log.info("estimate product=%s hours=%s over_price=%s", product, e.hours, e.over_price)
        return render(e, self._recipient)

    def _finish(self, llm: LLM, conv: Conversation, cls: Classification, product: str | None, skill: str,
                draft: SkillReply, text: str, history: list[tuple[str, str]]) -> Turn:
        if draft.proposed_action == "handoff":
            return self._handoff(conv, "model_request", text, history, prefix=draft.reply + "\n\n", product=product)
        reply = draft.reply
        target = parse_state(draft.next_state)
        if target is State.CONSENT_PENDING:
            # В consent_pending ведёт только ask_consent (с текстом согласия); иначе контакт станет заявкой без согласия.
            target = conv.state
        consent_ok = (can_transition(conv.state, State.CONSENT_PENDING)
                      or (conv.state is State.DISCOVERY and product is not None))
        if draft.proposed_action == "ask_consent" and consent_ok:
            # Текст согласия добавляет код: модель не может исказить, кому и зачем уходит контакт.
            reply = strip_consent_questions(reply)
            reply = (reply + "\n\n" if reply else "") + self._catalog.policy.consent_text
            target = State.CONSENT_PENDING
        price_shown = False
        if cls.intent == "price" and product:
            status = self._catalog.price_status(product)
            title = self._catalog.title(product)
            price = self._catalog.price_text(product)
            if status == "approved" and price:
                price_shown = True
                if estimate := self._estimate(llm, product, text, history):
                    reply += "\n\n" + estimate
                elif not mentions_price(price, reply):
                    reply += f"\n\nЦена «{title}»: {price}."
            elif status in ("unapproved", "none") and "уточн" not in reply.lower():
                reply += f"\n\nЦена «{title}» в каталоге не утверждена — её уточнит {self._recipient}."
        if conv.state is State.DISCOVERY and (cls.service_id or price_shown) and target in (None, State.DISCOVERY):
            # Модель часто остаётся в discovery, хотя услуга уже названа; без offer диалог не дойдёт до заявки.
            target = State.OFFER
        state = target if target is not None and _reachable(conv.state, target) else conv.state
        return Turn(reply, state, skill=skill, product=product)
