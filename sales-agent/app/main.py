import logging
import secrets
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.catalog import load_catalog
from app.config import Settings
from app.handoff import Channel, StubChannel
from app.llm_client import LLM, CloudRuLLM, LLMError
from app.pipeline import Pipeline
from app.skills import load_skills
from app.state import State
from app.store import AlreadyProcessing, Conversation, Store

STATIC = Path(__file__).resolve().parent / "static"
LOCAL_HOSTS = {"127.0.0.1", "::1"}
COOKIE = "sid"


class ChatIn(BaseModel):
    conversation_id: str = Field(max_length=64)
    client_message_id: str = Field(min_length=1, max_length=64)
    text: str


class ConvIn(BaseModel):
    conversation_id: str = Field(max_length=64)


class RateLimiter:
    def __init__(self, per_minute: int):
        self._limit = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True


def require_local(request: Request) -> None:
    # Только адрес TCP-соединения: X-Forwarded-For подделывается, поэтому uvicorn запускается без --proxy-headers.
    host = request.client.host if request.client else ""
    if host not in LOCAL_HOSTS:
        raise HTTPException(403, "Админка доступна только с этого компьютера")


def create_app(settings: Settings | None = None, *, llm: LLM | None = None,
               channel: Channel | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = settings or Settings()
    if llm is None and not settings.demo:
        llm = CloudRuLLM(settings)
    store = Store(settings.db_path)
    catalog = load_catalog(Path(settings.content_dir))
    key = settings.cloudru_api_key.strip()
    pipeline = Pipeline(store, catalog, load_skills(Path(settings.skills_dir)), llm, channel or StubChannel(),
                        [key] if key else [])
    limiter = RateLimiter(settings.rate_limit_per_minute)

    app = FastAPI(title="sales-agent", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store

    def session(request: Request, response: Response) -> str:
        sid = request.cookies.get(COOKIE)
        if not sid:
            sid = secrets.token_urlsafe(24)
            response.set_cookie(COOKIE, sid, httponly=True, samesite="strict", secure=settings.cookie_secure,
                                max_age=30 * 24 * 3600)
        return sid

    def own(cid: str, sid: str) -> Conversation:
        conv = store.get_conversation(cid)
        if conv is None or not secrets.compare_digest(conv.session_id, sid):
            raise HTTPException(403, "Нет доступа к этому диалогу")
        return conv

    def start(sid: str) -> dict:
        conv = store.create_conversation(sid)
        return {"conversation_id": conv.id, "state": conv.state.value, "demo": pipeline.demo,
                "catalog_version": catalog.version}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.post("/api/conversations")
    def new_conversation(sid: str = Depends(session)) -> dict:
        return start(sid)

    @app.post("/api/chat")
    def chat(body: ChatIn, sid: str = Depends(session)) -> dict:
        text = body.text.strip()
        if not text or len(text) > settings.max_message_chars:
            raise HTTPException(422, f"Сообщение должно быть от 1 до {settings.max_message_chars} символов")
        conv = own(body.conversation_id, sid)
        if not limiter.allow(sid):
            raise HTTPException(429, "Слишком много сообщений. Подождите минуту и нажмите «Повторить».")
        try:
            return pipeline.handle(conv, body.client_message_id, text)
        except AlreadyProcessing:
            raise HTTPException(409, "Это сообщение ещё обрабатывается")
        except LLMError:
            raise HTTPException(503, "Модель не ответила. Нажмите «Повторить» — сообщение не потеряется.")

    @app.post("/api/reset")
    def reset(body: ConvIn, sid: str = Depends(session)) -> dict:
        own(body.conversation_id, sid)
        return start(sid)

    @app.post("/api/stop")
    def stop(body: ConvIn, sid: str = Depends(session)) -> dict:
        conv = own(body.conversation_id, sid)
        store.set_stopped(conv.id, True)
        return {"conversation_id": conv.id, "stopped": True}

    @app.get("/admin", dependencies=[Depends(require_local)])
    def admin_page() -> FileResponse:
        return FileResponse(STATIC / "admin.html")

    @app.get("/api/admin/data", dependencies=[Depends(require_local)])
    def admin_data() -> dict:
        return {
            "leads": store.list_leads(), "handoffs": store.list_handoffs(),
            "human_pending": [c.id for c in store.conversations_in(State.HUMAN_PENDING)],
            "catalog_version": catalog.version, "demo": pipeline.demo,
            "consent_approved": catalog.policy.consent_approved,
        }

    @app.post("/api/admin/release", dependencies=[Depends(require_local)])
    def release(body: ConvIn) -> dict:
        conv = store.get_conversation(body.conversation_id)
        if conv is None or conv.state is not State.HUMAN_PENDING:
            raise HTTPException(409, "Диалог не ждёт человека")
        store.set_state(conv.id, State.DISCOVERY)  # единственный выход из human_pending — решение человека
        return {"conversation_id": conv.id, "state": State.DISCOVERY.value}

    return app
