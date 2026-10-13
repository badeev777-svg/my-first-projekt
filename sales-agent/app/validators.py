import re

from app.catalog import Fact
from app.skills import SkillReply
from app.state import State, model_may_set, parse_state

# Пробел, неразрывный пробел и узкий неразрывный пробел (разделители тысяч).
_SPACES = " \u00a0\u202f"
_NUM = re.compile(rf"\d(?:[\d{_SPACES}]*\d)?")
_UNIT = re.compile(r"^\s*(%|₽|руб|тыс|млн|k\b|к\b|дн|недел|мес|час|лет|год)", re.I)
# «скидка/скидки/скидку» и «скидок» (корни скидк- и скидо-).
_DISCOUNT = re.compile(r"скид(?:к|ок)|акци[яиюей]|промокод|бесплатн", re.I)
# Отрицание должно относиться к скидке: «нет проблем, сделаю скидку» — не отказ.
_NO_DISCOUNT = re.compile(
    r"скид(?:ок|к\w*)\s+нет\b|нет\s+скид(?:к|ок)|без\s+скидок?"
    r"|скид(?:к|ок)[^.!?]{0,40}\bне\s+(утвержд|предусмотр|даём|даем|даю|дам|могу|можем|предоставля)"
    r"|\bне\s+(утвержд|предусмотр)\w*[^.!?]{0,40}скид(?:к|ок)"
    r"|\bне\s+(даём|даем|даю|дам|могу|можем|предоставля\w*)\s+скид(?:к|ок)",
    re.I,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_SECRET = re.compile(r"cloudru|api_key|\.env\b|skill\.md|role\.md|системн\w*\s+(промпт|инструкц)|system prompt", re.I)
_SENT = re.compile(
    r"(заявк\w*|контакт\w*|запрос\w*|менеджер\w*|александр\w*)[^.!?]{0,40}(отправлен|передан|получил|получен|видит)",
    re.I,
)
_CONTACT = re.compile(r"телефон|номер|e-?mail|почт[аыуе]|контакт", re.I)


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

    bad = _foreign_numbers(text, allowed_numbers(fact_texts + [client_text]))
    if bad:
        issues.append("numbers: цифры не из фактов каталога: " + ", ".join(bad))
    # Честное «скидки не утверждены» — то, чего ждёт сценарий 6; блокируем только обещание скидки.
    promised = [s for s in _SENTENCE.split(text) if _DISCOUNT.search(s) and not _NO_DISCOUNT.search(s)]
    if promised and not any(_DISCOUNT.search(t) for t in fact_texts):
        issues.append("discount: скидки и акции не утверждены в каталоге")
    if _SECRET.search(text) or any(s and s in text for s in secrets):
        issues.append("secret: ответ раскрывает служебные данные")
    if _SENT.search(text):
        issues.append("sent_claim: об отправке заявки сообщает только система")
    if state is not State.CONSENT_PENDING and _CONTACT.search(text):
        issues.append("contact_request: контакт запрашивает система через proposed_action ask_consent")
    target = parse_state(reply.next_state)
    if target is None or not model_may_set(state, target):
        issues.append(f"next_state: недопустимый переход {state.value} → {reply.next_state}")
    known = {f.id for f in facts}
    unknown = [fid for fid in reply.facts_used if fid not in known]
    if unknown:
        issues.append("facts_used: неизвестные факты " + ", ".join(unknown))
    return issues
