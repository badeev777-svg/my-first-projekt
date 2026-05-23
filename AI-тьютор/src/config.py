import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    AUDIENCE: str = os.getenv("AUDIENCE", "adults").lower()
    TELEGRAM_TOKEN_STUDENTS: str = os.getenv("TELEGRAM_TOKEN_STUDENTS", "")
    TELEGRAM_TOKEN_ADULTS: str = os.getenv("TELEGRAM_TOKEN_ADULTS", "")
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./speakbuddy.db"
    )
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 200

    YUKASSA_API_KEY: str = os.getenv("YUKASSA_API_KEY", "")
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")

    FREE_DAILY_LIMIT: int = 10
    PREMIUM_MONTHLY_PRICE: int = 2499
    PREMIUM_YEARLY_PRICE: int = 24990

    def __init__(self) -> None:
        token = self._get_telegram_token()
        if not token:
            raise ValueError(
                "TELEGRAM_TOKEN must be set in .env, or use AUDIENCE=students/adults with "
                "TELEGRAM_TOKEN_STUDENTS and TELEGRAM_TOKEN_ADULTS"
            )
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY must be set in .env")

    def _get_telegram_token(self) -> str:
        if self.AUDIENCE == "students":
            return self.TELEGRAM_TOKEN_STUDENTS or self.TELEGRAM_TOKEN
        elif self.AUDIENCE == "adults":
            return self.TELEGRAM_TOKEN_ADULTS or self.TELEGRAM_TOKEN
        return self.TELEGRAM_TOKEN

    @property
    def get_telegram_token(self) -> str:
        return self._get_telegram_token()


# Initialize config on import
_config = Config()
