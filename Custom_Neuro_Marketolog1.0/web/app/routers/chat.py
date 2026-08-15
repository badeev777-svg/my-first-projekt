import re
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.agent import store, REPORT_MARKER, PAID_SPLIT
from app.auth import check_auth
from app.config import settings
from app.ip_limiter import is_allowed
from app.notifications import notify_all, notify_contact
from app import db

router = APIRouter(prefix="/api")

_MAX_INPUT_LEN = 2000
_MAX_SESSION_MSGS = 60
_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _extract_lead_info(report: str) -> tuple[str, str, str]:
    """Pull business_name, niche, pain_points from the generated report."""
    business_name = ""
    niche = ""
    pain_points = ""

    for line in report.splitlines():
        low = line.lower()
        if "ниша" in low and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                niche = parts[2]
        if "продукт" in low and "|" in line and not business_name:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                business_name = parts[2]

    # Extract first Quick Win as pain point proxy
    in_qw = False
    wins = []
    for line in report.splitlines():
        if "quick wins" in line.lower() or "топ-5 действий" in line.lower():
            in_qw = True
        elif in_qw and line.strip().startswith(("1.", "2.", "3.")):
            wins.append(line.strip())
        elif in_qw and line.startswith("###") and "quick wins" not in line.lower():
            break
    if wins:
        pain_points = "; ".join(wins[:3])

    pain_points = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", pain_points)
    return business_name[:200], niche[:100], pain_points[:500]


class MessageIn(BaseModel):
    text: str


class MessageOut(BaseModel):
    reply: str
    finished: bool
    contact_link: str | None = None


class UnlockIn(BaseModel):
    token: str


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
        response.set_cookie("session_id", session_id, max_age=86400 * 7, httponly=True, secure=True, samesite="lax")

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
        response.set_cookie("session_id", session_id, max_age=86400 * 7, httponly=True, secure=True, samesite="lax")

    if len(body.text) > _MAX_INPUT_LEN:
        raise HTTPException(status_code=400, detail="Message too long")

    session = store.get_or_create(session_id)
    if session.msg_count >= _MAX_SESSION_MSGS:
        raise HTTPException(status_code=429, detail="Session limit reached")

    clean = _sanitize(body.text)
    reply = await store.chat(session_id, clean)
    session = store.get_or_create(session_id)

    if session.finished and session.report_text:
        business_name, niche, pain_points = _extract_lead_info(session.report_text)
        utm = await db.get_session_utm(session_id)
        lead_id = await db.save_lead(
            session_id,
            business_name=business_name,
            niche=niche,
            pain_points=pain_points,
            utm_source=utm["utm_source"],
            utm_medium=utm["utm_medium"],
            utm_campaign=utm["utm_campaign"],
        )
        await notify_all(
            lead_id=lead_id,
            business_name=business_name,
            niche=niche,
            pain_points=pain_points,
            utm_source=utm["utm_source"],
            utm_medium=utm["utm_medium"],
        )
        await db.finish_session(session_id, session.msg_count, session.report_text)
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


@router.post("/unlock")
async def unlock(body: UnlockIn, response: Response):
    valid = settings.get_valid_tokens()
    if not valid or body.token.strip() not in valid:
        raise HTTPException(status_code=403, detail="Неверный токен доступа")
    response.set_cookie("nm_unlocked", "1", max_age=86400 * 30, httponly=True, secure=True, samesite="lax")
    return {"ok": True}


@router.get("/unlock-status")
async def unlock_status(nm_unlocked: str = Cookie(default="")):
    return {"unlocked": nm_unlocked == "1"}


@router.get("/stats")
async def stats(_: str = Depends(check_auth)):
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
