# Lead Parser — Project Context

## Что это

Веб-приложение для автоматического сбора заявок на разработку сайтов из Telegram, FL.ru и Habr Freelance. Фильтрует по ключевым словам и бюджету, сохраняет в SQLite, отправляет уведомления в Telegram.

## Стек

- **Backend**: FastAPI, SQLAlchemy, APScheduler
- **БД**: SQLite
- **Парсинг**: Telethon (Telegram userbot), RSS (FL.ru, Habr Freelance)
- **Auth**: JWT + Telegram OAuth
- **Запуск**: Docker / `start.bat`

## Структура

```
app/          — FastAPI приложение (роуты, модели, сервисы)
data/         — SQLite БД и данные
tests/        — тесты
main.py       — точка входа
scrape_contacts.py — скрапер контактов веб-студий
```

## Запуск

```bash
# Локально
pip install -r requirements_scraper.txt
python main.py

# Docker
docker build -t lead-parser .
docker run -p 8000:8000 lead-parser
```

## Важные файлы

- [PLAN.md](PLAN.md) — текущий план разработки
- [SETUP_TELEGRAM_BOT.md](SETUP_TELEGRAM_BOT.md) — настройка Telegram бота
- [SETUP_ADMIN_PASSWORD.md](SETUP_ADMIN_PASSWORD.md) — настройка пароля админа
