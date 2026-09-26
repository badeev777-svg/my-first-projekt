import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.chunker import chunk_units
from app.cloudru import CloudRuClient, CloudRuError
from app.config import Settings
from app.extract import ExtractError, extract
from app.rag import NoDocuments
from app.rag import answer as rag_answer
from app.session_store import Session, SessionStore

log = logging.getLogger("rag-demo")

COOKIE = "sid"
PURGE_INTERVAL_SECONDS = 300
INDEX_HTML = Path(__file__).parent / "static" / "index.html"
SESSION_EXPIRED = "Сессия завершена, документы удалены. Загрузите их снова."


class LoginIn(BaseModel):
    code: str


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


def create_app(settings: Settings, client=None, store: SessionStore | None = None) -> FastAPI:
    client = client if client is not None else CloudRuClient(settings)
    # `is None`, не `or`: пустой SessionStore ложен из-за __len__.
    store = store if store is not None else SessionStore(settings.session_ttl_seconds)
    max_bytes = settings.max_file_mb * 1024 * 1024

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def purger():
            while True:
                await asyncio.sleep(PURGE_INTERVAL_SECONDS)
                if n := store.purge_expired():
                    log.info("purged %d expired sessions", n)

        task = asyncio.create_task(purger())
        yield
        task.cancel()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def reject_anonymous_upload(request: Request, call_next):
        # До разбора multipart: иначе Starlette уже спулит тело во временный файл.
        if request.url.path == "/api/upload" and store.get(request.cookies.get(COOKIE, "")) is None:
            return JSONResponse(status_code=401, content={"detail": SESSION_EXPIRED})
        return await call_next(request)

    @app.exception_handler(CloudRuError)
    async def cloud_error(request: Request, exc: CloudRuError):
        log.warning("cloud.ru error: %s", exc)
        return JSONResponse(status_code=503, content={"detail": "Сервис ИИ временно недоступен, попробуйте через минуту."})

    def current_session(sid: str | None = Cookie(default=None)) -> Session:
        session = store.get(sid) if sid else None
        if session is None:
            raise HTTPException(401, SESSION_EXPIRED)
        return session

    @app.get("/")
    def index():
        return FileResponse(INDEX_HTML)

    @app.post("/api/login")
    def login(body: LoginIn, response: Response):
        if not secrets.compare_digest(body.code.encode(), settings.access_code.encode()):
            raise HTTPException(401, "Неверный код доступа.")
        session = store.create()
        response.set_cookie(
            COOKIE, session.id, httponly=True, secure=settings.cookie_secure,
            samesite="strict", max_age=settings.session_ttl_seconds,
        )
        return {"ok": True}

    @app.get("/api/session")
    def session_info(session: Session = Depends(current_session)):
        return {"files": session.files, "questions_left": settings.max_questions - session.questions}

    @app.post("/api/upload")
    def upload(files: list[UploadFile] = File(...), session: Session = Depends(current_session)):
        added = []
        for f in files:
            name = f.filename or "без имени"
            if len(session.files) >= settings.max_files:
                raise HTTPException(400, f"Можно загрузить не больше {settings.max_files} файлов.")
            if name in session.files:
                raise HTTPException(400, f"Файл «{name}» уже загружен.")
            data = f.file.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise HTTPException(400, f"Файл «{name}» больше {settings.max_file_mb} МБ.")
            try:
                units = extract(name, data)
            except ExtractError as e:
                raise HTTPException(400, str(e)) from e
            chunks = chunk_units(units)
            if len(chunks) > settings.max_chunks_per_file:
                raise HTTPException(400, f"Файл «{name}» слишком большой для демо.")
            vectors = client.embed([c.text for c in chunks])
            store.add_document(session, name, chunks, vectors)
            log.info("document indexed: %d units, %d chunks", len(units), len(chunks))
            added.append({"file": name, "chunks": len(chunks)})
        return {"added": added, "files": session.files}

    @app.post("/api/ask")
    def ask(body: AskIn, session: Session = Depends(current_session)):
        if session.questions >= settings.max_questions:
            raise HTTPException(400, f"Лимит {settings.max_questions} вопросов на сессию исчерпан.")
        try:
            result = rag_answer(client, session, body.question)
        except NoDocuments as e:
            raise HTTPException(400, "Сначала загрузите документы.") from e
        session.questions += 1
        return {"answer": result.text, "sources": [asdict(s) for s in result.sources]}

    @app.delete("/api/session")
    def delete_session(response: Response, sid: str | None = Cookie(default=None)):
        if sid:
            store.delete(sid)
        response.delete_cookie(COOKIE)
        return {"ok": True}

    return app


def build() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    return create_app(Settings())
