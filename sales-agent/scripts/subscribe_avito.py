"""Один раз подписывает Avito на вебхук: uv run python scripts/subscribe_avito.py https://домен"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.avito_bot import AvitoClient  # noqa: E402
from app.config import Settings  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: subscribe_avito.py https://<домен>")
    s = Settings()
    client = AvitoClient(s.avito_client_id.strip(), s.avito_client_secret.strip(), s.avito_user_id.strip())
    # Секрет — часть адреса, поэтому сам адрес не печатаем.
    client.subscribe(f"{sys.argv[1].rstrip('/')}/api/avito/webhook/{s.avito_webhook_secret.strip()}")
    print("avito webhook subscribed")


if __name__ == "__main__":
    main()
