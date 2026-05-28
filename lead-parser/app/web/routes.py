from fastapi import APIRouter, Depends, Request, Form, Query, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from datetime import datetime, timezone, timedelta
import re
import csv
import io
import json
import uuid

from app.database import Lead, Status, DemoUser, LeadAction, DealStage, get_session
from app.analyzer import analyze_lead
from app.auth import is_password_set, verify_password, get_password_hash, ADMIN_PASSWORD

router = APIRouter(prefix="/leads")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

SOURCE_LABELS = {
    "telegram": "Telegram",
    "fl": "FL.ru",
    "habr": "Habr Freelance",
    "kwork": "Kwork",
}

PAGE_SIZE = 25
SESSION_TIMEOUT = timedelta(days=7)


def is_authenticated(session_token: str = Cookie(None)) -> bool:
    """Check if user has valid session token."""
    if not is_password_set():
        return True
    if not session_token:
        return False
    return bool(session_token and len(session_token) > 0)


async def require_auth(
    request: Request,
    session_token: str = Cookie(None),
) -> bool:
    """Dependency for protecting routes."""
    if not is_password_set():
        return True
    if not session_token:
        raise RedirectResponse(url="/leads/login", status_code=302)
    return True


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, session_token: str = Cookie(None)):
    if not is_password_set():
        return RedirectResponse(url="/leads/", status_code=302)
    if session_token:
        return RedirectResponse(url="/leads/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    password: str = Form(...),
):
    if not is_password_set():
        return RedirectResponse(url="/leads/", status_code=302)

    if verify_password(password, ADMIN_PASSWORD):
        response = RedirectResponse(url="/leads/", status_code=302)
        token = str(uuid.uuid4())
        response.set_cookie(
            "session_token",
            token,
            max_age=int(SESSION_TIMEOUT.total_seconds()),
            httponly=True,
            samesite="lax",
        )
        return response

    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Неверный пароль"},
        status_code=401
    )


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/leads/login" if is_password_set() else "/leads/", status_code=302)
    response.delete_cookie("session_token")
    return response


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = Query(1, ge=1),
    source: str = Query(""),
    status: str = Query(""),
    search: str = Query(""),
    min_relevance: int = Query(0, ge=0, le=100),
    assigned_to: str = Query(""),
    session: AsyncSession = Depends(get_session),
    auth: bool = Depends(require_auth),
):
    query = select(Lead).order_by(Lead.fetched_at.desc())
    count_query = select(func.count()).select_from(Lead)

    filters = []
    if source:
        filters.append(Lead.source == source)
    if status:
        filters.append(Lead.status == status)
    if search:
        filters.append(
            (Lead.title.ilike(f"%{search}%")) |
            (Lead.text.ilike(f"%{search}%"))
        )
    if min_relevance > 0:
        filters.append(Lead.relevance_score >= min_relevance)
    if assigned_to:
        filters.append(Lead.assigned_to == assigned_to)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = await session.scalar(count_query) or 0
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    offset = (page - 1) * PAGE_SIZE

    leads = (await session.scalars(query.offset(offset).limit(PAGE_SIZE))).all()

    new_count = await session.scalar(
        select(func.count()).select_from(Lead).where(Lead.status == Status.new)
    ) or 0

    # Получить список уникальных исполнителей
    assignees_result = await session.execute(
        select(Lead.assigned_to).where(Lead.assigned_to.isnot(None)).distinct()
    )
    unique_assignees = [a[0] for a in assignees_result.all()]
    unique_assignees.sort()

    # Mark viewed
    for lead in leads:
        if lead.status == Status.new:
            lead.status = Status.viewed
    await session.commit()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "leads": leads,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "source": source,
            "status": status,
            "search": search,
            "min_relevance": min_relevance,
            "assigned_to": assigned_to,
            "unique_assignees": unique_assignees,
            "source_labels": SOURCE_LABELS,
            "counts": {"new": new_count, "total": total},
            "is_authenticated": bool(request.cookies.get("session_token")),
        },
    )


@router.get("/lead/{lead_id}", response_class=HTMLResponse)
async def lead_detail(
    request: Request,
    lead_id: int,
    session: AsyncSession = Depends(get_session),
):
    lead = await session.get(Lead, lead_id)
    if not lead:
        return HTMLResponse("Not found", status_code=404)

    if lead.status == Status.new:
        lead.status = Status.viewed
        await session.commit()

    return templates.TemplateResponse(
        request,
        "lead.html",
        {
            "lead": lead,
            "source_labels": SOURCE_LABELS,
            "is_authenticated": bool(request.cookies.get("session_token")),
        },
    )


@router.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    return templates.TemplateResponse(
        request,
        "portfolio.html",
        {"is_authenticated": bool(request.cookies.get("session_token"))},
    )


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth: bool = Depends(require_auth),
):
    # Лиды по источникам
    by_source = await session.execute(
        select(Lead.source, func.count(Lead.id).label("count"))
        .group_by(Lead.source)
        .order_by(func.count(Lead.id).desc())
    )
    leads_by_source = {row.source: row.count for row in by_source.all()}

    # Лиды по статусам
    by_status = await session.execute(
        select(Lead.status, func.count(Lead.id).label("count"))
        .group_by(Lead.status)
    )
    leads_by_status = {row.status: row.count for row in by_status.all()}

    # Средняя релевантность по источникам
    avg_relevance = await session.execute(
        select(Lead.source, func.avg(Lead.relevance_score).label("avg_score"))
        .where(Lead.relevance_score.isnot(None))
        .group_by(Lead.source)
    )
    relevance_by_source = {row.source: round(row.avg_score or 0, 1) for row in avg_relevance.all()}

    # Тренд за 14 дней
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
    trend_query = await session.execute(
        select(
            func.date(Lead.created_at).label("date"),
            func.count(Lead.id).label("count")
        )
        .where(Lead.created_at >= fourteen_days_ago)
        .group_by(func.date(Lead.created_at))
        .order_by(func.date(Lead.created_at))
    )
    trend_data = [(str(row.date), row.count) for row in trend_query.all()]

    # KPI
    total = await session.scalar(select(func.count()).select_from(Lead)) or 0
    today = datetime.now(timezone.utc).date()
    today_count = await session.scalar(
        select(func.count()).select_from(Lead)
        .where(func.date(Lead.created_at) == today)
    ) or 0
    avg_rel = await session.scalar(
        select(func.avg(Lead.relevance_score)).select_from(Lead)
        .where(Lead.relevance_score.isnot(None))
    ) or 0
    avg_budget = await session.scalar(
        select(func.avg(Lead.budget)).select_from(Lead)
        .where(Lead.budget.isnot(None))
    ) or 0

    # Сравнение платформ (для таблицы)
    platforms_comparison = []
    for source in ["fl", "habr", "kwork", "telegram"]:
        count = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.source == source)
        ) or 0

        if count > 0:
            avg_rel_src = await session.scalar(
                select(func.avg(Lead.relevance_score)).select_from(Lead)
                .where(and_(Lead.source == source, Lead.relevance_score.isnot(None)))
            ) or 0

            avg_budget_src = await session.scalar(
                select(func.avg(Lead.budget)).select_from(Lead)
                .where(and_(Lead.source == source, Lead.budget.isnot(None)))
            ) or 0

            high_relevance = await session.scalar(
                select(func.count()).select_from(Lead)
                .where(and_(Lead.source == source, Lead.relevance_score >= 80))
            ) or 0

            min_created = await session.scalar(
                select(func.min(Lead.created_at)).select_from(Lead).where(Lead.source == source)
            )
            max_created = await session.scalar(
                select(func.max(Lead.created_at)).select_from(Lead).where(Lead.source == source)
            )

            days_active = 1
            if min_created and max_created:
                days_active = max(1, (max_created - min_created).days + 1)

            leads_per_day = round(count / days_active, 1) if days_active > 0 else 0
            high_rel_percent = round((high_relevance / count * 100), 0) if count > 0 else 0

            platforms_comparison.append({
                "source": source,
                "count": count,
                "avg_relevance": round(avg_rel_src, 1),
                "avg_budget": round(avg_budget_src, 0),
                "leads_per_day": leads_per_day,
                "high_relevance_percent": int(high_rel_percent),
            })

    # Метрики конверсии
    won_count = await session.scalar(
        select(func.count()).select_from(Lead).where(Lead.deal_stage == DealStage.won)
    ) or 0
    conversion_rate = round((won_count / total * 100), 1) if total > 0 else 0

    avg_deal_value = await session.scalar(
        select(func.avg(Lead.deal_value)).select_from(Lead)
        .where(and_(Lead.deal_value.isnot(None), Lead.deal_stage == DealStage.won))
    ) or 0

    # Таблица по исполнителям
    assignees_query = await session.execute(
        select(
            Lead.assigned_to,
            func.count(Lead.id).label("lead_count"),
            func.count().filter(Lead.deal_stage == DealStage.won).label("won_count"),
            func.avg(Lead.deal_value).filter(Lead.deal_stage == DealStage.won).label("avg_value"),
        )
        .where(Lead.assigned_to.isnot(None))
        .group_by(Lead.assigned_to)
        .order_by(func.count(Lead.id).desc())
    )

    assignees = []
    for row in assignees_query.all():
        assignee = row[0]
        count = row[1]
        won = row[2] or 0
        conv = round((won / count * 100), 1) if count > 0 else 0
        avg_val = round(row[3] or 0, 0)

        assignees.append({
            "name": assignee,
            "leads": count,
            "won": won,
            "conversion": conv,
            "avg_deal_value": int(avg_val),
        })

    return templates.TemplateResponse(
        request,
        "analytics.html",
        {
            "leads_by_source": leads_by_source,
            "leads_by_status": leads_by_status,
            "relevance_by_source": relevance_by_source,
            "trend_data": trend_data,
            "total": total,
            "today_count": today_count,
            "avg_relevance": round(avg_rel, 1),
            "avg_budget": round(avg_budget, 0),
            "platforms_comparison": platforms_comparison,
            "source_labels": SOURCE_LABELS,
            "is_authenticated": bool(request.cookies.get("session_token")),
            "conversion_rate": conversion_rate,
            "avg_deal_value": int(avg_deal_value),
            "won_count": won_count,
            "assignees": assignees,
        },
    )


@router.get("/analytics/export/csv")
async def analytics_export_csv(
    session: AsyncSession = Depends(get_session),
    auth: bool = Depends(require_auth),
):
    output = io.StringIO()
    writer = csv.writer(output)

    # Заголовок
    writer.writerow(["Lead Parser Analytics Report", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])

    # KPI
    total = await session.scalar(select(func.count()).select_from(Lead)) or 0
    today = datetime.now(timezone.utc).date()
    today_count = await session.scalar(
        select(func.count()).select_from(Lead)
        .where(func.date(Lead.created_at) == today)
    ) or 0
    avg_rel = await session.scalar(
        select(func.avg(Lead.relevance_score)).select_from(Lead)
        .where(Lead.relevance_score.isnot(None))
    ) or 0
    avg_budget = await session.scalar(
        select(func.avg(Lead.budget)).select_from(Lead)
        .where(Lead.budget.isnot(None))
    ) or 0

    writer.writerow(["KPI Summary"])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Leads", total])
    writer.writerow(["Today", today_count])
    writer.writerow(["Avg Relevance (%)", round(avg_rel, 1)])
    writer.writerow(["Avg Budget (₽)", round(avg_budget, 0)])
    writer.writerow([])

    # Сравнение платформ
    writer.writerow(["Platform Comparison"])
    writer.writerow(["Source", "Total Leads", "Avg Relevance (%)", "Avg Budget (₽)", "Leads/Day", "High Relevance (%)"])

    for source in ["fl", "habr", "kwork", "telegram"]:
        count = await session.scalar(
            select(func.count()).select_from(Lead).where(Lead.source == source)
        ) or 0

        if count > 0:
            avg_rel_src = await session.scalar(
                select(func.avg(Lead.relevance_score)).select_from(Lead)
                .where(and_(Lead.source == source, Lead.relevance_score.isnot(None)))
            ) or 0

            avg_budget_src = await session.scalar(
                select(func.avg(Lead.budget)).select_from(Lead)
                .where(and_(Lead.source == source, Lead.budget.isnot(None)))
            ) or 0

            high_relevance = await session.scalar(
                select(func.count()).select_from(Lead)
                .where(and_(Lead.source == source, Lead.relevance_score >= 80))
            ) or 0

            min_created = await session.scalar(
                select(func.min(Lead.created_at)).select_from(Lead).where(Lead.source == source)
            )
            max_created = await session.scalar(
                select(func.max(Lead.created_at)).select_from(Lead).where(Lead.source == source)
            )

            days_active = 1
            if min_created and max_created:
                days_active = max(1, (max_created - min_created).days + 1)

            leads_per_day = round(count / days_active, 1) if days_active > 0 else 0
            high_rel_percent = round((high_relevance / count * 100), 0) if count > 0 else 0

            writer.writerow([
                SOURCE_LABELS.get(source, source),
                count,
                round(avg_rel_src, 1),
                round(avg_budget_src, 0),
                leads_per_day,
                int(high_rel_percent),
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analytics_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
    )


@router.get("/{lead_id}/actions")
async def get_lead_actions(
    lead_id: int,
    session: AsyncSession = Depends(get_session),
    auth=Depends(require_auth),
):
    actions = await session.scalars(
        select(LeadAction)
        .where(LeadAction.lead_id == lead_id)
        .order_by(LeadAction.changed_at.desc())
    )

    actions_list = [
        {
            "id": a.id,
            "action_type": a.action_type,
            "old_value": a.old_value,
            "new_value": a.new_value,
            "changed_by": a.changed_by,
            "changed_at": a.changed_at.isoformat(),
            "description": a.description,
        }
        for a in actions
    ]

    return JSONResponse({"actions": actions_list})


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth=Depends(require_auth),
):
    body = await request.json()
    new_status = body.get("status")

    if not new_status or new_status not in Status.__members__:
        return JSONResponse({"error": "Invalid status"}, status_code=400)

    lead = await session.get(Lead, lead_id)
    if not lead:
        return JSONResponse({"error": "Lead not found"}, status_code=404)

    old_status = lead.status
    lead.status = new_status

    # Логируем действие
    action = LeadAction(
        lead_id=lead_id,
        action_type="status_change",
        old_value=old_status,
        new_value=new_status,
        changed_by="admin",
    )
    session.add(action)
    await session.commit()

    return JSONResponse({"status": new_status, "id": lead_id})


@router.patch("/{lead_id}/assign")
async def assign_lead(
    lead_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth=Depends(require_auth),
):
    body = await request.json()
    assigned_to = body.get("assigned_to")

    lead = await session.get(Lead, lead_id)
    if not lead:
        return JSONResponse({"error": "Lead not found"}, status_code=404)

    old_assigned = lead.assigned_to
    lead.assigned_to = assigned_to if assigned_to else None

    action = LeadAction(
        lead_id=lead_id,
        action_type="assigned",
        old_value=old_assigned,
        new_value=assigned_to or "unassigned",
        changed_by="admin",
    )
    session.add(action)
    await session.commit()

    return JSONResponse({"assigned_to": lead.assigned_to, "id": lead_id})


@router.patch("/{lead_id}/deal-stage")
async def update_deal_stage(
    lead_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth=Depends(require_auth),
):
    body = await request.json()
    new_stage = body.get("deal_stage")

    if not new_stage or new_stage not in DealStage.__members__:
        return JSONResponse({"error": "Invalid deal stage"}, status_code=400)

    lead = await session.get(Lead, lead_id)
    if not lead:
        return JSONResponse({"error": "Lead not found"}, status_code=404)

    old_stage = lead.deal_stage
    lead.deal_stage = new_stage

    action = LeadAction(
        lead_id=lead_id,
        action_type="deal_stage_change",
        old_value=old_stage,
        new_value=new_stage,
        changed_by="admin",
    )
    session.add(action)
    await session.commit()

    return JSONResponse({"deal_stage": new_stage, "id": lead_id})


@router.patch("/{lead_id}/deal-value")
async def update_deal_value(
    lead_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    auth=Depends(require_auth),
):
    body = await request.json()
    deal_value = body.get("deal_value")

    if deal_value is not None and not isinstance(deal_value, int):
        return JSONResponse({"error": "Deal value must be integer"}, status_code=400)

    lead = await session.get(Lead, lead_id)
    if not lead:
        return JSONResponse({"error": "Lead not found"}, status_code=404)

    old_value = lead.deal_value
    lead.deal_value = deal_value

    action = LeadAction(
        lead_id=lead_id,
        action_type="deal_value_change",
        old_value=str(old_value) if old_value else None,
        new_value=str(deal_value) if deal_value else "cleared",
        changed_by="admin",
    )
    session.add(action)
    await session.commit()

    return JSONResponse({"deal_value": lead.deal_value, "id": lead_id})


@router.post("/lead/{lead_id}/status")
async def update_status(
    lead_id: int,
    status: str = Form(...),
    session: AsyncSession = Depends(get_session),
    auth=Depends(require_auth),
):
    lead = await session.get(Lead, lead_id)
    if lead and status in Status.__members__:
        old_status = lead.status
        lead.status = status

        # Логируем действие
        action = LeadAction(
            lead_id=lead_id,
            action_type="status_change",
            old_value=old_status,
            new_value=status,
            changed_by="admin",
        )
        session.add(action)
        await session.commit()
    return RedirectResponse(f"/leads/", status_code=303)


def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "0.0.0.0"


def contains_url(text: str) -> bool:
    url_pattern = r'(https?://|www\.|ftp://)'
    return bool(re.search(url_pattern, text, re.IGNORECASE))


async def can_use_demo(ip: str, session: AsyncSession) -> bool:
    demo_user = await session.scalar(
        select(DemoUser).where(DemoUser.ip_address == ip)
    )
    if not demo_user:
        return True
    now = datetime.now(timezone.utc)
    return (now - demo_user.used_at) >= timedelta(days=1)


@router.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request):
    return templates.TemplateResponse(
        request,
        "demo.html",
        {"is_authenticated": bool(request.cookies.get("session_token"))},
    )


@router.post("/demo/analyze")
async def demo_analyze(
    request: Request,
    text: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    ip = get_client_ip(request)

    text = text.strip()[:1000]
    if not text or len(text) < 10:
        return JSONResponse(
            {"error": "Текст должен быть от 10 до 1000 символов"},
            status_code=400
        )

    if contains_url(text):
        return JSONResponse(
            {"error": "Ссылки не допускаются. Пожалуйста, удалите URL и попробуйте снова"},
            status_code=400
        )

    can_use = await can_use_demo(ip, session)
    if not can_use:
        return JSONResponse(
            {"error": "Вы уже использовали демо. Попробуйте завтра"},
            status_code=429
        )

    analysis = await analyze_lead(
        source="demo",
        title="Демо-анализ",
        text=text,
        budget=None
    )

    if not analysis:
        return JSONResponse(
            {"error": "Ошибка анализа. Попробуйте позже"},
            status_code=500
        )

    demo_user = await session.scalar(
        select(DemoUser).where(DemoUser.ip_address == ip)
    )
    if demo_user:
        demo_user.used_at = datetime.now(timezone.utc)
    else:
        demo_user = DemoUser(ip_address=ip)
        session.add(demo_user)
    await session.commit()

    return JSONResponse(analysis)


@router.get("/export/csv")
async def export_csv(
    source: str = Query(""),
    status: str = Query(""),
    search: str = Query(""),
    min_relevance: int = Query(0, ge=0, le=100),
    session: AsyncSession = Depends(get_session),
):
    query = select(Lead)
    filters = []
    if source:
        filters.append(Lead.source == source)
    if status:
        filters.append(Lead.status == status)
    if search:
        filters.append(
            (Lead.title.ilike(f"%{search}%")) |
            (Lead.text.ilike(f"%{search}%"))
        )
    if min_relevance > 0:
        filters.append(Lead.relevance_score >= min_relevance)

    if filters:
        query = query.where(and_(*filters))

    leads = (await session.scalars(query.order_by(Lead.fetched_at.desc()))).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Source", "Title", "Budget", "Relevance", "Status", "Created", "Summary"
    ])

    for lead in leads:
        writer.writerow([
            lead.id,
            SOURCE_LABELS.get(lead.source, lead.source),
            lead.title or "",
            lead.budget or "",
            lead.relevance_score or "",
            lead.status,
            lead.created_at.isoformat() if lead.created_at else "",
            lead.summary or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"}
    )


@router.get("/export/json")
async def export_json(
    source: str = Query(""),
    status: str = Query(""),
    search: str = Query(""),
    min_relevance: int = Query(0, ge=0, le=100),
    session: AsyncSession = Depends(get_session),
):
    query = select(Lead)
    filters = []
    if source:
        filters.append(Lead.source == source)
    if status:
        filters.append(Lead.status == status)
    if search:
        filters.append(
            (Lead.title.ilike(f"%{search}%")) |
            (Lead.text.ilike(f"%{search}%"))
        )
    if min_relevance > 0:
        filters.append(Lead.relevance_score >= min_relevance)

    if filters:
        query = query.where(and_(*filters))

    leads = (await session.scalars(query.order_by(Lead.fetched_at.desc()))).all()

    data = []
    for lead in leads:
        data.append({
            "id": lead.id,
            "source": lead.source,
            "title": lead.title,
            "text": lead.text,
            "budget": lead.budget,
            "relevance_score": lead.relevance_score,
            "tags": lead.tags,
            "summary": lead.summary,
            "status": lead.status,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "source_url": lead.source_url,
        })

    return JSONResponse(data)
