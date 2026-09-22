import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
    YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./speakbuddy.db"
    )
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    LLM_MODEL: str = "yandexgpt-lite/latest"
    LLM_MAX_TOKENS: int = 200

    FREE_DAILY_LIMIT: int = 10
    PREMIUM_STARS_PRICE: int = 1250

    def __init__(self) -> None:
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN must be set in .env")
        if not self.YANDEX_API_KEY:
            raise ValueError("YANDEX_API_KEY must be set in .env")
        if not self.YANDEX_FOLDER_ID:
            raise ValueError("YANDEX_FOLDER_ID must be set in .env")

    @property
    def get_telegram_token(self) -> str:
        return self.TELEGRAM_TOKEN


# Initialize config on import
_config = Config()
