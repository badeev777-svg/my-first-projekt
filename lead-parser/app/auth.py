"""Simple password-based authentication."""
import os
import hashlib
import secrets

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

_valid_tokens: set[str] = set()


def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, stored: str) -> bool:
    """Compare hashes of both sides — stored can be plain text from .env."""
    return secrets.compare_digest(get_password_hash(plain), get_password_hash(stored))


def is_password_set() -> bool:
    return bool(ADMIN_PASSWORD)


def create_session_token() -> str:
    token = secrets.token_urlsafe(32)
    _valid_tokens.add(token)
    return token


def invalidate_session_token(token: str | None) -> None:
    if token:
        _valid_tokens.discard(token)


def is_valid_token(token: str | None) -> bool:
    if not token:
        return False
    return token in _valid_tokens
