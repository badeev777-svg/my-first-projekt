from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., description="Token from @BotFather")
    allowed_user_id: int = Field(..., ge=1, description="Telegram user id of the owner")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude Agent SDK (direct billing)")
    anthropic_base_url: str = Field(default="", description="Override base URL, e.g. Polza.ai proxy")
    anthropic_auth_token: str = Field(default="", description="Bearer token for anthropic_base_url proxy")
    model: str = Field(
        default="sonnet",
        description="Claude model alias for the Agent SDK (sonnet/opus/haiku). "
        "Left unset the CLI defaults to Opus, which is far more expensive per token.",
    )
    projects: dict[str, str] = Field(
        default_factory=dict,
        description="Project name -> absolute path on the VPS",
    )
    confirmation_timeout_seconds: float = Field(default=600.0, ge=1)
    run_turn_timeout_seconds: float = Field(
        default=1200.0,
        ge=1,
        description="Hard ceiling on a single run_turn() call, so a hung Agent "
        "SDK/subprocess call (e.g. the CLI never starting) can't block a turn "
        "forever with no user-visible feedback. Must stay well above "
        "confirmation_timeout_seconds since confirmation waits happen inside "
        "the same call.",
    )
    db_path: str = Field(default="state.db")
    projects_root: str = Field(
        default="/root/user-projects",
        description="Filesystem root under which dynamically-created projects "
        "(via the 'новый проект' chat trigger) get their own subfolder.",
    )
    log_level: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    return Settings()
