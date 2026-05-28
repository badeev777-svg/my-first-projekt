"""Simple password-based authentication."""
import os
from functools import lru_cache
import secrets
import hashlib

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


@lru_cache
def get_password_hash(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return get_password_hash(plain) == hashed


def is_password_set() -> bool:
    """Check if admin password is configured."""
    return bool(ADMIN_PASSWORD)
