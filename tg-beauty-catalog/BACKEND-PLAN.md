# BACKEND-PLAN.md — Архитектурный план бэкенда

> Статус: готов к разработке  
> Версия: 1.0  
> Дата: 2026-04-15  
> Основан на: research.md, brief.md, tg-app/CLAUDE.md + ответы на 7 архитектурных вопросов

---

## Содержание

1. [Обзор системы](#1-обзор-системы)
2. [Роли и доступ](#2-роли-и-доступ)
3. [Схема базы данных](#3-схема-базы-данных)
4. [API — эндпоинты](#4-api--эндпоинты)
5. [Webhook-архитектура (мультибот)](#5-webhook-архитектура-мультибот)
6. [Онбординг мастера](#6-онбординг-мастера)
7. [Подписка и лимиты (Telegram Stars)](#7-подписка-и-лимиты-telegram-stars)
8. [Scheduler — автоматические напоминания](#8-scheduler--автоматические-напоминания)
9. [Бот-консультант (гибридный режим)](#9-бот-консультант-гибридный-режим)
10. [Хранение файлов (фото)](#10-хранение-файлов-фото)
11. [Безопасность](#11-безопасность)
12. [Рекомендуемый стек](#12-рекомендуемый-стек)
13. [Фазы разработки](#13-фазы-разработки)

---

## 1. Обзор системы

```
┌─────────────────────────────────────────────────────────────────┐
│                      ПЛАТФОРМА (ваш сервер)                     │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐  │
│  │  Platform    │   │   REST API   │   │   Scheduler       │  │
│  │  Bot         │   │  (FastAPI)   │   │  (напоминания)    │  │
│  │ @YourBot     │   │              │   │                   │  │
│  └──────┬───────┘   └──────┬───────┘   └─────────┬─────────┘  │
│         │                  │                     │             │
│         └──────────────────┼─────────────────────┘            │
│                            │                                   │
│                    ┌───────▼────────┐                          │
│                    │  PostgreSQL DB  │                          │
│                    └───────┬────────┘                          │
│                            │                                   │
│  ┌─────────────────────────▼──────────────────────────────┐   │
│  │         Webhook Dispatcher (мультибот-маршрутизатор)    │   │
│  │  POST /webhook/{token_hash} → определяет master_id      │   │
│  └────┬────────────────┬──────────────────┬───────────────┘   │
│       │                │                  │                    │
└───────┼────────────────┼──────────────────┼────────────────────┘
        │                │                  │
   @MasterBot_1     @MasterBot_2       @MasterBot_N
   (бот Анны)       (бот Ольги)        (бот Марины)
        │                │                  │
   Клиенты Анны    Клиенты Ольги     Клиенты Марины
   Mini App Анны   Mini App Ольги    Mini App Марины
```

### Ключевые принципы

| Принцип | Решение |
|---------|---------|
| Мультитенантность | Полная изоляция по `master_id` — каждый мастер видит только своё |
| Один сервер — много ботов | Webhook multiplexer: платформа принимает обновления всех ботов |
| Mini App | Один задеплоенный фронтенд, URL содержит `?m={master_slug}` |
| Хранение фото | S3-совместимое хранилище (Cloudflare R2 / MinIO) |
| Идентификация клиента | `initData` от Telegram WebApp, верифицируется HMAC-SHA256 |
| Идентификация мастера | `telegram_user_id` мастера + его бот-токен |

---

## 2. Роли и доступ

### Три роли

```
Супер-админ (вы)
    │  управляет через команды @YourPlatformBot
    │  видит всё: всех мастеров, статусы, метрики
    │
    ├── Мастер (N штук)
    │       управляет через команды своего @MasterBot
    │       видит: только своих клиентов, свои записи, свои услуги
    │
    └── Клиент (M штук на мастера)
            взаимодействует через Mini App и @MasterBot
            видит: публичный профиль мастера, свои записи
```

### Матрица доступа

| Ресурс | Клиент | Мастер | Супер-админ |
|--------|--------|--------|-------------|
| Профиль мастера (публичный) | чтение | чтение + запись | чтение |
| Услуги мастера | чтение | CRUD (лимит 5 / ∞) | чтение |
| Портфолио мастера | чтение | CRUD | чтение |
| Расписание (слоты) | чтение свободных | CRUD | чтение |
| Записи (bookings) | своих: чтение + отмена | все своих: CRUD | чтение |
| Клиенты мастера | — | чтение своих, заметки | чтение |
| FAQ бота | чтение | CRUD | чтение |
| Темы оформления | — | чтение (выбор после оплаты) | CRUD |
| Подписка | — | оплата своей | управление всеми |
| Все мастера платформы | — | — | CRUD |

---

## 3. Схема базы данных

### 3.1 Таблица `masters`

```sql
CREATE TABLE masters (
    id                      BIGSERIAL PRIMARY KEY,
    telegram_user_id        BIGINT UNIQUE NOT NULL,   -- ID мастера в Telegram
    bot_token               TEXT NOT NULL,             -- зашифровано в БД
    bot_token_hash          TEXT UNIQUE NOT NULL,      -- SHA256(bot_token), для маршрутизации webhook
    bot_username            TEXT NOT NULL,             -- @username бота
    slug                    TEXT UNIQUE NOT NULL,      -- короткий ID для URL: ?m=anna_nails
    
    -- Профиль
    name                    TEXT NOT NULL,
    specialty               TEXT,                      -- 'Nail-мастер', 'Lash-мастер'
    city                    TEXT,
    bio                     TEXT,
    avatar_url              TEXT,
    tags                    TEXT[],                    -- ['Гель-лак', 'Наращивание']
    
    -- Рейтинг (денормализован для скорости)
    rating                  DECIMAL(2,1) DEFAULT 0,
    reviews_count           INT DEFAULT 0,
    rating_breakdown        JSONB DEFAULT '{"5":0,"4":0,"3":0,"2":0,"1":0}',
    
    -- Подписка
    subscription_status     TEXT DEFAULT 'free'        -- 'free' | 'active' | 'expired'
                            CHECK (subscription_status IN ('free', 'active', 'expired')),
    subscription_expires_at TIMESTAMPTZ,
    services_limit          INT DEFAULT 5,             -- 5 бесплатно, ∞ после оплаты
    
    -- Тема (разблокируется после оплаты)
    theme_id                INT REFERENCES themes(id) DEFAULT 1,
    accent_color            TEXT,                      -- кастомный HEX, перекрывает тему
    logo_url                TEXT,
    
    -- Статус
    is_active               BOOLEAN DEFAULT TRUE,
    webhook_set_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 Таблица `services`

```sql
CREATE TABLE services (
    id              BIGSERIAL PRIMARY KEY,
    master_id       BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    
    category        TEXT NOT NULL,     -- 'Маникюр' | 'Педикюр' | 'Брови' | 'Ресницы'
    name            TEXT NOT NULL,
    description     TEXT,
    price           INT NOT NULL,      -- в рублях (целое число)
    duration_min    INT NOT NULL,      -- длительность в минутах
    includes        JSONB,             -- ["Снятие покрытия", "Обработка кутикулы"]
    is_popular      BOOLEAN DEFAULT FALSE,
    sort_order      INT DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Лимит на количество активных услуг проверяется в API (не триггером)
CREATE INDEX idx_services_master ON services(master_id) WHERE is_active = TRUE;
```

### 3.3 Таблица `service_photos`

```sql
CREATE TABLE service_photos (
    id          BIGSERIAL PRIMARY KEY,
    service_id  BIGINT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    photo_url   TEXT NOT NULL,
    sort_order  INT DEFAULT 0
);
```

### 3.4 Таблица `portfolio_items`

```sql
CREATE TABLE portfolio_items (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    service_id  BIGINT REFERENCES services(id) ON DELETE SET NULL,
    
    category    TEXT NOT NULL,         -- для фильтра в Gallery экране
    photo_url   TEXT NOT NULL,
    label       TEXT,                  -- подпись к фото
    sort_order  INT DEFAULT 0,
    
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_portfolio_master ON portfolio_items(master_id, category);
```

### 3.5 Таблица `work_schedule` (шаблон недели)

```sql
CREATE TABLE work_schedule (
    id              BIGSERIAL PRIMARY KEY,
    master_id       BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    
    day_of_week     INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- 0=Пн, 6=Вс
    start_time      TIME NOT NULL,         -- '09:00'
    end_time        TIME NOT NULL,         -- '19:00'
    slot_duration_min INT DEFAULT 90,      -- интервал между слотами
    is_working      BOOLEAN DEFAULT TRUE,
    
    UNIQUE (master_id, day_of_week)
);
```

### 3.6 Таблица `slot_overrides` (исключения из расписания)

```sql
CREATE TABLE slot_overrides (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    
    date        DATE NOT NULL,
    time        TIME,               -- NULL = весь день недоступен
    is_blocked  BOOLEAN DEFAULT TRUE,
    reason      TEXT,               -- 'Отпуск', 'Личное'
    
    UNIQUE (master_id, date, time)
);
```

### 3.7 Таблица `clients`

> Полностью изолирована по `master_id`. Один человек в Telegram = разные записи у разных мастеров.

```sql
CREATE TABLE clients (
    id                  BIGSERIAL PRIMARY KEY,
    master_id           BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    
    telegram_user_id    BIGINT NOT NULL,
    telegram_chat_id    BIGINT NOT NULL,    -- для отправки сообщений боту мастера
    first_name          TEXT,
    last_name           TEXT,
    username            TEXT,
    phone               TEXT,               -- из requestContact(), может быть NULL
    
    -- Приватные заметки мастера (клиент не видит)
    master_notes        TEXT,
    
    -- Статистика (денормализовано)
    visits_count        INT DEFAULT 0,
    last_visit_at       DATE,
    
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (master_id, telegram_user_id)
);

CREATE INDEX idx_clients_master ON clients(master_id);
```

### 3.8 Таблица `bookings`

```sql
CREATE TABLE bookings (
    id              BIGSERIAL PRIMARY KEY,
    master_id       BIGINT NOT NULL REFERENCES masters(id),
    client_id       BIGINT NOT NULL REFERENCES clients(id),
    service_id      BIGINT REFERENCES services(id) ON DELETE SET NULL,
    
    -- Снимок данных на момент записи (услуга может измениться)
    service_name    TEXT NOT NULL,
    service_price   INT NOT NULL,
    duration_min    INT NOT NULL,
    
    date            DATE NOT NULL,
    time            TIME NOT NULL,
    phone           TEXT NOT NULL,
    comment         TEXT,
    
    status          TEXT DEFAULT 'confirmed'
                    CHECK (status IN ('confirmed', 'completed', 'cancelled', 'no_show')),
    cancelled_by    TEXT CHECK (cancelled_by IN ('client', 'master', 'system')),
    cancelled_at    TIMESTAMPTZ,
    
    -- Напоминания
    reminder_24h_sent   BOOLEAN DEFAULT FALSE,
    reminder_2h_sent    BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bookings_master_date ON bookings(master_id, date);
CREATE INDEX idx_bookings_client ON bookings(client_id);
-- Индекс для scheduler: поиск записей требующих напоминания
CREATE INDEX idx_bookings_reminders ON bookings(date, time, status)
    WHERE reminder_24h_sent = FALSE OR reminder_2h_sent = FALSE;
```

### 3.9 Таблица `reviews`

```sql
CREATE TABLE reviews (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    client_id   BIGINT REFERENCES clients(id) ON DELETE SET NULL,
    booking_id  BIGINT REFERENCES bookings(id) ON DELETE SET NULL,
    
    rating          INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text            TEXT,
    service_name    TEXT,       -- снимок названия услуги
    
    is_visible      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- После INSERT/UPDATE пересчитываем rating в masters:
-- UPDATE masters SET rating = ..., reviews_count = ..., rating_breakdown = ...
-- WHERE id = NEW.master_id
```

### 3.10 Таблица `themes`

```sql
CREATE TABLE themes (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,          -- 'Warm Nude'
    bg_color        TEXT NOT NULL,          -- '#FAF7F4'
    card_color      TEXT NOT NULL,          -- '#FFFFFF'
    accent_color    TEXT NOT NULL,          -- '#C9967A'
    accent2_color   TEXT NOT NULL,
    accent3_color   TEXT NOT NULL,
    text_color      TEXT NOT NULL,          -- '#2C2220'
    muted_color     TEXT NOT NULL,          -- '#9A8A82'
    border_color    TEXT NOT NULL,          -- '#EDE5DF'
    dark_bg_color   TEXT NOT NULL,          -- '#1C1C1E'
    dark_card_color TEXT NOT NULL,          -- '#2C2C2E'
    is_premium      BOOLEAN DEFAULT FALSE   -- FALSE = доступна всем, TRUE = только подписчикам
);

-- Предзаполнение из research.md:
INSERT INTO themes VALUES
(1, 'Warm Nude',    '#FAF7F4','#FFFFFF','#C9967A','#E8D5C4','#F5EDE6','#2C2220','#9A8A82','#EDE5DF','#1C1C1E','#2C2C2E', FALSE),
(2, 'Sage & Cream', '#F4F6F2','#FFFFFF','#8A9E7B','#D4C5A9','#EAF0E6','#2D3228','#7A8C73','#DDE4D9','#1E231D','#2A312A', TRUE),
(3, 'Dark Luxury',  '#1A1A1A','#2C2C2C','#C9A96E','#A07840','#3A3020','#F5F0E8','#B0A898','#333333','#0D0D0D','#1A1A1A', TRUE);
```

### 3.11 Таблица `subscriptions` (история платежей)

```sql
CREATE TABLE subscriptions (
    id                          BIGSERIAL PRIMARY KEY,
    master_id                   BIGINT NOT NULL REFERENCES masters(id),
    
    telegram_payment_charge_id  TEXT UNIQUE NOT NULL,   -- из Telegram successful_payment
    stars_amount                INT NOT NULL,
    period_months               INT NOT NULL DEFAULT 1,
    
    starts_at                   TIMESTAMPTZ NOT NULL,
    expires_at                  TIMESTAMPTZ NOT NULL,
    
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.12 Таблица `faq_items` (скрипты бота-консультанта)

```sql
CREATE TABLE faq_items (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    
    question    TEXT NOT NULL,      -- 'Сколько держится гель-лак?'
    answer      TEXT NOT NULL,      -- 'Покрытие держится 2–3 недели...'
    sort_order  INT DEFAULT 0
);
```

### 3.13 Таблица `master_settings`

```sql
CREATE TABLE master_settings (
    master_id                       BIGINT PRIMARY KEY REFERENCES masters(id) ON DELETE CASCADE,
    
    cancellation_hours              INT DEFAULT 24,         -- бесплатная отмена за N часов
    reminder_24h_enabled            BOOLEAN DEFAULT TRUE,
    reminder_2h_enabled             BOOLEAN DEFAULT TRUE,
    welcome_message                 TEXT DEFAULT 'Добро пожаловать! Я помогу вам записаться.',
    booking_confirm_message         TEXT DEFAULT 'Ваша запись подтверждена! Ждём вас.',
    days_advance_booking            INT DEFAULT 30,         -- бронирование на N дней вперёд
    forward_unknown_to_master       BOOLEAN DEFAULT TRUE    -- пересылать неизвестные сообщения мастеру
);
```

---

## 4. API — эндпоинты

Базовый URL: `https://api.yourplatform.com/v1`

Аутентификация: заголовок `X-Telegram-Init-Data: <raw initData string>`  
Сервер верифицирует HMAC-SHA256 с `bot_token` мастера (по `master_id` из URL).

---

### 4.1 Публичные (Mini App клиента)

#### Профиль мастера

```
GET /masters/{slug}/profile
→ { id, name, specialty, city, bio, avatar_url, tags,
    rating, reviews_count, rating_breakdown,
    theme: { bg_color, accent_color, ... },
    accent_color, logo_url }
```

#### Услуги

```
GET /masters/{slug}/services?category=Маникюр
→ [ { id, category, name, price, duration_min, includes,
      is_popular, photos: [{photo_url, sort_order}] } ]
```

#### Портфолио

```
GET /masters/{slug}/portfolio?category=Маникюр&limit=30&offset=0
→ [ { id, category, photo_url, label, service_id } ]
```

#### Отзывы

```
GET /masters/{slug}/reviews?limit=20&offset=0
→ { rating, reviews_count, rating_breakdown,
    items: [ { id, rating, text, service_name, client_name, created_at } ] }
```

#### Доступные слоты

```
GET /masters/{slug}/slots?date=2026-04-18
→ { date, slots: [ { time, is_available } ] }

GET /masters/{slug}/slots/month?year=2026&month=4
→ { days: { "2026-04-17": "unavailable", "2026-04-18": "partial", "2026-04-20": "free" } }
```

Логика: берём `work_schedule` для дня недели → генерируем слоты → вычитаем `bookings` (status=confirmed) и `slot_overrides`.

---

### 4.2 Клиентские (требуют initData)

#### Мои записи

```
GET /clients/me/bookings?status=upcoming
→ [ { id, service_name, date, time, duration_min, price, status, comment } ]

Параметры status: upcoming | past | all
```

#### Создать запись

```
POST /bookings
Body: {
    master_slug:  "anna_nails",
    service_id:   1,
    date:         "2026-04-18",
    time:         "10:30",
    phone:        "+7 900 000-00-00",
    comment:      "Покрытие бежевое"
}
→ 201 { booking_id, status: "confirmed", master_name, service_name, date, time }
→ 409 { error: "slot_taken" }         -- слот уже занят (race condition защита)
→ 402 { error: "master_inactive" }    -- у мастера закончилась подписка
```

**Защита от двойного бронирования:**
```sql
-- В транзакции:
SELECT id FROM bookings
WHERE master_id = ? AND date = ? AND time = ? AND status = 'confirmed'
FOR UPDATE;
-- Если нашли → 409
-- Если нет → INSERT bookings
```

#### Отменить запись

```
PATCH /bookings/{booking_id}/cancel
→ 200 { status: "cancelled" }
→ 403 { error: "cancellation_window_passed" }  -- прошло N часов до записи
→ 404
```

#### Перенести запись

```
PATCH /bookings/{booking_id}/reschedule
Body: { date: "2026-04-22", time: "12:00" }
→ 200 { booking_id, date, time }
→ 409 { error: "slot_taken" }
```

---

### 4.3 Мастер (команды через бота, не HTTP)

Мастер управляет через Telegram-команды своего бота. Никакого отдельного веб-интерфейса.

Полный список команд — в [разделе 9](#9-бот-консультант-гибридный-режим).

---

### 4.4 Webhook (Telegram → платформа)

```
POST /webhook/{token_hash}
```

Dispatcher по `token_hash` определяет `master_id` и передаёт update нужному обработчику.

---

### 4.5 Супер-админ (ваш платформенный бот)

Команды вашему личному боту @YourPlatformBot.  
Список — в [разделе 6.3](#63-команды-супер-админа).

---

## 5. Webhook-архитектура (мультибот)

### Проблема

У каждого мастера — свой бот. Telegram шлёт обновления на разные URL. Нам нужен один сервер.

### Решение: webhook per token, диспетчер на сервере

```
Telegram → POST /webhook/a3f9c2d1 (hash от токена бота Анны)
         → POST /webhook/b7e4a1f0 (hash от токена бота Ольги)

Dispatcher:
    1. Получает update
    2. Извлекает token_hash из URL
    3. SELECT master_id FROM masters WHERE bot_token_hash = ?
    4. Передаёт update в обработчик с master_id
```

### Регистрация webhook при онбординге

```python
# При /connect <token>:
token_hash = sha256(token)
webhook_url = f"https://api.yourplatform.com/v1/webhook/{token_hash}"
response = requests.post(
    f"https://api.telegram.org/bot{token}/setWebhook",
    json={"url": webhook_url, "allowed_updates": ["message", "callback_query", "pre_checkout_query", "successful_payment"]}
)
```

### Отправка сообщений через бот мастера

```python
def send_via_master_bot(master_id: int, chat_id: int, text: str):
    token = get_decrypted_token(master_id)
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
```

---

## 6. Онбординг мастера

### 6.1 Полный флоу подключения

```
Шаг 1. Мастер находит @YourPlatformBot
        → /start
        → Бот: «Добро пожаловать! Создайте своего бота через @BotFather:
                1. Откройте @BotFather
                2. Отправьте /newbot
                3. Придумайте имя и username
                4. Скопируйте токен и отправьте мне: /connect <токен>»

Шаг 2. Мастер присылает /connect 1234567890:AAH...
        → Платформа:
            a. Вызывает api.telegram.org/bot{TOKEN}/getMe
            b. Проверяет: токен валиден, бот не занят другим мастером
            c. Сохраняет masters{ bot_token (зашифровано), bot_token_hash, bot_username, ... }
            d. Регистрирует webhook
            e. Создаёт master_settings с дефолтами
            f. Отправляет мастеру инструкцию по заполнению профиля

Шаг 3. Мастер заполняет профиль через команды своего бота
        (см. раздел 9 — команды мастера)

Шаг 4. Платформа генерирует:
        Mini App URL: https://yourplatform.com/app?m={slug}
        → Мастер добавляет этот URL в @BotFather → /myapps → New App

Шаг 5. Первые 5 услуг — бесплатно. 6-я → предложение подписки.
```

### 6.2 Генерация slug

```python
def generate_slug(name: str, bot_username: str) -> str:
    # Приоритет: из имени бота без _bot
    slug = bot_username.replace("_bot", "").replace("bot", "").lower()
    # Если занят — добавить рандомные 4 символа
    if slug_exists(slug):
        slug = f"{slug}_{random_hex(4)}"
    return slug
```

### 6.3 Команды супер-админа

Доступны только вашему `telegram_user_id` в @YourPlatformBot.

```
/masters               — список всех мастеров (id, имя, @бот, статус подписки)
/master {id}           — подробная карточка: услуги, записи за месяц, клиенты
/activate {id}         — вручную активировать подписку (для тестов)
/block {id}            — заблокировать мастера (is_active = FALSE)
/unblock {id}          — разблокировать
/stats                 — общая статистика: мастеров, записей, выручка Stars
/setlimit {id} {n}     — вручную установить лимит услуг
```

---

## 7. Подписка и лимиты (Telegram Stars)

### 7.1 Тарифы

| Тариф | Услуг | Темы | Цена |
|-------|-------|------|------|
| Free  | 5     | Warm Nude (default) | 0 |
| Pro   | ∞     | Все 3+ темы, кастомный цвет и лого | N Stars/мес |

> Конкретное количество Stars — установить перед запуском. Рекомендация из research.md: аналог 990₽/мес.  
> 1 Star ≈ $0.013 → ~990₽ ≈ ~750 Stars.

### 7.2 Флоу оплаты

```
1. Мастер добавляет 6-ю услугу → бот присылает:
   «Вы использовали 5 бесплатных услуг. Подключите подписку Pro за 750 ⭐/мес»
   [Оплатить подписку]   [Отмена]

2. Нажимает «Оплатить» → бот отправляет Invoice (Telegram Payments API):
   sendInvoice(
       chat_id = master_chat_id,
       title = "Подписка BeautyCatalog Pro",
       description = "Безлимитные услуги + темы оформления · 1 месяц",
       payload = f"sub_master_{master_id}",
       currency = "XTR",       # Telegram Stars
       prices = [{"label": "Pro 1 месяц", "amount": 750}]
   )

3. Telegram шлёт pre_checkout_query → сервер подтверждает answerPreCheckoutQuery(ok=True)

4. Telegram шлёт successful_payment:
   a. Создаём запись в subscriptions
   b. UPDATE masters SET
          subscription_status = 'active',
          subscription_expires_at = NOW() + INTERVAL '1 month',
          services_limit = 999999
   c. Бот присылает: «Подписка активирована до {дата}! 🎉
                       Теперь выберите тему оформления:»
      [Warm Nude] [Sage & Cream] [Dark Luxury]

5. Мастер выбирает тему → UPDATE masters SET theme_id = ?, accent_color = ?
   После этого — кнопка «Загрузить логотип»
```

### 7.3 Истечение подписки

Scheduler ежедневно в 00:00:
```sql
UPDATE masters
SET subscription_status = 'expired', services_limit = 5
WHERE subscription_status = 'active'
  AND subscription_expires_at < NOW();
```

После истечения:
- Бот мастера уведомляет: «Подписка истекла. Клиенты видят только 5 услуг.»
- Услуги сверх 5 не удаляются — помечаются `is_active = FALSE`
- При продлении подписки — автоматически возвращаются в `is_active = TRUE`

### 7.4 Проверка лимита в API

```python
def check_services_limit(master_id: int) -> None:
    master = db.get_master(master_id)
    active_count = db.count_active_services(master_id)
    if active_count >= master.services_limit:
        raise HTTPException(402, detail={
            "error": "services_limit_reached",
            "limit": master.services_limit,
            "current": active_count,
            "upgrade_required": True
        })
```

---

## 8. Scheduler — автоматические напоминания

### 8.1 Задачи планировщика

| Задача | Интервал | SQL-условие |
|--------|----------|-------------|
| Напоминание за 24 часа | каждые 15 мин | `date + time BETWEEN NOW()+23h45m AND NOW()+24h15m AND reminder_24h_sent = FALSE` |
| Напоминание за 2 часа | каждые 15 мин | `date + time BETWEEN NOW()+1h45m AND NOW()+2h15m AND reminder_2h_sent = FALSE` |
| Истечение подписок | ежедневно 00:00 | `subscription_expires_at < NOW() AND status = 'active'` |

### 8.2 Тексты сообщений клиенту (через бот мастера)

**24 часа:**
```
⏰ Напоминание о записи

Завтра в {time} — {service_name}
Мастер: {master_name}
Адрес: {city}

Если планы изменились — отмените запись не позднее чем за {cancellation_hours} часов.
```

**2 часа:**
```
🔔 Ваша запись совсем скоро!

Через 2 часа — {service_name}
Время: {time}
Мастер: {master_name}
```

### 8.3 Обновление флагов после отправки

```sql
UPDATE bookings SET reminder_24h_sent = TRUE WHERE id = ?;
UPDATE bookings SET reminder_2h_sent = TRUE WHERE id = ?;
```

---

## 9. Бот-консультант (гибридный режим)

### 9.1 Логика обработки сообщений клиента

```
Клиент пишет в @MasterBot:
    │
    ├── /start → приветствие + кнопка «Открыть каталог» (Mini App)
    │
    ├── Нажал FAQ-кнопку → показать ответ из faq_items
    │
    ├── Текстовое сообщение → поиск в faq_items по ключевым словам
    │   ├── Найдено совпадение → отправить ответ из FAQ
    │   └── Не найдено → «Я передам ваш вопрос мастеру» → переслать мастеру
    │
    └── «Написать мастеру» → открыть диалог (forward_unknown_to_master)
```

### 9.2 Сообщение /start клиенту

```python
def send_start_message(master: Master, client_chat_id: int):
    bot.send_message(
        chat_id=client_chat_id,
        text=master.settings.welcome_message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Открыть каталог", web_app=WebAppInfo(url=mini_app_url))],
            [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq_menu")],
            [InlineKeyboardButton("💬 Написать мастеру", callback_data="contact_master")]
        ])
    )
```

### 9.3 FAQ-меню (из faq_items мастера)

```python
def send_faq_menu(master_id: int, client_chat_id: int):
    items = db.get_faq_items(master_id)
    keyboard = [[InlineKeyboardButton(item.question, callback_data=f"faq_{item.id}")]
                for item in items]
    keyboard.append([InlineKeyboardButton("← Назад", callback_data="back_to_menu")])
    bot.send_message(chat_id=client_chat_id, text="Выберите вопрос:", reply_markup=...)
```

### 9.4 Пересылка мастеру (неизвестные сообщения)

```python
def forward_to_master(master: Master, client: Client, message_text: str):
    # Мастеру в его личный чат (telegram_user_id)
    bot.send_message(
        chat_id=master.telegram_user_id,
        text=f"💬 Сообщение от клиента {client.first_name} (@{client.username}):\n\n{message_text}\n\n"
             f"Для ответа: /reply_{client.telegram_user_id} <текст>"
    )
```

### 9.5 Команды мастера (в его собственном боте)

```
--- Профиль ---
/profile               — показать текущий профиль
/set_name <текст>      — изменить имя
/set_bio <текст>       — изменить описание
/set_city <текст>      — изменить город
/set_avatar            — следующее фото станет аватаром

--- Услуги ---
/services              — список услуг с ID
/add_service           — диалог добавления услуги (шаг за шагом)
/edit_service <id>     — изменить услугу
/delete_service <id>   — удалить услугу
/toggle_service <id>   — включить/выключить услугу

--- Расписание ---
/schedule              — показать текущее расписание
/set_schedule          — настройка рабочих дней и часов (диалог)
/block_day <YYYY-MM-DD> [причина]   — заблокировать день
/block_slot <YYYY-MM-DD> <HH:MM>    — заблокировать конкретный слот
/unblock <YYYY-MM-DD>               — разблокировать день

--- Записи ---
/today                 — записи на сегодня
/upcoming              — ближайшие 7 дней
/booking <id>          — детали записи
/complete <id>         — отметить запись выполненной
/noshow <id>           — отметить no-show

--- Клиенты ---
/clients               — список клиентов (сортировка: последний визит)
/client <id>           — карточка клиента: история, контакт
/note <client_id> <текст>   — добавить заметку о клиенте

--- FAQ бота ---
/faq                   — список FAQ
/add_faq               — добавить вопрос/ответ
/delete_faq <id>       — удалить

--- Подписка и тема ---
/subscription          — статус подписки и дата истечения
/subscribe             — оплатить/продлить подписку (Stars)
/theme                 — выбрать тему (только для Pro)
/set_color <#HEX>      — кастомный акцентный цвет (только для Pro)
/set_logo              — следующее фото станет логотипом (только для Pro)

--- Ответ клиенту ---
/reply_<user_id> <текст>   — ответить клиенту, который написал боту
```

---

## 10. Хранение файлов (фото)

### Провайдер

**Cloudflare R2** (S3-совместимый): нет платы за исходящий трафик, $0.015/GB хранилище.  
Альтернатива: MinIO на том же VPS для малого масштаба.

### Структура бакета

```
beauty-catalog/
└── masters/
    └── {master_id}/
        ├── avatar.webp
        ├── logo.webp
        ├── portfolio/
        │   ├── {portfolio_item_id}.webp
        │   └── ...
        └── services/
            ├── {service_id}/
            │   ├── photo_1.webp
            │   └── photo_2.webp
            └── ...
```

### Обработка загрузки

Мастер присылает фото боту → сервер:
1. Скачивает с Telegram CDN (`getFile` → `file_path`)
2. Конвертирует в WebP (Pillow / sharp)
3. Создаёт thumbnail 400×400 (для сетки портфолио)
4. Создаёт fullsize 1200px max (для просмотра)
5. Загружает оба в R2
6. Сохраняет URL в БД

```python
THUMBNAIL_SIZE = (400, 400)
FULLSIZE_MAX = 1200
```

---

## 11. Безопасность

### 11.1 Верификация initData (обязательно)

Каждый запрос из Mini App содержит `initData`. Сервер обязан проверить подпись.

```python
def verify_init_data(init_data: str, bot_token: str) -> dict:
    parsed = parse_qs(init_data)
    received_hash = parsed.pop("hash")[0]
    
    data_check_string = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()
    
    if not hmac.compare_digest(received_hash, expected_hash):
        raise HTTPException(401, "Invalid initData")
    
    # Проверка давности: initData валидна не более 1 часа
    auth_date = int(parsed["auth_date"][0])
    if time.time() - auth_date > 3600:
        raise HTTPException(401, "initData expired")
    
    return json.loads(parsed["user"][0])
```

### 11.2 Шифрование bot_token в БД

```python
# При сохранении:
from cryptography.fernet import Fernet
FERNET_KEY = os.environ["FERNET_KEY"]  # 32-байтовый ключ в env
cipher = Fernet(FERNET_KEY)
encrypted_token = cipher.encrypt(token.encode()).decode()

# При чтении:
token = cipher.decrypt(master.bot_token.encode()).decode()
```

### 11.3 Защита от race condition при бронировании

```sql
BEGIN;
SELECT id FROM bookings
WHERE master_id = $1 AND date = $2 AND time = $3 AND status = 'confirmed'
FOR UPDATE NOWAIT;           -- немедленно ошибка если строка залочена
-- Если SELECT вернул строку → ROLLBACK + 409
INSERT INTO bookings (...) VALUES (...);
COMMIT;
```

### 11.4 Остальные меры

- Все запросы только по HTTPS
- `bot_token` не логируется (маскировать в логах)
- Команды мастера доступны только его `telegram_user_id`
- Команды супер-админа — только вашему `telegram_user_id` (захардкожен в env)
- Rate limiting: 60 req/min на `master_slug` для публичных эндпоинтов
- Фото: проверять MIME-type и размер (max 10MB) перед загрузкой

---

## 12. Рекомендуемый стек

| Компонент | Выбор | Почему |
|-----------|-------|--------|
| Язык | **Python 3.11+** | aiogram для ботов, FastAPI для API — зрелые, быстрые |
| API-фреймворк | **FastAPI** | автодокументация, async, pydantic-валидация |
| Telegram-боты | **aiogram 3.x** | поддерживает мультибот, активно развивается |
| БД | **PostgreSQL 15** | JSONB, транзакции, `FOR UPDATE`, надёжность |
| ORM | **SQLAlchemy 2 + asyncpg** | async-поддержка PostgreSQL |
| Scheduler | **APScheduler** | встраивается в Python-процесс, cron-задачи |
| Файлы | **Cloudflare R2** | S3-API, бесплатный исходящий трафик |
| Обработка фото | **Pillow** | конвертация в WebP, ресайз |
| Шифрование токенов | **cryptography (Fernet)** | симметричное шифрование |
| Хостинг | **VPS 2vCPU / 2GB RAM** | Timeweb/DigitalOcean — от 500₽/мес |
| Деплой | **Docker Compose** | один файл: api + scheduler + postgres + nginx |

### Структура проекта (бэкенд)

```
backend/
├── main.py                  # FastAPI app + webhook dispatcher
├── config.py                # env vars (FERNET_KEY, ADMIN_TG_ID, DATABASE_URL)
├── database.py              # SQLAlchemy engine, session
│
├── models/                  # SQLAlchemy ORM-модели
│   ├── master.py
│   ├── service.py
│   ├── booking.py
│   └── ...
│
├── api/                     # REST API роутеры
│   ├── public.py            # GET /masters/{slug}/...
│   ├── client.py            # GET/POST /bookings, /clients/me/...
│   └── webhook.py           # POST /webhook/{token_hash}
│
├── bot/                     # Telegram bot handlers
│   ├── platform_bot.py      # @YourPlatformBot (онбординг, супер-админ)
│   ├── master_bot.py        # Обработчик команд мастера
│   ├── client_bot.py        # Обработчик сообщений клиента (FAQ, /start)
│   └── payments.py          # Stars: pre_checkout, successful_payment
│
├── services/                # Бизнес-логика
│   ├── slots.py             # Генерация слотов, проверка занятости
│   ├── booking.py           # Создание, отмена, перенос
│   ├── subscription.py      # Активация, проверка лимитов
│   ├── notifications.py     # Отправка сообщений через бот мастера
│   └── media.py             # Загрузка фото в R2
│
├── scheduler/
│   └── jobs.py              # Напоминания 24h/2h, истечение подписок
│
└── docker-compose.yml
```

---

## 13. Фазы разработки

### Фаза 1 — Фундамент (1–2 нед)

- [ ] PostgreSQL: все таблицы + миграции (Alembic)
- [ ] FastAPI: базовая структура, health-check
- [ ] Platform Bot (@YourPlatformBot): `/start`, `/connect <token>`, базовый онбординг
- [ ] Webhook dispatcher: регистрация + маршрутизация
- [ ] Шифрование bot_token

**Готовность:** мастер может подключить своего бота через платформу.

---

### Фаза 2 — Профиль и услуги (1–2 нед)

- [ ] Master Bot: команды `/set_name`, `/set_bio`, `/add_service`, `/services`
- [ ] API: `GET /masters/{slug}/profile`, `GET /masters/{slug}/services`
- [ ] Загрузка фото: аватар, фото услуг, портфолио → R2
- [ ] API: `GET /masters/{slug}/portfolio`
- [ ] Проверка лимита 5 услуг

**Готовность:** Mini App отображает реальные данные мастера.

---

### Фаза 3 — Запись (1–2 нед)

- [ ] Расписание: таблицы `work_schedule` + `slot_overrides`, команды мастера
- [ ] API: `GET /masters/{slug}/slots?date=...`, `GET .../slots/month`
- [ ] API: `POST /bookings` (с защитой от race condition)
- [ ] API: `PATCH /bookings/{id}/cancel`, `PATCH .../reschedule`
- [ ] API: `GET /clients/me/bookings`
- [ ] Верификация initData на всех клиентских эндпоинтах
- [ ] Уведомление мастеру о новой записи

**Готовность:** полный флоу записи через Mini App работает.

---

### Фаза 4 — Подписка и темы (1 нед)

- [ ] Таблицы: `themes` (предзаполнить 3 темы), `subscriptions`
- [ ] Stars Invoice: `/subscribe`, pre_checkout_query, successful_payment
- [ ] Активация подписки, обновление `services_limit`
- [ ] Выбор темы через кнопки после оплаты
- [ ] API: тема возвращается в `GET /masters/{slug}/profile`
- [ ] Scheduler: проверка истечения подписок (ежедневно)
- [ ] Деактивация услуг сверх 5 при истечении

**Готовность:** монетизация работает.

---

### Фаза 5 — Автоматика и консультант (1 нед)

- [ ] Scheduler: напоминания за 24h и 2h (APScheduler, интервал 15 мин)
- [ ] Client Bot: `/start`, FAQ-меню, пересылка неизвестных мастеру
- [ ] Master Bot: `/add_faq`, `/delete_faq`, `/reply_<user_id>`
- [ ] Master Bot: `/today`, `/upcoming`, `/complete`, `/noshow`
- [ ] Супер-админ: `/masters`, `/stats`, `/block`, `/activate`

**Готовность:** система работает автономно.

---

### Фаза 6 — Отзывы и клиентские карточки (по желанию)

- [ ] Таблица `reviews`
- [ ] После `/complete <booking_id>` → бот просит клиента оставить отзыв
- [ ] Пересчёт рейтинга в `masters`
- [ ] API: `GET /masters/{slug}/reviews`
- [ ] Master Bot: `/clients`, `/client <id>`, `/note <id> <текст>`

---

*BACKEND-PLAN.md основан на: research.md (лучшие решения рынка), brief.md (экраны и требования), tg-app/ (текущий фронтенд), ответах на 7 архитектурных вопросов.*
