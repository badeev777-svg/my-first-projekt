from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    MODEL: str = "anthropic/claude-sonnet-4-6"
    MAX_TOKENS: int = 14000

    # Branding — override in .env for white-label deployments
    AGENT_NAME: str = "Нейро-Маркетолог"
    AGENT_INITIALS: str = "НМ"
    AGENCY_NAME: str = "Badeev Agency"
    AGENCY_TAGLINE: str = "AI-автоматизация бизнеса"
    CONTACT_LINK: str = "https://t.me/badeev777"
    WA_LINK: str = ""
    MAX_LINK: str = ""

    # White-label: только чат, без лендинга, автостарт
    CHAT_ONLY_MODE: bool = False

    # Unlock tokens for paid report sections (comma-separated)
    UNLOCK_TOKENS: str = ""

    # Telegram notifications
    TG_BOT_TOKEN: str = ""
    TG_CHAT_ID: str = ""

    # MAX messenger notifications
    MAX_BOT_TOKEN: str = ""
    MAX_USER_ID: int = 0

    # Admin dashboard
    ADMIN_LOGIN: str = "admin"
    ADMIN_PASSWORD: str = "changeme"
    ADMIN_URL: str = "http://localhost:8001/admin"

    def get_valid_tokens(self) -> set[str]:
        return {t.strip() for t in self.UNLOCK_TOKENS.split(",") if t.strip()}

    class Config:
        env_file = ".env"


settings = Settings()
