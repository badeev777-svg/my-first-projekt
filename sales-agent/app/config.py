from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Пустой ключ = режим DEMO: модель не вызывается, заявки никуда не уходят.
    cloudru_api_key: str = ""
    cloudru_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    chat_model: str = "GigaChat/GigaChat-2-Max"
    llm_timeout_seconds: float = 20.0
    db_path: str = "data/sales.db"
    content_dir: str = "content"
    skills_dir: str = "skills"
    max_message_chars: int = 2000
    rate_limit_per_minute: int = 20
    cookie_secure: bool = False
    # Оба пустые = заявки уходят в канал-заглушку (только лог).
    notify_bot_token: str = ""
    notify_chat_id: str = ""
    # Оба пустые = канал MAX выключен (вебхук отвечает 404).
    max_bot_token: str = ""
    max_webhook_secret: str = ""
    # VK Callback API: ключ доступа сообщества, секретный ключ и строка подтверждения из настроек сервера.
    vk_group_token: str = ""
    vk_secret: str = ""
    vk_confirmation: str = ""
    # Avito Messenger API: client_id/secret и номер профиля; секрет вебхука — часть URL (подписи у Avito нет).
    avito_client_id: str = ""
    avito_client_secret: str = ""
    avito_user_id: str = ""
    avito_webhook_secret: str = ""
    # Сроки хранения из политики конфиденциальности бизнесгенератор.рф — менять только вместе с ней.
    retention_plain_days: int = 30
    retention_contact_days: int = 90

    @property
    def demo(self) -> bool:
        return not self.cloudru_api_key.strip()
