from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Пустой ключ = режим DEMO: модель не вызывается, заявки никуда не уходят.
    cloudru_api_key: str = ""
    cloudru_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    chat_model: str = "ai-sage/GigaChat3.5-432B-A28B"
    llm_timeout_seconds: float = 20.0
    db_path: str = "data/sales.db"
    content_dir: str = "content"
    skills_dir: str = "skills"
    max_message_chars: int = 2000
    rate_limit_per_minute: int = 20
    cookie_secure: bool = False

    @property
    def demo(self) -> bool:
        return not self.cloudru_api_key.strip()
