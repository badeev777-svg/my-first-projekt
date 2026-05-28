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

### 4. Профи.ру парсер (заморожен)
**Описание:** Добавить четвертый источник через веб-скрейпинг  
**Статус:** ❌ ЗАМОРОЖЕН — требует Playwright/Selenium

**Почему не реализовано:**
- Profi.ru использует JavaScript рендеринг (SPA)
- Простой HTTP + BeautifulSoup не работает
- Решение требует: Playwright/Selenium (~500MB) или скрытое API
- Сейчас хватает 3 источников (FL.ru, Habr, Kwork) — ~50 лидов/день

**Если понадобится в будущем:**
- Добавить Playwright в зависимости
- Реализовать браузер-like парсер в `app/scrapers/profi.py`
- Или найти API Profi.ru через DevTools анализ

**Примерный объем:** 4-6 часов  
**Приоритет:** 🔴 Очень низкий (лишь если нужно 100+ лидов/день)

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

2026-06-??: 🔄 Phase 3 — Расширение (опционально)
          ├─ Профи.ру парсер ❌ заморожен (требует Playwright)
          ├─ Telegram Premium + userbot (если будет)
          └─ LinkedIn интеграция (если нужны B2B)
```

---

## 💾 Текущее состояние

**Источники:** 3 (FL.ru, Habr, Kwork)  
**Интервал:** 10 минут  
**Лидов/день:** ~30-50 (质量высокая)  
**Server:** 155.212.208.194:8000/leads  
**Database:** SQLite (можно мигрировать на PostgreSQL)  

---

## 📝 Примечания

- Система stable и ready for production
- RSS источники надежны
- Telegram Bot работает
- Админ-панель защищена паролем
- Все логи в Docker контейнере

**Next meeting:** Когда захочешь начать Phase 2
