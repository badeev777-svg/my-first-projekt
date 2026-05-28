# Lead Parser

Автоматический сбор заявок на разработку и продвижение сайтов из Telegram, FL.ru и Habr Freelance.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Описание

Lead Parser — это веб-приложение для автоматического мониторинга и сбора заявок на разработку сайтов и продвижение из популярных источников:

- **Telegram каналы** (через userbot)
- **FL.ru** (RSS фид)
- **Habr Freelance** (RSS фид)

Приложение фильтрует заявки по ключевым словам и минимальному бюджету, сохраняет их в базу данных и отправляет уведомления в Telegram. Веб-интерфейс позволяет просматривать и управлять собранными лидами.

### Основные возможности

- 🔍 Автоматический сбор из 3 источников
- 🎯 Фильтрация по ключевым словам и бюджету
- 📱 Веб-интерфейс с фильтрами и пагинацией
- 📢 Уведомления в Telegram
- 🗄️ SQLite база данных
- ⏰ Планировщик задач (APScheduler)

### Технологии

- **Backend**: FastAPI, SQLAlchemy, APScheduler
- **Frontend**: Jinja2, Tailwind CSS
- **Парсинг**: Telethon, feedparser, httpx
- **База данных**: SQLite (aiosqlite)
- **Деплой**: Docker, uvicorn

## Скриншоты

![Главная страница](screenshots/index.png)
![Детали заявки](screenshots/lead.png)

## Быстрый старт

### Локальный запуск

#### 1. Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

#### 2. Настройка

```bash
cp .env.example .env
```

Заполни `.env`:

| Переменная | Где взять |
|---|---|
| `TG_API_ID` / `TG_API_HASH` | https://my.telegram.org/apps |
| `TG_PHONE` | Номер Telegram аккаунта (userbot) |
| `BOT_TOKEN` | Создать бота через @BotFather |
| `BOT_CHAT_ID` | Свой Telegram ID — узнать через @userinfobot |
| `TG_CHANNELS` | Список каналов через запятую (без @) |

#### 3. Запуск

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Открой браузер: http://localhost:8000

При первом запуске Telethon попросит ввести код из SMS — это нормально, сессия сохранится в `data/tg_session`.

### Демо-режим

Для демонстрации без настройки Telegram:

```bash
echo "DEMO_MODE=true" >> .env
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

В демо-режиме загружаются фейковые лиды и отключается планировщик сбора.

### Docker

```bash
docker build -t lead-parser .
docker run -p 8000:8000 --env-file .env lead-parser
```

## Развертывание

### Railway (бесплатно)

1. Создай аккаунт на [Railway](https://railway.app)
2. Подключи GitHub репозиторий
3. Добавь переменные окружения из `.env`
4. Деплой

### Render

1. Создай аккаунт на [Render](https://render.com)
2. Создай новый Web Service
3. Подключи GitHub
4. Укажи команду запуска: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Добавь переменные окружения

### VPS

```bash
# На сервере Ubuntu/Debian
git clone <repo> && cd lead-parser
pip install -e .
cp .env.example .env && nano .env

# Запуск через systemd или screen
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Структура проекта

```
lead-parser/
├── main.py              # точка входа, FastAPI + планировщик
├── pyproject.toml       # зависимости и конфигурация
├── Dockerfile           # контейнеризация
├── .env.example         # пример конфигурации
├── README.md            # документация
├── tests/               # тесты
│   └── test_collector.py
├── app/
│   ├── config.py        # настройки из .env
│   ├── database.py      # SQLAlchemy модели
│   ├── filter.py        # фильтрация по ключевым словам и бюджету
│   ├── collector.py     # оркестратор всех парсеров
│   ├── notifier.py      # Telegram-уведомления
│   ├── scrapers/
│   │   ├── fl_rss.py    # FL.ru RSS
│   │   ├── habr.py      # Habr Freelance RSS
│   │   └── telegram_poller.py  # Telethon userbot
│   └── web/
│       ├── routes.py    # FastAPI эндпоинты
│       └── templates/   # Jinja2 HTML-шаблоны
└── data/                # SQLite БД и Telethon сессия
```

## Конфигурация

### Переменные окружения

- `TG_API_ID` / `TG_API_HASH` — для Telegram userbot
- `TG_PHONE` — номер телефона для userbot
- `BOT_TOKEN` — токен Telegram бота для уведомлений
- `BOT_CHAT_ID` — ID чата для уведомлений
- `TG_CHANNELS` — каналы для мониторинга (через запятую)
- `KEYWORDS` — ключевые слова для фильтрации
- `MIN_BUDGET` — минимальный бюджет (0 = без ограничений)
- `POLL_INTERVAL_MINUTES` — интервал опроса источников
- `DEMO_MODE` — демо-режим (true/false)

## Тестирование

```bash
pip install -e ".[tests]"
pytest tests/
```

## Лицензия

MIT License. См. [LICENSE](LICENSE) для деталей.

## Автор

Бадеев Александр — разработчик веб-приложений и парсеров.

## План развития

- добавить страницу портфолио `/portfolio` на сайт
- добавить ссылку `Портфолио` в шапку сайта
- указать автора проекта на странице портфолио
- при необходимости добавить карточку проекта в главную страницу
- оформить коммит с этими изменениями

