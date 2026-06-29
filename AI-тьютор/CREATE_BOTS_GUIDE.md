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
