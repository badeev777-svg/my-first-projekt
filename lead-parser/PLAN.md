# Lead Parser — План развития

**Дата создания:** 2026-05-30  
**Статус:** В разработке

---

## ✅ Завершено (Phase 1)

- [x] FL.ru RSS парсер
- [x] Habr RSS парсер
- [x] Kwork.ru RSS парсер
- [x] Claude AI анализ (релевантность, теги, резюме, бюджет)
- [x] Telegram Bot уведомления
- [x] Веб-интерфейс (поиск, фильтры, экспорт CSV/JSON)
- [x] Авторизация админ-панели
- [x] Развертывание на production сервер (155.212.208.194)

---

## ⏳ Планируется (Phase 2)

### 1. Analytics Dashboard
**Описание:** Дашборд со статистикой по источникам  
**Статус:** ✅ ЗАВЕРШЕНО

**Реализовано:**
- [x] Графики: лиды по источникам, релевантность, тренд за 14 дней
- [x] KPI: всего, сегодня, средняя релевантность, средний бюджет
- [x] Таблица сравнения: цена, качество, скорость по платформам
- [x] Тренды: 14-дневный график активности
- [x] Экспорт в CSV

**Дата завершения:** 2026-05-28

---

### 2. CRM Integration

#### 2.1 Lead Action History (MVP)
**Описание:** История действий с лидами  
**Статус:** ✅ ЗАВЕРШЕНО (2026-05-28)

**Реализовано:**
- [x] Модель LeadAction: action_type, old_value, new_value, changed_by, changed_at
- [x] API: PATCH /leads/{id}/status, GET /leads/{id}/actions
- [x] UI: статус dropdown + история modal на странице лидов
- [x] Логирование: автоматическая запись всех изменений

**Код:**
- LeadAction model: [app/database.py:54-64](app/database.py#L54-L64)
- Status API: [app/web/routes.py:390-445](app/web/routes.py#L390-L445)
- UI + Modal: [app/web/templates/index.html:93-195](app/web/templates/index.html#L93-L195)

---

#### 2.2 Lead Assignment & Deal Tracking
**Описание:** Назначение исполнителей и трекинг конверсии  
**Статус:** ✅ ЗАВЕРШЕНО (2026-05-28)

**Реализовано:**
- [x] Поле `assigned_to` в Lead (никнейм исполнителя или null)
- [x] Поле `deal_value` в Lead (сумма сделки, если заключена)
- [x] Поле `deal_stage` в Lead (lead, negotiation, won, lost) — enum DealStage
- [x] UI: deal modal с полями для назначения, стадии, суммы
- [x] История действий: assigned, deal_stage_change, deal_value_change
- [x] Кнопка 💼 для открытия modal

**Код:**
- DealStage enum + Lead fields: [app/database.py:23-30, 56-58](app/database.py)
- API endpoints: [app/web/routes.py:411-490](app/web/routes.py)
- UI + Modal + JS: [app/web/templates/index.html:93-115, 152-191, 233-289](app/web/templates/index.html)

---

#### 2.3 Conversion Metrics & Filters
**Описание:** Метрики конверсии на аналитике и фильтры по исполнителям  
**Статус:** ✅ ЗАВЕРШЕНО (2026-05-28)

**Реализовано:**
- [x] Метрика конверсии на аналитике: % лидов со стадией won
- [x] Среднее значение сделки (deal_value для won)
- [x] Фильтр по исполнителю на странице лидов
- [x] Таблица по исполнителям: кол-во, конверсия %, avg deal value
- [x] KPI карточки: conversion_rate, won_count, avg_deal_value

**Код:**
- Analytics metrics + assignees query: [app/web/routes.py:300-350](app/web/routes.py)
- Analytics UI: [app/web/templates/analytics.html:62-130](app/web/templates/analytics.html)
- Index filter: [app/web/routes.py:100-145](app/web/routes.py)
- Index dropdown: [app/web/templates/index.html:29-34](app/web/templates/index.html)

---

### 3. Telegram Premium + Userbot
**Описание:** Сбор лидов из Telegram каналов  
**Условие:** Только если будет Telegram Premium  
**Задачи:**
- [ ] Получить Telegram Premium
- [ ] Зарегистрировать приложение на my.telegram.org
- [ ] Реактивировать auth_telegram.py
- [ ] Раскомментировать fetch_telegram_leads в collector.py
- [ ] Тестирование

**Примерный объем:** 1-2 часа (при наличии Premium)  
**Приоритет:** 🟢 Низкий (опционально)

---

### 4. Profi.ru + VK парсинг
**Описание:** Playwright для JS-рендеринга Profi.ru, VK Groups API для постов с заказами  
**Статус:** ✅ ЗАВЕРШЕНО (2026-06-06)

**Реализовано:**
- [x] `profi.py` — полный Playwright скрапер (Next.js JSON payload + DOM fallback)
- [x] 6 поисковых запросов: разработка сайта, лендинг, интернет-магазин, верстка, SEO, создание сайта
- [x] `vk.py` — VK Groups API, читает посты из публичных групп с заказами
- [x] Playwright + Chromium добавлены в Docker образ
- [x] `settings_store.py` — динамические настройки фильтров (keywords, budget, vk_groups) без перезапуска
- [x] `filter.py` — читает из settings_store, добавлен max_budget

**Код:**
- Profi.ru scraper: [app/scrapers/profi.py](app/scrapers/profi.py)
- VK scraper: [app/scrapers/vk.py](app/scrapers/vk.py)
- Settings store: [app/settings_store.py](app/settings_store.py)

---

## 📋 Общая дорожная карта

```
2026-05-30: ✅ Phase 1 завершена
          └─ 3 источника, Telegram Bot, Web UI, Production

2026-05-28: ✅ Phase 2 завершена
          ├─ Analytics Dashboard ✅
          │  ├─ KPI (4), Charts (3), Platform Comparison
          │  └─ CSV Export
          └─ CRM Integration ✅
             ├─ Lead Action History
             ├─ Deal Assignment & Tracking
             └─ Conversion Metrics & Filters

2026-06-06: ✅ Phase 3 — Расширение источников
          ├─ Profi.ru парсер ✅ (Playwright, Next.js JSON + DOM fallback)
          ├─ VK Groups API ✅ (посты с заказами)
          └─ settings_store ✅ (динамические фильтры без перезапуска)

2026-06-??: 🔄 Phase 4 — Опционально
          ├─ /settings UI (редактор keywords/budget в браузере)
          └─ LinkedIn интеграция (если нужны B2B)
```

---

## 💾 Текущее состояние

**Источники:** 5 (FL.ru, Kwork, Profi.ru, VK, Telegram*)  
**Интервал:** 10 минут  
**Лидов/день:** ~50-100+  
**Server:** 155.212.208.194:8000/leads  
**Database:** SQLite (можно мигрировать на PostgreSQL)  

---

## 🔄 Миграция AI-анализа: OpenRouter/Claude Haiku → GigaChat (cloud.ru) — 2026-07-31

**Статус:** Код готов, требуется реальный API-ключ и тест на живых данных.

**Причина:** уход от OpenRouter (риск WAF-блокировки с российских IP, как в других проектах) в сторону российского провайдера.

**Что сделано:**
- [app/analyzer.py](app/analyzer.py) — переписан на cloud.ru Foundation Models API (OpenAI-совместимый Bearer-запрос вместо OpenRouter)
- [app/config.py](app/config.py) — `GIGACHAT_API_KEY`, `GIGACHAT_MODEL` (default `ai-sage/GigaChat3-10B-A1.8B`), `GIGACHAT_API_URL` (`https://foundation-models.api.cloud.ru/v1/chat/completions`)
- [.env.example](.env.example) — обновлена инструкция получения ключа

**Как получить ключ:** личный кабинет cloud.ru → Пользователи → Сервисные аккаунты → создать аккаунт → API-ключи → выбрать сервис Foundation Models → сохранить Key Secret (показывается один раз).

**Сделано (2026-07-31):**
- [x] Создан сервисный аккаунт `lead-parser-gigachat` в cloud.ru (роль `ml_inference_ai_marketplace.apikey-limit.user`, сервис Foundation Models)
- [x] Получен и вписан `GIGACHAT_API_KEY` в локальный `.env`
- [x] Пополнен баланс cloud.ru (грант "4000 Б" не покрывает Foundation Models — нужен реальный ₽-баланс)
- [x] `analyze_lead()` протестирован на реальном лиде: корректный JSON, `relevance_score=85`, теги, кириллица в `summary` без искажений

- [x] `GIGACHAT_API_KEY`/`GIGACHAT_MODEL` вписаны в `.env.local` на production-сервере (155.212.208.194), задеплоен обновлённый код через `deploy.py`, контейнер пересоздан
- [x] Подтверждено по логам прод-сервера: лиды анализируются через GigaChat (`Analyzed lead #NNN, relevance=...`), ошибок нет

**Статус: миграция завершена ✅ (2026-07-31)**

---

## 🔀 Перенос уведомлений Telegram → MAX (черновой план, 2026-08-11)

**Статус:** Отложено, разбираться позже.

**Причина:** переход на российский мессенджер MAX.

**Что переносится:** только исходящие уведомления из [app/notifier.py](app/notifier.py) (Telegram Bot API → MAX Bot API).

**Что НЕ переносится:** [app/scrapers/telegram_poller.py](app/scrapers/telegram_poller.py) — Telethon-парсинг Telegram-каналов остаётся как есть, это источник данных, физически привязанный к Telegram.

**Найденные детали MAX Bot API (dev.max.ru):**
1. **Регистрация бота:** @MasterBot в MAX → создать бота (ник оканчивается на `_bot`/`bot`, имя ≤16 символов) → токен из карточки настроек бота
2. **Базовый URL:** `https://platform-api2.max.ru`
3. **Отправка сообщения:** `POST /messages`
4. **Авторизация:** заголовок `Authorization: <token>` (НЕ query-параметр, в отличие от Telegram)
5. **Тело запроса:** `chat_id`/`user_id` (аналог `BOT_CHAT_ID`), `text`, `format: "html"` или `"markdown"` (аналог `parse_mode`)
6. **Входящие/webhook:** `POST /subscriptions` (webhook) или `GET /updates` (long polling)

**Открытые вопросы (уточнить перед реализацией):**
- [ ] Как получить `chat_id`/`user_id` получателя в MAX (в Telegram — через `getUpdates`/`/start`) — в найденной документации явно не описано
- [ ] Совпадение поддерживаемых HTML/Markdown тегов с Telegram (проверить `<a href>`, `<b>` и т.д.)
- [ ] Решить: полная замена `BOT_TOKEN`/`BOT_CHAT_ID` или параллельная отправка в Telegram + MAX на переходный период

**Задачи при реализации:**
- [ ] Зарегистрировать бота через @MasterBot, получить токен
- [ ] Добавить `MAX_BOT_TOKEN`, `MAX_CHAT_ID` в [app/config.py](app/config.py) и `.env`
- [ ] Переписать/расширить `notify_new_lead()` в [app/notifier.py](app/notifier.py) под MAX API
- [ ] Задеплоить, обновить `.env.local` на production-сервере

**Источники:**
- https://dev.max.ru/docs-api
- https://dev.max.ru/docs/chatbots/bots-coding/js

---

## 📝 Примечания

- Система stable и ready for production
- RSS источники надежны
- Telegram Bot работает
- Админ-панель защищена паролем
- Все логи в Docker контейнере

**Next meeting:** Когда захочешь начать Phase 2
