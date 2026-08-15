from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from app.auth import check_auth
from app.config import settings
from app import db

router = APIRouter(prefix="/admin")
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

_STATUS_LABELS = {
    "new": "Новый",
    "contacted": "Связались",
    "qualified": "Квалифицирован",
    "closed": "Закрыт",
}


@router.get("/", response_class=RedirectResponse)
async def admin_root(_: str = Depends(check_auth)):
    return RedirectResponse(url="/admin/leads")


@router.get("/leads", response_class=HTMLResponse)
async def leads_list(request: Request, _: str = Depends(check_auth)):
    leads = await db.get_all_leads()
    for lead in leads:
        lead["status_label"] = _STATUS_LABELS.get(lead.get("status", "new"), lead.get("status", ""))
        lead["stage"] = "Маркетолог"
    return _TEMPLATES.TemplateResponse("admin/leads.html", {
        "request": request,
        "leads": leads,
        "status_labels": _STATUS_LABELS,
        "agency_name": settings.AGENCY_NAME,
    })


@router.get("/leads/{lead_id}", response_class=HTMLResponse)
async def lead_detail(request: Request, lead_id: int, _: str = Depends(check_auth)):
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
async def update_status(lead_id: int, body: StatusUpdate, _: str = Depends(check_auth)):
    if body.status not in _STATUS_LABELS:
        raise HTTPException(status_code=400, detail="Неверный статус")
    await db.update_lead_status(lead_id, body.status, body.notes or None)
    return {"ok": True}
