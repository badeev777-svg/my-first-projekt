# ============================================================
# services/storage.py — загрузка файлов в Supabase Storage
# ============================================================
# Бакет: beauty-catalog (PUBLIC)
# Публичный URL: {supabase_url}/storage/v1/object/public/beauty-catalog/{key}

import uuid

from supabase import create_client

from config import settings

BUCKET = "beauty-catalog"


def is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def _client():
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def make_key(folder: str, ext: str = "jpg") -> str:
    return f"{folder}/{uuid.uuid4().hex}.{ext}"


def upload_bytes(data: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Загружает байты в Supabase Storage, возвращает публичный URL."""
    _client().storage.from_(BUCKET).upload(
        path=key,
        file=data,
        file_options={"content-type": content_type},
    )
    return f"{settings.supabase_url}/storage/v1/object/public/{BUCKET}/{key}"


def delete_object(key: str) -> None:
    """Удаляет объект из бакета."""
    _client().storage.from_(BUCKET).remove([key])


def url_to_key(url: str) -> str:
    """Извлекает ключ объекта из публичного URL."""
    prefix = f"{settings.supabase_url}/storage/v1/object/public/{BUCKET}/"
    return url.removeprefix(prefix)
