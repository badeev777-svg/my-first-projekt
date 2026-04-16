# ============================================================
# main.py — точка входа FastAPI приложения
# ============================================================
# Запуск: uvicorn main:app --reload --port 8001

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from database import engine
from api.public import router as public_router
from api.client import router as client_router
from api.webhook import router as webhook_router
from bot.platform_bot import bot as platform_bot, dp as platform_dp


# Задача long-polling платформенного бота (работает в фоне вместе с сервером)
_poll_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poll_task

    # Запускаем платформенного бота (long polling)
    # В продакшне он будет работать через вебхук, здесь — polling для удобства разработки
    _poll_task = asyncio.create_task(
        platform_dp.start_polling(platform_bot, skip_updates=True)
    )

    print(f"BeautyCatalog API running [{settings.environment}]")
    print(f"Database: {settings.database_url.split('@')[-1]}")
    print(f"Platform bot: polling started")

    yield

    # Останавливаем бот и закрываем соединения при завершении
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass

    await platform_bot.session.close()
    await engine.dispose()
    print("Server stopped")


app = FastAPI(
    title="BeautyCatalog API",
    description="Платформа для мастеров красоты — запись, каталог, боты",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
)

# CORS — разрешаем запросы из Mini App (Telegram WebApp)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # в production заменить на конкретный домен Mini App
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(public_router,  prefix="/v1")
app.include_router(client_router,  prefix="/v1")
app.include_router(webhook_router, prefix="/v1")


@app.get("/health", tags=["System"])
async def health_check():
    """Проверка состояния сервера и БД."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "environment": settings.environment,
        "database": db_status,
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": "BeautyCatalog API", "docs": "/docs"}
