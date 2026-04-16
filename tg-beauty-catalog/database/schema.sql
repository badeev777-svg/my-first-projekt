-- ============================================================
-- BeautyCatalog — Database Schema
-- Platform: Supabase (PostgreSQL 15)
-- Version:  1.0 | 2026-04-16
-- ============================================================
-- Порядок создания таблиц важен: сначала «родители», потом «дети».
-- Например, masters ссылается на themes → themes создаём первой.
-- ============================================================


-- ============================================================
-- 0. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- для gen_random_uuid() если понадобится


-- ============================================================
-- 1. THEMES — темы оформления Mini App
-- ============================================================
-- Метафора: это как шаблоны дизайна в Canva. Мастер выбирает
-- одну тему, и весь его каталог красится в эти цвета.
-- Бесплатная тема одна (Warm Nude), остальные — после оплаты.

CREATE TABLE themes (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    -- Цвета для светлого режима
    bg_color        TEXT NOT NULL,       -- фон страницы
    card_color      TEXT NOT NULL,       -- фон карточек
    accent_color    TEXT NOT NULL,       -- главный акцент (кнопки, заголовки)
    accent2_color   TEXT NOT NULL,
    accent3_color   TEXT NOT NULL,
    text_color      TEXT NOT NULL,       -- основной текст
    muted_color     TEXT NOT NULL,       -- приглушённый текст (описания)
    border_color    TEXT NOT NULL,       -- рамки, разделители
    -- Цвета для тёмного режима
    dark_bg_color   TEXT NOT NULL,
    dark_card_color TEXT NOT NULL,
    -- Флаг: TRUE = тема доступна только подписчикам Pro
    is_premium      BOOLEAN DEFAULT FALSE
);

-- Предустановленные темы из research.md
INSERT INTO themes (id, name, bg_color, card_color, accent_color, accent2_color, accent3_color,
                    text_color, muted_color, border_color, dark_bg_color, dark_card_color, is_premium)
VALUES
(1, 'Warm Nude',    '#FAF7F4','#FFFFFF','#C9967A','#E8D5C4','#F5EDE6','#2C2220','#9A8A82','#EDE5DF','#1C1C1E','#2C2C2E', FALSE),
(2, 'Sage & Cream', '#F4F6F2','#FFFFFF','#8A9E7B','#D4C5A9','#EAF0E6','#2D3228','#7A8C73','#DDE4D9','#1E231D','#2A312A', TRUE),
(3, 'Dark Luxury',  '#1A1A1A','#2C2C2C','#C9A96E','#A07840','#3A3020','#F5F0E8','#B0A898','#333333','#0D0D0D','#1A1A1A', TRUE);

-- Сбрасываем счётчик ID чтобы следующая тема получила id=4, а не 1
SELECT setval('themes_id_seq', 3);


-- ============================================================
-- 2. MASTERS — мастера платформы
-- ============================================================
-- Метафора: это как карточка арендатора в торговом центре.
-- Каждый мастер — отдельный «магазин» со своим ботом и клиентами.
-- Все данные других мастеров для него невидимы.

CREATE TABLE masters (
    id                      BIGSERIAL PRIMARY KEY,
    telegram_user_id        BIGINT UNIQUE NOT NULL,   -- числовой ID пользователя в Telegram
    bot_token               TEXT NOT NULL,             -- токен бота (хранится ЗАШИФРОВАННЫМ через Fernet)
    bot_token_hash          TEXT UNIQUE NOT NULL,      -- SHA256(bot_token) — для поиска мастера по webhook-запросу
    bot_username            TEXT NOT NULL,             -- @username бота, например "@anna_nails_bot"
    slug                    TEXT UNIQUE NOT NULL,      -- короткий ID для URL: ?m=anna_nails

    -- Публичный профиль мастера
    name                    TEXT NOT NULL,
    specialty               TEXT,                      -- 'Nail-мастер', 'Lash-мастер'
    city                    TEXT,
    bio                     TEXT,
    avatar_url              TEXT,
    tags                    TEXT[],                    -- массив тегов: ['Гель-лак', 'Наращивание']

    -- Рейтинг (денормализован: дублируем данные для быстрого чтения)
    rating                  DECIMAL(2,1) DEFAULT 0,
    reviews_count           INT DEFAULT 0,
    rating_breakdown        JSONB DEFAULT '{"5":0,"4":0,"3":0,"2":0,"1":0}',

    -- Подписка
    subscription_status     TEXT DEFAULT 'free'
                            CHECK (subscription_status IN ('free', 'active', 'expired')),
    subscription_expires_at TIMESTAMPTZ,
    services_limit          INT DEFAULT 5,             -- 5 услуг бесплатно, 999999 после оплаты

    -- Тема оформления
    theme_id                INT REFERENCES themes(id) DEFAULT 1,
    accent_color            TEXT,                      -- кастомный HEX-цвет (перекрывает тему)
    logo_url                TEXT,

    -- Технические поля
    is_active               BOOLEAN DEFAULT TRUE,
    webhook_set_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 3. SERVICES — услуги мастера
-- ============================================================
-- Метафора: это «меню» в кафе. У каждого мастера своё меню.
-- Бесплатный план — 5 позиций. Подписка — безлимит.

CREATE TABLE services (
    id              BIGSERIAL PRIMARY KEY,
    master_id       BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,

    category        TEXT NOT NULL,     -- 'Маникюр' | 'Педикюр' | 'Брови' | 'Ресницы'
    name            TEXT NOT NULL,
    description     TEXT,
    price           INT NOT NULL,      -- в рублях, целое число
    duration_min    INT NOT NULL,      -- длительность процедуры в минутах
    includes        JSONB,             -- список того, что входит: ["Снятие", "Покрытие"]
    is_popular      BOOLEAN DEFAULT FALSE,
    sort_order      INT DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Индекс ускоряет запрос «все активные услуги мастера X»
CREATE INDEX idx_services_master ON services(master_id) WHERE is_active = TRUE;


-- ============================================================
-- 4. SERVICE_PHOTOS — фотографии к услугам
-- ============================================================

CREATE TABLE service_photos (
    id          BIGSERIAL PRIMARY KEY,
    service_id  BIGINT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    photo_url   TEXT NOT NULL,
    sort_order  INT DEFAULT 0
);


-- ============================================================
-- 5. PORTFOLIO_ITEMS — портфолио мастера
-- ============================================================
-- Метафора: галерея работ. Клиент листает фото и выбирает стиль.

CREATE TABLE portfolio_items (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    service_id  BIGINT REFERENCES services(id) ON DELETE SET NULL,  -- можно привязать к услуге

    category    TEXT NOT NULL,   -- для фильтра: 'Маникюр', 'Педикюр'
    photo_url   TEXT NOT NULL,
    label       TEXT,            -- подпись к фото
    sort_order  INT DEFAULT 0,

    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_portfolio_master ON portfolio_items(master_id, category);


-- ============================================================
-- 6. WORK_SCHEDULE — шаблон рабочей недели
-- ============================================================
-- Метафора: расписание звонков в школе. Это «образцовая» неделя.
-- Пн: 09:00–19:00, Вт: 09:00–19:00, Вс: выходной и т.д.
-- Конкретные исключения (отпуск, болезнь) — в slot_overrides.

CREATE TABLE work_schedule (
    id                BIGSERIAL PRIMARY KEY,
    master_id         BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,

    day_of_week       INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Пн, 6=Вс
    start_time        TIME NOT NULL,
    end_time          TIME NOT NULL,
    slot_duration_min INT DEFAULT 90,   -- каждые 90 мин — новый слот
    is_working        BOOLEAN DEFAULT TRUE,

    UNIQUE (master_id, day_of_week)    -- у мастера один шаблон на каждый день
);


-- ============================================================
-- 7. SLOT_OVERRIDES — исключения из расписания
-- ============================================================
-- Метафора: стикеры «занято» на конкретных ячейках календаря.
-- «15 мая — отпуск» или «20 мая в 12:00 — занято».

CREATE TABLE slot_overrides (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,

    date        DATE NOT NULL,
    time        TIME,              -- NULL = весь день недоступен
    is_blocked  BOOLEAN DEFAULT TRUE,
    reason      TEXT,              -- 'Отпуск', 'Личное дело'

    UNIQUE (master_id, date, time)
);


-- ============================================================
-- 8. CLIENTS — клиенты мастера
-- ============================================================
-- Метафора: записная книжка мастера. Полная изоляция —
-- один человек в Telegram может быть клиентом разных мастеров,
-- но каждый мастер видит только «свою» запись этого человека.

CREATE TABLE clients (
    id                  BIGSERIAL PRIMARY KEY,
    master_id           BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,

    telegram_user_id    BIGINT NOT NULL,   -- числовой ID пользователя в Telegram
    telegram_chat_id    BIGINT NOT NULL,   -- ID чата для отправки сообщений через бота мастера
    first_name          TEXT,
    last_name           TEXT,
    username            TEXT,              -- @username в Telegram (может отсутствовать)
    phone               TEXT,             -- из requestContact(), может быть NULL

    -- Приватные заметки мастера (клиент их НЕ видит)
    master_notes        TEXT,

    -- Статистика (денормализовано для быстрого показа в карточке клиента)
    visits_count        INT DEFAULT 0,
    last_visit_at       DATE,

    created_at          TIMESTAMPTZ DEFAULT NOW(),

    -- Один и тот же человек не может дважды попасть в базу одного мастера
    UNIQUE (master_id, telegram_user_id)
);

CREATE INDEX idx_clients_master ON clients(master_id);


-- ============================================================
-- 9. BOOKINGS — записи на приём
-- ============================================================
-- Метафора: журнал записи в салоне. Каждая строка = один визит.
-- Важно: храним снимок услуги (название, цена) на момент записи,
-- потому что мастер может потом изменить прайс.

CREATE TABLE bookings (
    id              BIGSERIAL PRIMARY KEY,
    master_id       BIGINT NOT NULL REFERENCES masters(id),
    client_id       BIGINT NOT NULL REFERENCES clients(id),
    service_id      BIGINT REFERENCES services(id) ON DELETE SET NULL,

    -- Снимок данных услуги на момент записи
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

    -- Флаги напоминаний (scheduler помечает TRUE после отправки)
    reminder_24h_sent   BOOLEAN DEFAULT FALSE,
    reminder_2h_sent    BOOLEAN DEFAULT FALSE,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bookings_master_date ON bookings(master_id, date);
CREATE INDEX idx_bookings_client ON bookings(client_id);
-- Частичный индекс для scheduler: только записи у которых ещё не отправлено напоминание
CREATE INDEX idx_bookings_reminders ON bookings(date, time, status)
    WHERE reminder_24h_sent = FALSE OR reminder_2h_sent = FALSE;


-- ============================================================
-- 10. REVIEWS — отзывы клиентов
-- ============================================================

CREATE TABLE reviews (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    client_id   BIGINT REFERENCES clients(id) ON DELETE SET NULL,
    booking_id  BIGINT REFERENCES bookings(id) ON DELETE SET NULL,

    rating          INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text            TEXT,
    service_name    TEXT,      -- снимок названия услуги (на случай её удаления)

    is_visible      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 11. SUBSCRIPTIONS — история платежей (Telegram Stars)
-- ============================================================
-- Метафора: квитанции об оплате. Каждая строка = один платёж.

CREATE TABLE subscriptions (
    id                          BIGSERIAL PRIMARY KEY,
    master_id                   BIGINT NOT NULL REFERENCES masters(id),

    telegram_payment_charge_id  TEXT UNIQUE NOT NULL,  -- уникальный ID платежа от Telegram
    stars_amount                INT NOT NULL,
    period_months               INT NOT NULL DEFAULT 1,

    starts_at                   TIMESTAMPTZ NOT NULL,
    expires_at                  TIMESTAMPTZ NOT NULL,

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 12. FAQ_ITEMS — база знаний бота-консультанта
-- ============================================================
-- Метафора: шпаргалка для бота. Клиент спрашивает «сколько держится
-- гель-лак?» → бот ищет похожий вопрос и отвечает автоматически.

CREATE TABLE faq_items (
    id          BIGSERIAL PRIMARY KEY,
    master_id   BIGINT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,

    question    TEXT NOT NULL,   -- 'Сколько держится гель-лак?'
    answer      TEXT NOT NULL,   -- 'Покрытие держится 2–3 недели...'
    sort_order  INT DEFAULT 0
);


-- ============================================================
-- 13. MASTER_SETTINGS — настройки мастера
-- ============================================================
-- Метафора: «Настройки» в приложении. Один мастер = одна строка.
-- Создаётся автоматически при онбординге с дефолтными значениями.

CREATE TABLE master_settings (
    master_id                   BIGINT PRIMARY KEY REFERENCES masters(id) ON DELETE CASCADE,

    cancellation_hours          INT DEFAULT 24,         -- бесплатная отмена за N часов до записи
    reminder_24h_enabled        BOOLEAN DEFAULT TRUE,
    reminder_2h_enabled         BOOLEAN DEFAULT TRUE,
    welcome_message             TEXT DEFAULT 'Добро пожаловать! Я помогу вам записаться.',
    booking_confirm_message     TEXT DEFAULT 'Ваша запись подтверждена! Ждём вас.',
    days_advance_booking        INT DEFAULT 30,         -- запись не дальше чем на N дней вперёд
    forward_unknown_to_master   BOOLEAN DEFAULT TRUE    -- пересылать мастеру неизвестные сообщения
);


-- ============================================================
-- TRIGGERS (автоматические действия при изменении данных)
-- ============================================================

-- Trigger 1: Автоматически обновлять поле updated_at в masters
-- Метафора: штамп «последнее изменение» на документе.

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_masters_updated_at
    BEFORE UPDATE ON masters
    FOR EACH ROW
    EXECUTE FUNCTION fn_set_updated_at();


-- Trigger 2: Пересчитывать рейтинг мастера при каждом новом/изменённом отзыве
-- Метафора: кассовый аппарат — сам пересчитывает сумму когда добавляют товар.
-- Вместо того чтобы считать AVG каждый раз при запросе профиля,
-- мы держим готовый результат в таблице masters (денормализация).

CREATE OR REPLACE FUNCTION fn_recalculate_master_rating()
RETURNS TRIGGER AS $$
DECLARE
    v_master_id     BIGINT;
    v_avg           DECIMAL(2,1);
    v_count         INT;
    v_breakdown     JSONB;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_master_id := OLD.master_id;
    ELSE
        v_master_id := NEW.master_id;
    END IF;

    SELECT
        COALESCE(ROUND(AVG(rating)::numeric, 1), 0),
        COUNT(*),
        jsonb_build_object(
            '5', COUNT(*) FILTER (WHERE rating = 5),
            '4', COUNT(*) FILTER (WHERE rating = 4),
            '3', COUNT(*) FILTER (WHERE rating = 3),
            '2', COUNT(*) FILTER (WHERE rating = 2),
            '1', COUNT(*) FILTER (WHERE rating = 1)
        )
    INTO v_avg, v_count, v_breakdown
    FROM reviews
    WHERE master_id = v_master_id AND is_visible = TRUE;

    UPDATE masters
    SET
        rating           = v_avg,
        reviews_count    = v_count,
        rating_breakdown = v_breakdown
    WHERE id = v_master_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reviews_rating
    AFTER INSERT OR UPDATE OR DELETE ON reviews
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalculate_master_rating();


-- ============================================================
-- ROW LEVEL SECURITY (RLS) — защита данных на уровне БД
-- ============================================================
-- Метафора: турникет в офисном здании.
-- Даже если кто-то узнает адрес базы данных, без правильного
-- «пропуска» (service_role ключа) он ничего не прочитает.
--
-- Наш FastAPI-бэкенд подключается через service_role ключ,
-- который ОБХОДИТ RLS — бэкенд видит всё.
-- Прямой доступ через anon/authenticated ключи — полностью закрыт.
-- ============================================================

ALTER TABLE themes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE masters         ENABLE ROW LEVEL SECURITY;
ALTER TABLE services        ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_photos  ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_schedule   ENABLE ROW LEVEL SECURITY;
ALTER TABLE slot_overrides  ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients         ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings        ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews         ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE faq_items       ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_settings ENABLE ROW LEVEL SECURITY;

-- Политика: anon и authenticated роли не имеют НИКАКОГО доступа.
-- В Supabase: отсутствие политики при включённом RLS = запрет на всё.
-- service_role обходит RLS автоматически — ему политики не нужны.


-- ============================================================
-- REVOKE — дополнительная защита публичной схемы
-- ============================================================
-- Убираем права по умолчанию для anon/authenticated ролей
-- на все таблицы в публичной схеме.

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
