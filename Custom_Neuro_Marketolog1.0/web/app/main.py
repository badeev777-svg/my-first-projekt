from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.config import settings
from app.routers.chat import router as chat_router
from app.routers.chat2 import router as arch_router
from app.routers.chat3 import router as sales_router
from app.routers.admin import router as admin_router
from app import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init()
    yield


app = FastAPI(title="custom_neuro_marketolog", docs_url=None, redoc_url=None, lifespan=lifespan)

app.include_router(chat_router)
app.include_router(arch_router)
app.include_router(sales_router)
app.include_router(admin_router)

_STATIC = Path(__file__).parent.parent / "static"
_TEMPLATES = Path(__file__).parent.parent / "templates"

app.mount("/static", StaticFiles(directory=_STATIC), name="static")
templates = Jinja2Templates(directory=_TEMPLATES)


@app.get("/api/brand")
async def brand():
    return {
        "agent_name": settings.AGENT_NAME,
        "agent_initials": settings.AGENT_INITIALS,
        "agency_name": settings.AGENCY_NAME,
        "agency_tagline": settings.AGENCY_TAGLINE,
        "contact_link": settings.CONTACT_LINK,
        "wa_link": settings.WA_LINK,
        "max_link": settings.MAX_LINK,
        "chat_only": settings.CHAT_ONLY_MODE,
    }


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "site_title": f"{settings.AGENT_NAME} — {settings.AGENCY_NAME}",
        "agent_name": settings.AGENT_NAME,
        "agent_initials": settings.AGENT_INITIALS,
        "agency_name": settings.AGENCY_NAME,
        "agency_tagline": settings.AGENCY_TAGLINE,
        "contact_link": settings.CONTACT_LINK,
        "wa_link": settings.WA_LINK,
        "max_link": settings.MAX_LINK,
        "chat_only": settings.CHAT_ONLY_MODE,
    })


@app.get("/analytics")
async def analytics(request: Request):
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "site_title": f"Аналитика — {settings.AGENCY_NAME}",
        "agency_name": settings.AGENCY_NAME,
    })


@app.get("/architect")
async def architect(request: Request):
    return templates.TemplateResponse("architect.html", {
        "request": request,
        "site_title": f"AI-Архитектор — {settings.AGENCY_NAME}",
        "agency_name": settings.AGENCY_NAME,
        "contact_link": settings.CONTACT_LINK,
    })


@app.get("/sales")
async def sales(request: Request):
    return templates.TemplateResponse("sales.html", {
        "request": request,
        "site_title": f"AI Sales Engineer — {settings.AGENCY_NAME}",
        "agency_name": settings.AGENCY_NAME,
        "contact_link": settings.CONTACT_LINK,
    })
