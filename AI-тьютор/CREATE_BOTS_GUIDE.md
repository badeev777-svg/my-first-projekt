# 🤖 Гайд: Создание двух ботов в BotFather

## Шаг 1: Откройте BotFather

1. Откройте Telegram
2. Найдите @BotFather и откройте чат
3. Нажмите `/start` или введите `/newbot`

---

## Шаг 2: Создайте первого бота (для Студентов)

### Диалог с BotFather:

```
BotFather: Alright, a new bot. How should I call it? 
           Give me a name for your bot.

Вы: SpeakBuddy Students
(или другое название)

BotFather: Good. Now tell me the bot's username. 
           It must end in 'bot' (e.g., TetrisBot or tetris_bot).

Вы: speakbuddy_students_bot
(или @username_по_выбору_bot)

BotFather: Done! Congratulations on your new bot. 
           Here are your bot credentials.

           Name: SpeakBuddy Students
           @speakbuddy_students_bot
           🔗 https://t.me/speakbuddy_students_bot

           Use this token to access the HTTP API:
           7123456789:ABCDEFGhIjKlMnOpQrStUvWxYz-_ABCDEF

           Keep your token secure and store it safely!
```

**Сохраните токен:**
```
TELEGRAM_TOKEN_STUDENTS=7123456789:ABCDEFGhIjKlMnOpQrStUvWxYz-_ABCDEF
```

---

## Шаг 3: Создайте второго бота (для Взрослых)

Введите `/newbot` снова в BotFather

### Диалог:

```
BotFather: Alright, a new bot. How should I call it?

Вы: SpeakBuddy Adults
(или другое название)

BotFather: Good. Now tell me the bot's username.

Вы: speakbuddy_adults_bot
(или @username_по_выбору_bot)

BotFather: Done! Congratulations on your new bot.
           
           Name: SpeakBuddy Adults
           @speakbuddy_adults_bot
           🔗 https://t.me/speakbuddy_adults_bot

           Use this token to access the HTTP API:
           9876543210:XYZabcdefghijklmnopqrstuvwxyz123456

           Keep your token secure and store it safely!
```

**Сохраните токен:**
```
TELEGRAM_TOKEN_ADULTS=9876543210:XYZabcdefghijklmnopqrstuvwxyz123456
```

---

## Шаг 4: Обновите .env файл

Откройте `.env` в проекте и заполните:

```env
# ============================================================================
# TELEGRAM BOT CONFIGURATION
# ============================================================================
# Choose audience: students or adults (default: adults)
AUDIENCE=adults

# Bot token for STUDENTS audience
TELEGRAM_TOKEN_STUDENTS=7123456789:ABCDEFGhIjKlMnOpQrStUvWxYz-_ABCDEF

# Bot token for ADULTS audience
TELEGRAM_TOKEN_ADULTS=9876543210:XYZabcdefghijklmnopqrstuvwxyz123456

# ============================================================================
# CLAUDE API CONFIGURATION
# ============================================================================
# Get from: https://console.anthropic.com/account/keys
ANTHROPIC_API_KEY=sk-ant-v0-xxxxxxxxxxxxxxxxxxxxx

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL=sqlite+aiosqlite:///./speakbuddy.db

# ============================================================================
# ENVIRONMENT & DEBUG
# ============================================================================
ENVIRONMENT=development
DEBUG=True

# ============================================================================
# PAYMENT CONFIGURATION (опционально)
# ============================================================================
YUKASSA_API_KEY=your_yukassa_api_key_here
YUKASSA_SHOP_ID=your_shop_id_here
```

---

## Шаг 5: (Опционально) Конфигурация ботов в BotFather

Для каждого бота можно установить:
- Описание
- Картинку профиля
- Команды

**Например, для Students бота:**

```
/mybots
→ Выберите @speakbuddy_students_bot
→ Edit Bot
→ Edit description

Description:
Практикуй разговорный английский! Общение со сценариями о учёбе, клубах, здоровье и отношениях.
```

**Команды:**

```
/setcommands
→ Выберите бота
→ Введите команды:

/start - начать регистрацию
/new - новый диалог
/profile - мой профиль
/stats - статистика
/premium - купить премиум
/end - завершить диалог
```

---

## Шаг 6: Тестирование

### Запустите бот для студентов:
```bash
AUDIENCE=students python -m src.main
```

Затем откройте Telegram и найдите @speakbuddy_students_bot и нажмите /start

### Запустите бот для взрослых:
```bash
AUDIENCE=adults python -m src.main
```

Затем откройте Telegram и найдите @speakbuddy_adults_bot и нажмите /start

---

## Важно!

⚠️ **Никогда не публикуйте токены в GitHub!**

- Токены хранятся в `.env` файле
- `.env` добавлен в `.gitignore` (не коммитится)
- Если случайно опубликовали, удалите бота и создайте новый

---

## Что дальше?

После создания ботов и заполнения .env:

1. ✅ Убедитесь, что БД инициализирована
2. ✅ Обновлена .env файл
3. Тестируйте оба бота:
   - Регистрация с выбором аудитории
   - Выбор сценариев
   - Диалоги с Claude
   - Проверка лимитов сообщений

Удачи! 🚀
