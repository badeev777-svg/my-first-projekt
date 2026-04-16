# ============================================================
# services/crypto.py — шифрование/дешифрование токенов ботов
# ============================================================
# Метафора: сейф для токенов. bot_token хранится в БД
# зашифрованным — даже при утечке БД токены нельзя использовать.

from cryptography.fernet import Fernet
from config import settings


def get_cipher() -> Fernet:
    if not settings.fernet_key:
        raise RuntimeError("FERNET_KEY не задан в .env")
    return Fernet(settings.fernet_key.encode())


def encrypt_token(token: str) -> str:
    """Зашифровать токен бота перед сохранением в БД."""
    return get_cipher().encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Расшифровать токен для отправки запросов к Telegram API."""
    return get_cipher().decrypt(encrypted_token.encode()).decode()
