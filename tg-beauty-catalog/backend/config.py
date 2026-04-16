# ============================================================
# config.py — загрузка переменных окружения из .env
# ============================================================
# Метафора: это «приборная панель» приложения.
# Все настройки в одном месте. Остальные файлы берут отсюда.

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Supabase ---
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str

    # --- Telegram ---
    admin_telegram_user_id: int
    platform_bot_token: str

    # --- Шифрование токенов ботов мастеров ---
    fernet_key: str = ""

    # --- Cloudflare R2 ---
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "beauty-catalog"
    r2_public_url: str = ""

    # --- Приложение ---
    environment: str = "development"
    api_base_url: str = "http://localhost:8000"
    mini_app_base_url: str = ""

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"

    class Config:
        # Локально: .env рядом с папкой backend/ или на уровень выше
        # На Railway: переменные задаются в dashboard, .env не нужен
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Глобальный объект настроек — импортировать так:
#   from config import settings
settings = get_settings()
