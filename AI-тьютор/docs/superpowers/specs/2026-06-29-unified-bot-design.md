# SpeakBuddy — Unified Bot Design

**Date:** 2026-06-29  
**Status:** Approved (updated after expert review)

## Goal

Merge the two-bot architecture (AUDIENCE=students/adults) into a single Telegram bot with one token. Users select their audience during registration.

## What Changes

### `src/config.py`
- Remove: `AUDIENCE`, `TELEGRAM_TOKEN_STUDENTS`, `TELEGRAM_TOKEN_ADULTS`, `_get_telegram_token()`
- Keep: `TELEGRAM_TOKEN` (single field)
- Update: `PREMIUM_MONTHLY_PRICE = 1499`
- Remove: `PREMIUM_YEARLY_PRICE` — убираем годовой план полностью
- Update error message in `__init__` to reference only `TELEGRAM_TOKEN`

### `.env.example`
- Remove: `AUDIENCE`, `TELEGRAM_TOKEN_STUDENTS`, `TELEGRAM_TOKEN_ADULTS`
- Remove: section "HOW TO RUN DIFFERENT BOTS"
- Keep: `TELEGRAM_TOKEN`, `OPENROUTER_API_KEY`, `DATABASE_URL`, `ENVIRONMENT`, `DEBUG`, `YUKASSA_*`
- Update launch instructions to: `python -m src.main`

### `CREATE_BOTS_GUIDE.md`
- Rewrite: guide now covers creating ONE bot (not two)
- Fix: references `ANTHROPIC_API_KEY` — should be `OPENROUTER_API_KEY`

### `src/handlers/registration.py`
- Remove: dead `get_registration_handler()` function (returns empty ConversationHandler, never called)

### `plan.md`
- Mark "Разделение: Students vs Adults" as done
- Remove "Создать двух ботов в BotFather" from next steps

## What Stays the Same

Everything else already supports the unified architecture:

| Component | Already works |
|-----------|--------------|
| `registration.py` | ASK_AUDIENCE step saves user.audience |
| `dialog.py` | Branches scenario keyboard by user.audience |
| `system_prompts.py` | Routes prompts by audience + level |
| `models.py` | User.audience field exists |
| `main.py` | All handlers registered including ASK_AUDIENCE |
| `alembic/003_add_audience.py` | Migration exists |

## Migration Step (before deploy)

```bash
python -m alembic upgrade head
```

Required if migration 003 hasn't been applied yet. Adds `audience` column with default `'adults'`.

## ENV after change

```
TELEGRAM_TOKEN=...          # single token
OPENROUTER_API_KEY=...      # unchanged
DATABASE_URL=...            # unchanged
YUKASSA_API_KEY=...         # unchanged
YUKASSA_SHOP_ID=...         # unchanged
```

## User Action Required

Update existing `.env` file manually:
- Remove `AUDIENCE=...`
- Remove `TELEGRAM_TOKEN_STUDENTS=...`
- Remove `TELEGRAM_TOKEN_ADULTS=...`
- Ensure `TELEGRAM_TOKEN=...` is set

## Pricing

- Monthly: **1499 RUB** (updated from 2499)
- Yearly: **removed** — only monthly subscriptions offered
