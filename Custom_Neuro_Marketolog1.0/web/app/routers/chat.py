import re
import uuid

from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.agent import store
from app.config import settings
from app.ip_limiter import is_allowed
from app.lead_parser import parse_handoff_block
from app.notifications import notify_all, notify_contact
from app import db

router = APIRouter(prefix="/api")

_MAX_INPUT_LEN = 2000
_MAX_SESSION_MSGS = 50
_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


class MessageIn(BaseModel):
    text: str


class MessageOut(BaseModel):
    reply: str
    finished: bool
    contact_link: str | None = None


@router.post("/start", response_model=MessageOut)
async def start_session(
    request: Request,
    response: Response,
    session_id: str = Cookie(default=None),
    utm_source: str = Query(default=""),
    utm_medium: str = Query(default=""),
    utm_campaign: str = Query(default=""),
):
    ip = request.headers.get("X-Real-IP") or request.client.host
    if not is_allowed(ip):
        raise HTTPException(status_code=429, detail="Вы уже прошли диагностику сегодня. Возвращайтесь завтра!")

    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie("session_id", session_id, max_age=86400 * 7, httponly=True)

    reply = await store.start(session_id)
    session = store.get_or_create(session_id)

    await db.create_session(session_id, ip, utm_source, utm_medium, utm_campaign)

    contact = settings.CONTACT_LINK if session.finished else None
    return MessageOut(reply=reply, finished=session.finished, contact_link=contact)


@router.post("/chat", response_model=MessageOut)
async def chat(
    body: MessageIn,
    response: Response,
    session_id: str = Cookie(default=None),
):
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie("session_id", session_id, max_age=86400 * 7, httponly=True)

    if len(body.text) > _MAX_INPUT_LEN:
        raise HTTPException(status_code=400, detail="Message too long")

    session = store.get_or_create(session_id)
    if session.msg_count >= _MAX_SESSION_MSGS:
        raise HTTPException(status_code=429, detail="Session limit reached")

    clean = _sanitize(body.text)
    reply = await store.chat(session_id, clean)
    session = store.get_or_create(session_id)

    if session.finished and session.handoff_block:
        parsed = parse_handoff_block(session.handoff_block)
        utm = await db.get_session_utm(session_id)
        lead_id = await db.save_lead(
            session_id,
            business_name=parsed.get("business_name", ""),
            niche=parsed.get("niche", ""),
            pain_points=parsed.get("pain_points", ""),
            budget_estimate=parsed.get("budget_estimate", ""),
            utm_source=utm["utm_source"],
            utm_medium=utm["utm_medium"],
            utm_campaign=utm["utm_campaign"],
        )
        await notify_all(session.handoff_block, lead_id, utm["utm_source"], utm["utm_medium"])
        await db.finish_session(session_id, session.msg_count, session.handoff_block)
    else:
        await db.update_msg_count(session_id, session.msg_count)

    contact = settings.CONTACT_LINK if session.finished else None
    return MessageOut(reply=reply, finished=session.finished, contact_link=contact)


@router.post("/undo", response_model=MessageOut)
async def undo_last(session_id: str = Cookie(default=None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="No session")
    prev_reply = store.undo(session_id)
    if prev_reply is None:
        raise HTTPException(status_code=400, detail="Nothing to undo")
    return MessageOut(reply=prev_reply, finished=False, contact_link=None)


@router.post("/reset")
async def reset_session(session_id: str = Cookie(default=None)):
    if session_id:
        store.reset(session_id)
    return {"ok": True}


@router.get("/stats")
async def stats():
    return await db.get_stats()


class ContactIn(BaseModel):
    name: str
    phone: str
    email: str = ""


@router.post("/contact")
async def contact(body: ContactIn):
    name = _sanitize(body.name)[:100]
    phone = _sanitize(body.phone)[:30]
    email = _sanitize(body.email)[:100]
    if not name or not phone:
        raise HTTPException(status_code=400, detail="Имя и телефон обязательны")
    await notify_contact(name, phone, email)
    return {"ok": True}
