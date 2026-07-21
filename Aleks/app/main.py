# app/main.py
import logging
import os
from logging.handlers import RotatingFileHandler

from telegram.ext import Application

from app.bot.handlers import chat as chat_handler
from app.bot.handlers import confirm as confirm_handler
from app.bot.handlers import project as project_handler
from app.config import get_settings
from app.confirmation import ConfirmationBridge
from app.state import StateStore

LOG_FILE_PATH = os.environ.get("ALEKS_LOG_FILE", "aleks-agent.log")
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_FILE_BACKUP_COUNT = 3


def setup_logging(level: str) -> None:
    log_format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    logging.basicConfig(
        level=level.upper(),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(), file_handler],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    log = logging.getLogger(__name__)

    # claude_agent_sdk reads ANTHROPIC_API_KEY from the process environment.
    os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    state = StateStore(settings.db_path)
    confirmation_bridge = ConfirmationBridge(timeout_seconds=settings.confirmation_timeout_seconds)

    async def post_init(application: Application) -> None:
        await state.init()

    app = Application.builder().token(settings.telegram_bot_token).post_init(post_init).build()
    app.bot_data["settings"] = settings
    app.bot_data["state"] = state
    app.bot_data["confirmation_bridge"] = confirmation_bridge
    app.bot_data["project_locks"] = {}

    project_handler.register(app)
    confirm_handler.register(app)
    chat_handler.register(app)

    log.info("Aleks agent bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
