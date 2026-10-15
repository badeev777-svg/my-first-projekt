from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cloudru_api_key: str
    # Пустой код пустил бы любого: compare_digest(b"", b"") истинно.
    access_code: str = Field(min_length=8)
    cloudru_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    embed_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    chat_model: str = "ai-sage/GigaChat3.5-432B-A28B-Reasoning"
    session_ttl_seconds: int = 3600
    max_files: int = 10
    max_file_mb: int = 20
    max_questions: int = 60
    # ~300 стр. текста. Замер 2026-10-15: эмбеддинги cloud.ru ~1 с на 100 фрагментов, т.е. ~15 с —
    # далеко от таймаута прокси; лимит ограничивает расход и память сессии.
    max_chunks_per_file: int = 1500
    http_timeout_seconds: float = 60.0
    cookie_secure: bool = True
