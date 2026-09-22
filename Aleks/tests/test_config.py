import os

import pytest
from pydantic import ValidationError

from app.config import Settings, configure_anthropic_env


def test_settings_parses_projects_mapping_from_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("PROJECTS", '{"aleks": "/root/projects/Aleks"}')

    settings = Settings(_env_file=None)

    assert settings.telegram_bot_token == "test-token"
    assert settings.allowed_user_id == 42
    assert settings.projects == {"aleks": "/root/projects/Aleks"}
    assert settings.confirmation_timeout_seconds == 600.0
    assert settings.db_path == "state.db"


def test_settings_raises_when_required_fields_missing(monkeypatch) -> None:
    monkeypatch.delenv("ALLOWED_USER_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_raises_when_allowed_user_id_not_positive(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_defaults_apply_when_only_required_fields_set(monkeypatch) -> None:
    monkeypatch.delenv("PROJECTS", raising=False)
    monkeypatch.delenv("CONFIRMATION_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    settings = Settings(_env_file=None)

    assert settings.projects == {}
    assert settings.confirmation_timeout_seconds == 600.0
    assert settings.db_path == "state.db"
    assert settings.log_level == "INFO"


def test_projects_root_defaults_to_root_user_projects(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = Settings(_env_file=None)

    assert settings.projects_root == "/root/user-projects"


def test_projects_root_overridable_via_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("PROJECTS_ROOT", "/srv/user-projects")
    settings = Settings(_env_file=None)

    assert settings.projects_root == "/srv/user-projects"


def test_agent_effort_and_max_turn_budget_default_to_unset(monkeypatch) -> None:
    monkeypatch.delenv("AGENT_EFFORT", raising=False)
    monkeypatch.delenv("MAX_TURN_BUDGET_USD", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = Settings(_env_file=None)

    assert settings.agent_effort is None
    assert settings.max_turn_budget_usd is None


def test_agent_effort_and_max_turn_budget_overridable_via_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("AGENT_EFFORT", "low")
    monkeypatch.setenv("MAX_TURN_BUDGET_USD", "1.5")
    settings = Settings(_env_file=None)

    assert settings.agent_effort == "low"
    assert settings.max_turn_budget_usd == 1.5


def test_skill_hunter_settings_default_to_empty_niches_and_owner_chat(monkeypatch) -> None:
    monkeypatch.delenv("SKILL_HUNTER_NICHES", raising=False)
    monkeypatch.delenv("SKILL_HUNTER_CHAT_ID", raising=False)
    monkeypatch.delenv("SKILL_HUNTER_HISTORY_PATH", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    settings = Settings(_env_file=None)

    assert settings.skill_hunter_niches == []
    assert settings.skill_hunter_chat_id == 42
    assert settings.skill_hunter_history_path == "skill_hunter_history.json"


def test_skill_hunter_niches_parsed_from_json_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SKILL_HUNTER_NICHES", '["Python/FastAPI", "Telegram-боты"]')

    settings = Settings(_env_file=None)

    assert settings.skill_hunter_niches == ["Python/FastAPI", "Telegram-боты"]


def test_skill_hunter_chat_id_overridable_independent_of_allowed_user(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SKILL_HUNTER_CHAT_ID", "999")

    settings = Settings(_env_file=None)

    assert settings.skill_hunter_chat_id == 999
    assert settings.allowed_user_id == 42


def test_configure_anthropic_env_blanks_api_key_when_proxy_base_url_set(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    settings = Settings(
        _env_file=None,
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="sk-ant-direct",
        anthropic_base_url="https://proxy.polza.ai",
        anthropic_auth_token="proxy-token",
    )

    configure_anthropic_env(settings)

    assert os.environ["ANTHROPIC_BASE_URL"] == "https://proxy.polza.ai"
    assert os.environ["ANTHROPIC_AUTH_TOKEN"] == "proxy-token"
    assert os.environ["ANTHROPIC_API_KEY"] == ""


def test_configure_anthropic_env_uses_direct_key_when_no_proxy(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        telegram_bot_token="t",
        allowed_user_id=42,
        anthropic_api_key="sk-ant-direct",
        anthropic_base_url="",
        anthropic_auth_token="",
    )

    configure_anthropic_env(settings)

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-direct"
