# Unified Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Упростить архитектуру с двух ботов до одного — убрать концепцию `AUDIENCE` env var, оставить единственный `TELEGRAM_TOKEN`, обновить цену на 1499 руб/мес, убрать годовой план.

**Architecture:** Весь код выбора аудитории (students/adults) уже работает через `user.audience` из БД — пользователь выбирает при регистрации. Нужно только убрать слой конфигурации, который дублировал этот выбор через env var.

**Tech Stack:** Python 3.10+, python-telegram-bot 21.1, SQLAlchemy 2.0, Alembic, OpenRouter API

---

## Files Changed

| File | Action |
|------|--------|
| `src/config.py` | Modify — убрать AUDIENCE/multi-token логику, обновить цену |
| `src/handlers/registration.py` | Modify — удалить мёртвую функцию `get_registration_handler()` |
| `.env.example` | Modify — переписать под один бот |
| `CREATE_BOTS_GUIDE.md` | Modify — переписать под один бот |
| `plan.md` | Modify — обновить статус задачи |

---

### Task 1: Упростить config.py

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Открой `src/config.py` и замени содержимое**

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./speakbuddy.db"
    )
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    LLM_MODEL: str = "anthropic/claude-3-5-sonnet"
    LLM_MAX_TOKENS: int = 200

    YUKASSA_API_KEY: str = os.getenv("YUKASSA_API_KEY", "")
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")

    FREE_DAILY_LIMIT: int = 10
    PREMIUM_MONTHLY_PRICE: int = 1499

    def __init__(self) -> None:
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN must be set in .env")
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY must be set in .env")

    @property
    def get_telegram_token(self) -> str:
        return self.TELEGRAM_TOKEN


# Initialize config on import
_config = Config()
```

- [ ] **Step 2: Проверь что импорт не сломан**

```bash
python -c "from src.config import Config; print('OK')"
```

Ожидаемый результат: `OK` (или ValueError если `.env` не настроен — это нормально, значит код работает).

- [ ] **Step 3: Commit**

```bash
git add src/config.py
git commit -m "refactor: simplify config to single bot token, price 1499/mo, remove yearly plan"
```

---

### Task 2: Удалить мёртвый код из registration.py

**Files:**
- Modify: `src/handlers/registration.py`

- [ ] **Step 1: Удали функцию `get_registration_handler()` в конце файла**

Найди и удали эти строки (в самом конце файла):

```python
def get_registration_handler():
    return ConversationHandler(
        entry_points=[],
        states={
            ASK_NAME: [],
            ASK_AGE: [],
            ASK_GOAL: [],
            LEVEL_TEST: [],
            TEST_SUMMARY: []
        },
        fallbacks=[]
    )
```

Функция никогда не вызывается — `main.py` строит `ConversationHandler` самостоятельно.

- [ ] **Step 2: Проверь что импорты в main.py не сломаны**

```bash
python -c "from src.handlers.registration import start_command, ask_name, ask_age, ask_audience, ask_goal, level_test_answer, finish_test; print('OK')"
```

Ожидаемый результат: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/handlers/registration.py
git commit -m "chore: remove dead get_registration_handler() function"
```

---

### Task 3: Обновить .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Замени содержимое `.env.example`**

```
# ============================================================================
# TELEGRAM BOT CONFIGURATION
# ============================================================================
# Get from: https://t.me/BotFather → /newbot → copy token
TELEGRAM_TOKEN=your_telegram_token_from_botfather

# For webhook mode (optional, production only)
WEBHOOK_URL=https://your-domain.com/webhook

# ============================================================================
# OPENROUTER API CONFIGURATION
# ============================================================================
# Get from: https://openrouter.io/account/keys
# Model used: anthropic/claude-3-5-sonnet
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# Development: SQLite (auto-created, no setup needed)
DATABASE_URL=sqlite+aiosqlite:///./speakbuddy.db

# Production: PostgreSQL
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/speakbuddy

# ============================================================================
# ENVIRONMENT & DEBUG
# ============================================================================
ENVIRONMENT=development
DEBUG=True

# ============================================================================
# PAYMENT CONFIGURATION (YuKassa)
# ============================================================================
# Get from: https://yookassa.ru → Settings → API keys
YUKASSA_API_KEY=your_yukassa_api_key_here
YUKASSA_SHOP_ID=your_shop_id_here

# ============================================================================
# HOW TO RUN
# ============================================================================
# 1. Apply migrations:  python -m alembic upgrade head
# 2. Start bot:         python -m src.main
```

- [ ] **Step 2: Обнови существующий `.env` вручную**

Открой `.env` и:
- Удали строки: `AUDIENCE=...`, `TELEGRAM_TOKEN_STUDENTS=...`, `TELEGRAM_TOKEN_ADULTS=...`
- Убедись что `TELEGRAM_TOKEN=...` заполнен корректным токеном

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "docs: update .env.example for single-bot architecture"
```

---

### Task 4: Переписать CREATE_BOTS_GUIDE.md

**Files:**
- Modify: `CREATE_BOTS_GUIDE.md`

- [ ] **Step 1: Замени содержимое `CREATE_BOTS_GUIDE.md`**

```markdown
# Гайд: Создание бота в BotFather

## Шаг 1: Создай бота

1. Открой Telegram → найди @BotFather → `/newbot`
2. Введи имя бота: `SpeakBuddy`
3. Введи username (должен заканчиваться на `bot`): например `speakbuddy_practice_bot`
4. Сохрани полученный токен:

```
TELEGRAM_TOKEN=1234567890:ABCDEFGhIjKlMnOpQrStUvWxYz-_ABCDEF
```

## Шаг 2: Заполни .env

```env
TELEGRAM_TOKEN=1234567890:ABCDEFGhIjKlMnOpQrStUvWxYz-_ABCDEF
OPENROUTER_API_KEY=sk-or-v1-your-key-here
DATABASE_URL=sqlite+aiosqlite:///./speakbuddy.db
ENVIRONMENT=development
DEBUG=True
YUKASSA_API_KEY=your_yukassa_api_key_here
YUKASSA_SHOP_ID=your_shop_id_here
```

## Шаг 3: Запусти

```bash
# Применить миграции БД
python -m alembic upgrade head

# Запустить бота
python -m src.main
```

## Шаг 4 (опционально): Настрой команды в BotFather

```
/setcommands → выбери своего бота → вставь:

start - начать регистрацию
new - новый диалог
profile - мой профиль
stats - статистика
premium - купить премиум
end - завершить диалог
```

## Важно

⚠️ **Никогда не публикуй токен в GitHub!**
- `.env` добавлен в `.gitignore` — не коммитится
- Если случайно опубликовал → удали бота в BotFather и создай нового
```

- [ ] **Step 2: Commit**

```bash
git add CREATE_BOTS_GUIDE.md
git commit -m "docs: rewrite CREATE_BOTS_GUIDE for single-bot setup"
```

---

### Task 5: Убрать годовую цену из payment.py

**Files:**
- Modify: `src/handlers/payment.py`

- [ ] **Step 1: Обнови текст команды `/premium` в `start_payment_command`**

Найди в `src/handlers/payment.py` (строки 22-33) и замени блок `text`:

```python
    text = f"""
💎 **Premium Subscription**

Unlimited daily messages + priority support

**Pricing:**
- Monthly: {Config.PREMIUM_MONTHLY_PRICE} ₽ (30 days)

Use /buy_monthly to purchase
    """
```

- [ ] **Step 2: Проверь что импорт Config не сломан**

```bash
python -c "from src.handlers.payment import start_payment_command; print('OK')"
```

Ожидаемый результат: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/handlers/payment.py
git commit -m "feat: remove yearly subscription, monthly only at 1499 RUB"
```

---

### Task 6: Обновить plan.md и проверить запуск

**Files:**
- Modify: `plan.md`

- [ ] **Step 1: Обнови статус в plan.md**

Найди строку:
```
- [ ] Разделение: Students vs Adults (промпты, сценарии, ценообразование)
```
Замени на:
```
- [x] Разделение: Students vs Adults — единый бот, audience по выбору при /start
```

Найди секцию "Следующие шаги" и удали пункты про два бота:
```
- [ ] **Шаг 1** — Создать двух ботов в BotFather
  - Читай: [CREATE_BOTS_GUIDE.md](CREATE_BOTS_GUIDE.md)
  - Сохрани токены

- [ ] **Шаг 2** — Заполнить .env
  - TELEGRAM_TOKEN_STUDENTS
  - TELEGRAM_TOKEN_ADULTS
  - ANTHROPIC_API_KEY (Claude)

- [ ] **Шаг 3** — Тестировать
  - `AUDIENCE=students python -m src.main`
  - `AUDIENCE=adults python -m src.main`
  - Проверить: /start → выбор аудитории → тест уровня → сценарии
```

Замени на:
```
- [ ] **Шаг 1** — Создать бота в BotFather
  - Читай: [CREATE_BOTS_GUIDE.md](CREATE_BOTS_GUIDE.md)
  - Сохрани токен в .env как TELEGRAM_TOKEN

- [ ] **Шаг 2** — Запустить и протестировать
  - `python -m alembic upgrade head`
  - `python -m src.main`
  - Проверить: /start → выбор аудитории → тест уровня → сценарии
```

- [ ] **Step 2: Проверь запуск бота**

```bash
python -m src.main
```

Ожидаемый результат: бот запускается без ошибок, в логах видно:
```
INFO - Initializing database...
INFO - ✅ Database initialized successfully
INFO - 🤖 Starting SpeakBuddy bot...
```

- [ ] **Step 3: Проверь полный flow в Telegram**

1. Открой бота в Telegram → `/start`
2. Введи имя → возраст → выбери аудиторию (Студент / Взрослый)
3. Выбери цель → пройди тест уровня
4. Убедись что `/new` показывает правильные сценарии для выбранной аудитории

- [ ] **Step 5: Commit**

```bash
git add plan.md
git commit -m "chore: update plan.md — mark student/adult split done, single-bot next steps"
```

---

### Task 7: Получить GROQ_API_KEY и подключить голос

**Статус:** БЛОКИРОВКА — сайт console.groq.com не открывается через Stytch magic link / редирект завис.

**Что нужно сделать вручную:**
- [ ] Открыть `console.groq.com` в **Firefox или Edge** (Chrome не работает)
- [ ] Войти через **Continue with GitHub** (не email — email использует Stytch и зависает)
- [ ] Слева: **API Keys** → **Create API Key**
- [ ] Скопировать ключ (`gsk_...`)
- [ ] Добавить в `.env`: `GROQ_API_KEY=gsk_твой_ключ`
- [ ] `pip install groq edge-tts` (если ещё не установлено)
- [ ] Запустить бота: `python -m src.main`
- [ ] Проверить: отправить голосовое → бот должен распознать и ответить

**Команды бота после подключения:**
- `/voice` — включить голосовой режим (ответы голосом)
- `/text` — вернуться к тексту
