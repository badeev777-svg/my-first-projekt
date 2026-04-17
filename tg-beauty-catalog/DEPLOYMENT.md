# Deployment Guide — BeautyCatalog API

## Хостинг

**Render.com** (free tier)  
URL: `https://beauty-catalog-api.onrender.com`  
Репозиторий: `badeev777-svg/my-first-projekt`, ветка `master`  
Root directory: `tg-beauty-catalog/backend`

> Free tier засыпает после 15 минут неактивности. Cold start ~50 сек.  
> UptimeRobot пингует `/health` каждые 5 минут — предотвращает сон.

---

## Переменные окружения (Render Dashboard → Environment)

| Ключ | Описание |
|------|----------|
| `ENVIRONMENT` | `production` |
| `PYTHON_VERSION` | `3.11.0` |
| `DATABASE_URL` | PostgreSQL URL из Supabase (формат: `postgresql+asyncpg://...`) |
| `PLATFORM_BOT_TOKEN` | Токен @Anna_Ghuk_Beauty_bot (платформенный бот) |
| `ADMIN_TELEGRAM_USER_ID` | Telegram ID администратора |
| `FERNET_KEY` | Ключ шифрования токенов мастеров (генерируется один раз) |
| `API_BASE_URL` | `https://beauty-catalog-api.onrender.com` |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | Публичный ключ Supabase (anon) |
| `SUPABASE_SERVICE_ROLE_KEY` | Секретный ключ Supabase (используется для Storage) |

### Генерация FERNET_KEY

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

---

## Python version pinning

Версия зафиксирована тремя способами (для надёжности):

1. `backend/.python-version` → `3.11.0`
2. `backend/runtime.txt` → `python-3.11.0`
3. Render env var `PYTHON_VERSION=3.11.0`

---

## Деплой

Render деплоит автоматически при каждом `git push origin master`.

```bash
git push origin master
```

Следить за прогрессом: Render Dashboard → Events.

---

## База данных

**Supabase** (PostgreSQL)  
Таблицы создаются через SQLAlchemy при старте приложения (`Base.metadata.create_all`).

---

## Подключение бота мастера

1. Мастер создаёт бота через @BotFather
2. Открывает платформенный бот @Anna_Ghuk_Beauty_bot
3. Отправляет: `/connect <токен>`
4. Платформа:
   - Проверяет токен через Telegram `getMe`
   - Создаёт запись в таблице `masters`
   - Устанавливает вебхук: `https://beauty-catalog-api.onrender.com/v1/webhook/<sha256(token)>`

### Ручная установка вебхука

Если вебхук не установился автоматически:

```bash
# Вычислить хеш токена
python -c "import hashlib; print(hashlib.sha256('<TOKEN>'.encode()).hexdigest())"

# Установить вебхук
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://beauty-catalog-api.onrender.com/v1/webhook/<HASH>"
```

---

## UptimeRobot

Монитор: `beauty-catalog-api.onrender.com/health`  
Интервал: 5 минут, метод HEAD  
Сайт: [uptimerobot.com](https://uptimerobot.com)

Эндпоинт `/health` принимает GET и HEAD запросы.

---

## Платформенный бот (вебхук)

При старте в production автоматически устанавливается вебхук:  
`https://beauty-catalog-api.onrender.com/v1/platform-webhook`

При остановке вебхук снимается автоматически.
