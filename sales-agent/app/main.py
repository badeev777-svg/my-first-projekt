import logging
import secrets
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.catalog import load_catalog
from app.config import Settings
from app.handoff import Channel, StubChannel, TelegramChannel
from app.llm_client import LLM, CloudRuLLM, LLMError
from app.max_bot import (BUSY_REPLY, GREETING, LLM_DOWN_REPLY, RESTART_WORDS, SESSION_PREFIX, Incoming, MaxClient,
                         adapt_reply, parse_update)
from app.pipeline import Pipeline
from app.skills import load_skills
from app.state import State
from app.store import AlreadyProcessing, Conversation, Store

STATIC = Path(__file__).resolve().parent / "static"
LOCAL_HOSTS = {"127.0.0.1", "::1"}
LOCAL_HOST_NAMES = {"127.0.0.1", "localhost", "::1", "[::1]"}
COOKIE = "sid"
PURGE_INTERVAL_SECONDS = 24 * 3600
log = logging.getLogger("sales-agent")


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
    # Host проверяется против DNS rebinding: чужой сайт может указать своё имя на 127.0.0.1 и читать админку из браузера.
    if host not in LOCAL_HOSTS or _host_name(request.headers.get("host", "")) not in LOCAL_HOST_NAMES:
        raise HTTPException(403, "Админка доступна только с этого компьютера")


def _host_name(header: str) -> str:
    value = header.strip().lower()
    if value.startswith("["):
        end = value.find("]")
        return value[: end + 1] if end > 0 else value
    return value.split(":", 1)[0] if value.count(":") == 1 else value


def create_app(settings: Settings | None = None, *, llm: LLM | None = None,
               channel: Channel | None = None, max_client: MaxClient | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    # httpx на INFO пишет полный URL запроса, а в URL Bot API лежит токен.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = settings or Settings()
    if llm is None and not settings.demo:
        llm = CloudRuLLM(settings)
    store = Store(settings.db_path)
    catalog = load_catalog(Path(settings.content_dir))
    key = settings.cloudru_api_key.strip()
    if channel is None:
        token, chat = settings.notify_bot_token.strip(), settings.notify_chat_id.strip()
        channel = TelegramChannel(token, chat) if token and chat else StubChannel()
    max_token, max_secret = settings.max_bot_token.strip(), settings.max_webhook_secret.strip()
    if max_client is None and max_token and max_secret:
        max_client = MaxClient(max_token)
    pipeline = Pipeline(store, catalog, load_skills(Path(settings.skills_dir)), llm, channel,
                        [s for s in (key, settings.notify_bot_token.strip(), max_token) if s])
    limiter = RateLimiter(settings.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        stop = threading.Event()

        def purge_daily() -> None:
            while not stop.is_set():
                try:
                    removed = store.purge_expired(plain_days=settings.retention_plain_days,
                                                  contact_days=settings.retention_contact_days)
                    log.info("retention purge: removed %d conversations", removed)
                except Exception:
                    log.exception("retention purge failed")
                stop.wait(PURGE_INTERVAL_SECONDS)

        threading.Thread(target=purge_daily, name="retention-purge", daemon=True).start()
        yield
        stop.set()

    app = FastAPI(title="sales-agent", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.store = store
    app.state.channel = channel

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
        if store.saved_response(conv.id, body.client_message_id) is not None:
            return pipeline.handle(conv, body.client_message_id, text)  # повтор не тратит квоту
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

    def max_turn(client: MaxClient, msg: Incoming) -> None:
        sid = SESSION_PREFIX + msg.user_id
        try:
            conv = store.latest_conversation(sid)
            if msg.text is None or msg.text.strip().lower() in RESTART_WORDS:
                store.create_conversation(sid)
                client.send(msg.user_id, GREETING)
                return
            conv = conv or store.create_conversation(sid)
            if store.saved_response(conv.id, msg.mid) is not None:
                return  # MAX повторил доставку уже отвеченного сообщения
            if not limiter.allow(sid):
                client.send(msg.user_id, BUSY_REPLY)
                return
            try:
                reply = pipeline.handle(conv, msg.mid, msg.text)["reply"]
            except AlreadyProcessing:
                return
            except LLMError:
                client.send(msg.user_id, LLM_DOWN_REPLY)
                return
            if reply:
                client.send(msg.user_id, *adapt_reply(reply))
        except Exception:
            # Текст клиента в лог не пишем (ПДн).
            log.exception("max turn failed")

    @app.post("/api/max/webhook")
    def max_webhook(update: dict, tasks: BackgroundTasks,
                    x_max_bot_api_secret: str = Header(default="")) -> dict:
        if max_client is None or not max_secret:
            raise HTTPException(404)
        if not secrets.compare_digest(x_max_bot_api_secret.encode(), max_secret.encode()):
            raise HTTPException(403)
        msg = parse_update(update)
        if msg is None:
            # Только структура, без текста: по ней сверяем форму апдейта с документацией.
            log.info("max update skipped type=%s keys=%s message_keys=%s", update.get("update_type"),
                     sorted(update), sorted(update.get("message") or {}))
            return {"ok": True}
        # MAX ждёт ответ 30 с, а ход модели бывает дольше — отвечаем сразу, сообщение обрабатываем после.
        tasks.add_task(max_turn, max_client, msg)
        return {"ok": True}

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
        store.bump_epoch(conv.id)
        store.set_state(conv.id, State.DISCOVERY)  # единственный выход из human_pending — решение человека
        return {"conversation_id": conv.id, "state": State.DISCOVERY.value}

    return app
