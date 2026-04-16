# ============================================================
# main.py — точка входа FastAPI приложения
# ============================================================
# Запуск: uvicorn main:app --reload --port 8001

import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from aiogram.types import Update

from config import settings
from database import engine
from api.public import router as public_router
from api.client import router as client_router
from api.webhook import router as webhook_router
from bot.platform_bot import bot as platform_bot, dp as platform_dp


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"BeautyCatalog API running [{settings.environment}]")
    print(f"Database: {settings.database_url.split('@')[-1]}")

    if settings.is_dev:
        # Локально: long polling (не нужен публичный URL)
        _poll_task = asyncio.create_task(
            platform_dp.start_polling(platform_bot, skip_updates=True)
        )
        print("Platform bot: polling started")
    else:
        # Продакшн: устанавливаем вебхук для платформенного бота
        platform_webhook_url = f"{settings.api_base_url}/v1/platform-webhook"
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{settings.platform_bot_token}/setWebhook",
                    json={"url": platform_webhook_url},
                )
                ok = r.json().get("ok", False)
                print(f"Platform bot: webhook {'set' if ok else 'FAILED'} -> {platform_webhook_url}")
        except Exception as e:
            print(f"Platform bot: webhook error: {e}")

    yield

    # Завершение — закрываем соединения
    if settings.is_dev:
        try:
            _poll_task.cancel()
            await _poll_task
        except Exception:
            pass
    else:
        # Снимаем вебхук при остановке
        try:
            async with httpx.AsyncClient(verify=False, timeout=5) as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.platform_bot_token}/deleteWebhook"
                )
        except Exception:
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


@app.post("/v1/platform-webhook", tags=["Webhook"])
async def platform_webhook(request: Request):
    """Вебхук для платформенного бота (используется в продакшне)."""
    update_data = await request.json()
    update = Update.model_validate(update_data)
    await platform_dp.feed_update(platform_bot, update)
    return {"ok": True}


@app.api_route("/health", methods=["GET", "HEAD"], tags=["System"])
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
