# tests/test_bot_auth.py
from unittest.mock import MagicMock

from app.bot.auth import is_authorized


def test_authorized_user_returns_true() -> None:
    update = MagicMock()
    update.effective_user.id = 42

    assert is_authorized(update, 42) is True


def test_wrong_user_returns_false_and_logs(caplog) -> None:
    update = MagicMock()
    update.effective_user.id = 999

    with caplog.at_level("WARNING"):
        result = is_authorized(update, 42)

    assert result is False
    assert "999" in caplog.text


def test_no_effective_user_returns_false_and_logs(caplog) -> None:
    update = MagicMock()
    update.effective_user = None

    with caplog.at_level("WARNING"):
        result = is_authorized(update, 42)

    assert result is False
    assert "unauthorized" in caplog.text.lower()
