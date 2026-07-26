import pytest
from pydantic import ValidationError

from app.config import Settings


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
