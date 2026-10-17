import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.catalog import Policy
from app.handoff import Channel
from app.store import Store

log = logging.getLogger("sales_agent.leads")

# Границы по цифрам отсекают артикулы и суммы; после префикса первая цифра 3-9 (код страны/оператора),
# без префикса только 9 (мобильный). Разделители между группами допускают пробел, NBSP, дефис, точку, скобки.
_SEP = r"[\s \-().]*"
_PHONE = re.compile(
    rf"(?<!\d)(?:(?:\+?7|8){_SEP}[3-9]|9)\d{{2}}{_SEP}\d{{3}}{_SEP}\d{{2}}{_SEP}\d{{2}}(?!\d)"
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


@dataclass(frozen=True)
class Outcome:
    id: int
    delivery_status: str
    created: bool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_phone(raw: str) -> str:
    return "+7" + re.sub(r"\D", "", raw)[-10:]


def extract_contact(text: str) -> str | None:
    if m := _EMAIL.search(text):
        return m.group()
    if m := _PHONE.search(text):
        return _normalize_phone(m.group())
    return None


def mask_contact(contact: str) -> str:
    if "@" in contact:
        name, domain = contact.split("@", 1)
        return f"{name[:1]}***@{domain}"
    return f"+7*** ***-**-{contact[-2:]}"


def mask_text(text: str) -> str:
    text = _EMAIL.sub(lambda m: mask_contact(m.group()), text)
    return _PHONE.sub(lambda m: mask_contact(_normalize_phone(m.group())), text)


def _deliver(channel: Channel, kind: str, payload: dict, demo: bool, contact: str = "") -> str:
    if demo:
        return "demo"
    try:
        return channel.send(kind, payload, contact=contact)
    except Exception:
        # Любой сбой = доставка не подтверждена; клиенту нельзя сообщать об успехе.
        log.exception("delivery failed for %s %s", kind, payload.get("id"))
        return "failed"


def create_lead(store: Store, channel: Channel, *, conversation_id: str, contact: str, need: str,
                product_id: str | None, policy: Policy, demo: bool, epoch: int = 0) -> Outcome:
    real = policy.consent_approved and not demo
    masked = mask_contact(contact)
    lead_id, created = store.create_lead(
        conversation_id=conversation_id, idempotency_key=f"lead:{conversation_id}:{epoch}", contact_masked=masked,
        contact=contact if real else "", consent_status="given" if real else "demo",
        consent_time=_now() if real else None,
        need=mask_text(need)[:500], product_id=product_id or "unknown",
        next_step=f"ответ: {policy.recipient}", delivery_status="pending",
    )
    if not created:
        return Outcome(lead_id, store.get_lead(lead_id)["delivery_status"], False)
    payload = {"id": lead_id, "conversation_id": conversation_id, "contact_masked": masked,
               "need": mask_text(need)[:500], "product_id": product_id or "unknown"}
    status = _deliver(channel, "lead", payload, demo=not real, contact=contact)
    store.set_lead_delivery(lead_id, status)
    return Outcome(lead_id, status, True)


def create_handoff(store: Store, channel: Channel, *, conversation_id: str, reason: str, summary: str,
                   question: str, demo: bool, epoch: int = 0) -> Outcome:
    handoff_id, created = store.create_handoff(
        conversation_id=conversation_id, idempotency_key=f"handoff:{conversation_id}:{epoch}:{reason}", reason=reason,
        summary=mask_text(summary)[:1000], question=mask_text(question)[:500], delivery_status="pending",
    )
    if not created:
        return Outcome(handoff_id, store.get_handoff(handoff_id)["delivery_status"], False)
    payload = {"id": handoff_id, "conversation_id": conversation_id, "reason": reason,
               "summary": mask_text(summary)[:1000]}
    status = _deliver(channel, "handoff", payload, demo=demo)
    store.set_handoff_delivery(handoff_id, status)
    return Outcome(handoff_id, status, True)
