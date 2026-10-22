import re

from app.catalog import Fact
from app.skills import SkillReply
from app.state import State, model_may_set, parse_state

# Пробел, неразрывный пробел и узкий неразрывный пробел (разделители тысяч).
_SPACES = " \u00a0\u202f"
_NUM = re.compile(rf"\d(?:[\d{_SPACES}]*\d)?")
_UNIT = re.compile(r"^\s*(%|₽|руб|тыс|млн|k\b|к\b|дн|недел|мес|час|лет|год)", re.I)
# Число клиента с валютой или порядком — это цена клиента; повторить её значит согласиться на неутверждённую цену.
_MONEY_UNIT = re.compile(r"^\s*(₽|руб|тыс|т\.\s*р|млн|р\.|k\b|к\b|\$|евро)", re.I)
_NUM_WORD = (r"(?:один|одн|два|две|двух|три|трёх|трех|четыр|пят|шест|сем|восем|девят|десят|одиннадцат|двенадцат"
             r"|двадцат|тридцат|сорок|девяност|ст[оа]|двест|трист|четырест|полтор|тысяч|сотн|миллион)\w*")
# Цена словами: «пятьдесят тысяч рублей». Сразу после цифр («50 тысяч рублей») не ищем — это проверяет _NUM.
_WORD_PRICE = re.compile(rf"(?<![\w\d])(?<!\d\s){_NUM_WORD}(?:\s+{_NUM_WORD})*\s*(?:руб|₽|тыс)", re.I)
# «скидка/скидки/скидку» и «скидок» (корни скидк- и скидо-).
_DISCOUNT = re.compile(r"скид(?:к|ок)|акци[яиюей]|промокод|бесплатн", re.I)
# Отрицание должно относиться к скидке: «нет проблем, сделаю скидку» — не отказ.
_NO_DISCOUNT = re.compile(
    r"скид(?:ок|к\w*)\s+нет\b|нет\s+скид(?:к|ок)|без\s+скидок?"
    r"|скид(?:к|ок)[^.!?]{0,40}\bне\s+(утвержд|предусмотр|даём|даем|даю|дам|могу|можем|предоставля)"
    r"|\bне\s+(утвержд|предусмотр)\w*[^.!?]{0,40}скид(?:к|ок)"
    r"|\bне\s+(даём|даем|даю|дам|могу|можем|предоставля\w*)\s+скид(?:к|ок)"
    # «Скидки — только по согласованию / уточнит Александр» — тоже не обещание (живая приёмка 2026-10-15).
    r"|скид(?:к|ок)[^.!?]{0,60}(по\s+согласовани|согласовыва|уточн|обсуд|обсужда)",
    re.I,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_SECRET = re.compile(r"cloudru|api_key|\.env\b|skill\.md|role\.md|системн\w*\s+(промпт|инструкц)|system prompt", re.I)
_SENT = re.compile(
    r"(заявк\w*|контакт\w*|запрос\w*|менеджер\w*|александр\w*)[^.!?]{0,40}(отправлен|передан|получил|получен|видит)",
    re.I,
)
_CONTACT = re.compile(r"телефон|номер\w*\s+телефон|e-?mail|почт[аыуе]|контакт", re.I)
# Просьба, а не упоминание: «оставьте телефон», «ваш e-mail». «Номер заявки» и «Александр свяжется» — не просьба.
_ASK = re.compile(r"оставь|остав(ите|ьте)|пришл|присыл|отправ(ьте|ите)|напиш|укаж|дай|сообщ|поделит|продикт|\bваш", re.I)
_PIECES = re.compile(r"(?<=[.!?])(\s+)")


def _asks_contact(sentence: str) -> bool:
    return bool(_CONTACT.search(sentence) and _ASK.search(sentence))


def strip_contact_asks(text: str) -> str:
    """Убирает предложения с просьбой контакта: её показывает код вместе с текстом согласия.

    Модель просит телефон даже вопреки инструкции; без вырезания ответ уходит на доработку и чаще всего
    заканчивается заглушкой, хотя остальной текст годный.
    """
    parts = _PIECES.split(text)
    kept = [s + (parts[i + 1] if i + 1 < len(parts) else "")
            for i, s in enumerate(parts) if i % 2 == 0 and not _asks_contact(s)]
    return "".join(kept).strip()


_CONSENT_QUESTION = re.compile(r"соглас\w*[^.!?]*\?", re.I)


def strip_consent_questions(text: str) -> str:
    """Убирает вопрос «Согласны передать?» перед текстом согласия: согласие — это присланный контакт.

    На такой вопрос клиент отвечает «Согласна» без контакта (живой тест VK 2026-10-22).
    """
    parts = _PIECES.split(text)
    kept = [s + (parts[i + 1] if i + 1 < len(parts) else "")
            for i, s in enumerate(parts) if i % 2 == 0 and not _CONSENT_QUESTION.search(s)]
    return "".join(kept).strip()


def _norm(s: str) -> str:
    return re.sub(rf"[{_SPACES}]", "", s)


def allowed_numbers(texts: list[str]) -> set[str]:
    out: set[str] = set()
    for text in texts:
        for m in _NUM.finditer(text):
            n = _norm(m.group())
            out.add(n)
            value = int(n)
            if value >= 1000 and value % 1000 == 0:
                out.add(str(value // 1000))
    return out


def mentions_price(price: str, text: str) -> bool:
    """Первая сумма цены (нижняя граница) уже есть в тексте — цену не дублируем.

    «от 15 000» без верхней границы честен; дописывать к нему всю вилку — дубль (живая проверка 2026-10-15).
    Одна верхняя граница («200 000») без нижней — не цена «от», её дописываем.
    """
    first = _NUM.search(price)
    return first is not None and _norm(first.group()) in {_norm(m.group()) for m in _NUM.finditer(text)}


def _client_numbers(text: str) -> list[str]:
    return [m.group() for m in _NUM.finditer(text) if not _MONEY_UNIT.match(text[m.end():])]


def _foreign_numbers(text: str, allowed: set[str]) -> list[str]:
    bad: list[str] = []
    for m in _NUM.finditer(text):
        n = _norm(m.group())
        commercial = int(n) >= 10 or bool(_UNIT.match(text[m.end():]))
        if commercial and n not in allowed:
            bad.append(n)
    return bad


def check_reply(reply: SkillReply, *, facts: list[Fact], state: State, client_text: str,
                secrets: list[str]) -> list[str]:
    issues: list[str] = []
    text = reply.reply
    fact_texts = [f.text for f in facts]

    bad = _foreign_numbers(text, allowed_numbers(fact_texts + _client_numbers(client_text)))
    if bad:
        issues.append("numbers: цифры не из фактов каталога: " + ", ".join(bad))
    if words := [m.group() for m in _WORD_PRICE.finditer(text)]:
        issues.append("numbers: цена словами не из фактов каталога: " + ", ".join(words))
    # Честное «скидки не утверждены» — то, чего ждёт сценарий 6; блокируем только обещание скидки.
    promised = [s for s in _SENTENCE.split(text) if _DISCOUNT.search(s) and not _NO_DISCOUNT.search(s)]
    if promised and not any(_DISCOUNT.search(t) for t in fact_texts):
        issues.append("discount: скидки и акции не утверждены в каталоге")
    if _SECRET.search(text) or any(s and s in text for s in secrets):
        issues.append("secret: ответ раскрывает служебные данные")
    if _SENT.search(text):
        issues.append("sent_claim: об отправке заявки сообщает только система")
    if state is not State.CONSENT_PENDING and any(_asks_contact(s) for s in _PIECES.split(text)):
        issues.append("contact_request: контакт запрашивает система через proposed_action ask_consent")
    target = parse_state(reply.next_state)
    # Остаться в текущем состоянии (в т.ч. new → new) всегда допустимо, даже если can_transition(src, src) ложно.
    if target is None or (target is not state and not model_may_set(state, target)):
        issues.append(f"next_state: недопустимый переход {state.value} → {reply.next_state}")
    known = {f.id for f in facts}
    unknown = [fid for fid in reply.facts_used if fid not in known]
    if unknown:
        issues.append("facts_used: неизвестные факты " + ", ".join(unknown))
    return issues
