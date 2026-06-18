import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from app.config import settings
from app import db

router = APIRouter(prefix="/admin")
security = HTTPBasic()
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

_STATUS_LABELS = {
    "new": "Новый",
    "contacted": "Связались",
    "qualified": "Квалифицирован",
    "closed": "Закрыт",
}


def _check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    admin_login = getattr(settings, "ADMIN_LOGIN", "admin")
    admin_password = getattr(settings, "ADMIN_PASSWORD", "changeme")
    ok_user = secrets.compare_digest(credentials.username.encode(), admin_login.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), admin_password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.get("/", response_class=RedirectResponse)
async def admin_root(_: str = Depends(_check_auth)):
    return RedirectResponse(url="/admin/leads")


@router.get("/leads", response_class=HTMLResponse)
async def leads_list(request: Request, _: str = Depends(_check_auth)):
    leads = await db.get_all_leads()
    for lead in leads:
        lead["status_label"] = _STATUS_LABELS.get(lead.get("status", "new"), lead.get("status", ""))
        stage = "Agent 1"
        if lead.get("has_agent2"):
            stage = "Agent 2"
        if lead.get("has_agent3"):
            stage = "Agent 3"
        lead["stage"] = stage
    return _TEMPLATES.TemplateResponse("admin/leads.html", {
        "request": request,
        "leads": leads,
        "status_labels": _STATUS_LABELS,
        "agency_name": settings.AGENCY_NAME,
    })


@router.get("/leads/{lead_id}", response_class=HTMLResponse)
async def lead_detail(request: Request, lead_id: int, _: str = Depends(_check_auth)):
    lead = await db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    messages = await db.get_messages_by_session(lead["session_id"])
    return _TEMPLATES.TemplateResponse("admin/lead_detail.html", {
        "request": request,
        "lead": lead,
        "messages": messages,
        "status_labels": _STATUS_LABELS,
        "agency_name": settings.AGENCY_NAME,
    })


class StatusUpdate(BaseModel):
    status: str
    notes: str = ""


@router.post("/leads/{lead_id}/status")
async def update_status(lead_id: int, body: StatusUpdate, _: str = Depends(_check_auth)):
    if body.status not in _STATUS_LABELS:
        raise HTTPException(status_code=400, detail="Неверный статус")
    await db.update_lead_status(lead_id, body.status, body.notes or None)
    return {"ok": True}
