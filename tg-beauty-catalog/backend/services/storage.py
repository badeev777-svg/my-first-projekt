# ============================================================
# services/storage.py — загрузка файлов в Cloudflare R2
# ============================================================
# R2 совместим с S3 API, используем boto3.
# Ключ объекта = путь внутри бакета: masters/{id}/services/{svc_id}/{uuid}.jpg
# Публичный URL = r2_public_url + "/" + ключ

import uuid

import boto3
from botocore.client import Config

from config import settings


def is_configured() -> bool:
    return bool(
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_public_url
    )


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def make_key(folder: str, ext: str = "jpg") -> str:
    return f"{folder}/{uuid.uuid4().hex}.{ext}"


def upload_bytes(data: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Загружает байты в R2, возвращает публичный URL."""
    _client().put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"{settings.r2_public_url.rstrip('/')}/{key}"


def delete_object(key: str) -> None:
    """Удаляет объект из R2. key = часть URL после домена."""
    _client().delete_object(Bucket=settings.r2_bucket_name, Key=key)


def url_to_key(url: str) -> str:
    """Извлекает ключ объекта из публичного URL."""
    base = settings.r2_public_url.rstrip("/")
    return url.removeprefix(base).lstrip("/")
