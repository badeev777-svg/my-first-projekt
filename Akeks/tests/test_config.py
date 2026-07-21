from app.config import Settings


def test_settings_parses_projects_mapping_from_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "42")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("PROJECTS", '{"akeks": "/root/projects/Akeks"}')

    settings = Settings(_env_file=None)

    assert settings.telegram_bot_token == "test-token"
    assert settings.allowed_user_id == 42
    assert settings.projects == {"akeks": "/root/projects/Akeks"}
    assert settings.confirmation_timeout_seconds == 600.0
    assert settings.db_path == "state.db"
