# SpeakBuddy — Development Guidelines

## Project Overview

**SpeakBuddy** — Telegram bot for conversational English practice with Claude AI.

**Tech Stack:** Python 3.10+, AsyncIO, SQLAlchemy 2.0, Alembic, Claude API, python-telegram-bot 21.1, SQLite/PostgreSQL

**Current Phase:** 2 (Payments integration — Telegram Stars + YuKassa)

**Completed:** Phase 1 (Foundation — users, dialogs, levels, daily limits)

---

## Code Style & Conventions

### Python
- **Async-first:** Use `async/await` for all I/O (database, HTTP, Telegram)
- **Type hints:** Required for function signatures
- **Imports:** Group by stdlib, third-party, local
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **No comments:** Code should be self-documenting; add comments only for WHY, not WHAT

### Database
- **SQLAlchemy 2.0** async syntax: `select()`, `await session.get()`, `await session.scalar()`
- **Models:** Always define relationships and foreign keys
- **Migrations:** Use Alembic; commit migration files alongside code
- **Queries:** Use `select()` with filters; avoid raw SQL

### Handlers
- **Telegram handlers:** Use `ConversationHandler` for multi-step flows
- **Callbacks:** Use `callback_data` for state machine transitions
- **Error handling:** Catch Telegram API errors; return user-friendly messages

---

## Project Structure

```
src/
├── main.py              # Entry point; bot initialization
├── config.py            # All config from .env
├── db/
│   ├── models.py        # SQLAlchemy ORM models
│   └── database.py      # Engine, session factory, init_db(), close_db()
├── services/
│   ├── claude.py        # Claude API calls (with history)
│   ├── limits.py        # Daily message limit logic
│   └── payment.py       # Payment processing (YuKassa, Telegram Stars)
├── handlers/
│   ├── registration.py  # /start → level test state machine
│   ├── dialog.py        # /new → dialogue with Claude
│   ├── profile.py       # /profile, /stats
│   └── payment.py       # /premium, /buy_monthly, webhooks
└── prompts/
    └── scenarios.py     # System prompts for each scenario+level combo
```

---

## Key Workflows

### Registration (`/start`)
1. Check if user exists in DB
2. If new: ASK_NAME → ASK_AGE → ASK_GOAL → 7-QUESTION LEVEL TEST
3. Score → assign level (A1-C2)
4. Create `User` in DB

### Dialogue (`/new`)
1. Show 6 scenario options
2. User picks → create `Dialog` with `scenario` and `level`
3. Generate opening message from Claude (system prompt + scenario opener)
4. On each user message:
   - Check daily limit (free: 10/day, premium: unlimited)
   - Load dialogue history from `Dialog.messages` JSON
   - Call Claude with full history
   - Append user + assistant messages to history
   - Save to DB
   - Increment daily counter

### Payment (`/premium` → `/buy_monthly`)
1. Create `Payment` record (status: pending)
2. Send YuKassa payment link to user
3. On webhook: verify signature → update `Payment` status → activate `premium_until`
4. Future message checks: if `User.premium_until > now()` → unlimited

---

## Testing Checklist (Before Commit)

- [ ] `python -m alembic upgrade head` — migrations apply cleanly
- [ ] `python -m pytest tests/` — all tests pass (if tests exist)
- [ ] Bot starts: `python -m src.main` (no exceptions)
- [ ] `/start` flow works (register new user, get level)
- [ ] `/new` → scenario selection works
- [ ] Message handling works + increments limit
- [ ] `/profile` shows real data
- [ ] Premium check: 11+ free messages → limit hit
- [ ] No hardcoded secrets in code (use .env)

---

## Dependencies & Updates

```
python-telegram-bot==21.1  # Telegram bot framework
anthropic==0.28.0          # Claude API
sqlalchemy==2.0.25         # ORM
asyncpg==0.29.0            # PostgreSQL async driver
aiosqlite==0.22.1          # SQLite async driver
alembic==1.13.1            # Database migrations
python-dotenv==1.0.0       # .env loading
```

**Notes:**
- Do NOT upgrade `sqlalchemy` past 2.0.x without async compatibility check
- `asyncpg` only needed if using PostgreSQL; SQLite uses `aiosqlite`
- Keep `python-telegram-bot==21.1` (v21+ has better async support)

---

## Common Tasks

### Add a new database field
1. Update model in `src/db/models.py`
2. Create migration: `python -m alembic revision --autogenerate -m "add field"`
3. Review generated migration
4. Test: `python -m alembic upgrade head`

### Add a new Telegram command
1. Create handler function in `src/handlers/`
2. Register in `src/main.py`: `app.add_handler(CommandHandler("cmd", handler_fn))`
3. Test: `/cmd` in bot

### Call Claude API
```python
from src.services.claude import get_claude_response

response = await get_claude_response(
    system_prompt="You are a tutor...",
    history=[{"role": "user", "content": "Hello"}],
    user_message="How are you?"
)
```

### Check user premium status
```python
from datetime import datetime

is_premium = user.premium_until and user.premium_until > datetime.utcnow()
```

---

## Known Limitations & TODOs

- Voice messages: Not yet implemented (Phase 3)
- Analytics: Basic stats only; no advanced insights (Phase 4)
- Error handling: Basic; should add retry logic for Claude API (Phase 3)
- Logging: Minimal; should add structured logging (Phase 4)

---

## Contact & Support

- **Repo:** [GitHub link]
- **Issues:** Use GitHub Issues for bugs/features
- **Author:** @badeev777
