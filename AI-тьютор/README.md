# SpeakBuddy — Telegram Bot for English Conversation Practice

AI-powered Telegram bot for practicing English conversation with Claude AI. Features scenario-based dialogues, level testing, daily message limits, and premium subscription support.

## Quick Start

### 1. Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure
Copy `.env` and fill in your credentials:
```bash
cp .env .env.local
# Edit .env.local with your tokens and API keys
```

Required:
- `TELEGRAM_TOKEN` — from BotFather
- `ANTHROPIC_API_KEY` — from claude.ai
- `DATABASE_URL` — SQLite (dev) or PostgreSQL (prod)

### 3. Database
```bash
python -m alembic upgrade head
```

### 4. Run
```bash
python -m src.main
```

## Architecture

```
src/
├── main.py               # Bot orchestration
├── config.py             # Configuration
├── db/
│   ├── models.py         # SQLAlchemy models (User, Dialog, DailyLimits, Subscription, Payment)
│   └── database.py       # Async engine setup
├── services/
│   ├── claude.py         # Claude API integration
│   ├── limits.py         # Daily message limit enforcement
│   └── payment.py        # Payment processing
├── handlers/
│   ├── registration.py   # /start → level test (7 questions)
│   ├── dialog.py         # /new → scenario selection → dialogue
│   ├── profile.py        # /profile, /stats
│   └── payment.py        # /premium, /buy_monthly
└── prompts/
    └── scenarios.py      # System prompts for 6 scenarios × 6 levels
```

## Features

### Phase 1: Foundation ✅
- User registration with level testing (A1-C2 CEFR)
- 6 dialogue scenarios (small talk, job interview, business meeting, etc.)
- 10 messages/day limit for free users
- Conversation history stored in PostgreSQL
- Claude API integration with context awareness

### Phase 2: Payments ✅
- Telegram Stars support
- YuKassa payment gateway
- Premium subscription (monthly/yearly)
- Unlimited messages for premium users
- Webhook handling for payment confirmations

### Phase 3: Coming Soon
- Voice message support
- Advanced analytics
- Community leaderboards

## Development

### Add Migration
```bash
python -m alembic revision --autogenerate -m "description"
```

### Run Migration
```bash
python -m alembic upgrade head
```

### Revert Migration
```bash
python -m alembic downgrade -1
```

## Database Schema

**Users** — Telegram user profiles
**Dialogs** — Conversation sessions with message history
**DailyLimits** — Track daily message usage (free tier)
**Subscriptions** — Premium subscription records
**Payments** — Payment transaction log

## Environment Variables

```
TELEGRAM_TOKEN=...              # Telegram Bot API token
ANTHROPIC_API_KEY=...           # Claude API key
DATABASE_URL=...                # SQLAlchemy connection string
ENVIRONMENT=development         # development|production
DEBUG=True                       # Debug mode
YUKASSA_API_KEY=...            # YuKassa payment API key
YUKASSA_SHOP_ID=...            # YuKassa shop ID
```

## Commands

- `/start` — Register & test English level
- `/new` — Start new dialogue scenario
- `/end` — End current dialogue
- `/profile` — View your profile & stats
- `/stats` — Detailed usage statistics
- `/premium` — View premium subscription options
- `/buy_monthly` — Purchase 1-month premium

## Support

Questions? Issues? Open an issue on GitHub or contact @badeev777
