# SpeakBuddy — План развития (3 ботов)

## Архитектура проекта
**Целевая аудитория:** 3 сегмента  
1. **SpeakBuddy Schools** (позже) — школьники 4-11 класс, программа по учебнику
2. **SpeakBuddy Students** (сейчас) — студенты, разговорный английский
3. **SpeakBuddy Adults** (сейчас) — взрослые, разговорный английский, повышение уровня

---

## Фаза 1: SpeakBuddy Students + Adults (текущий код)
**Статус:** Phase 2 (Payments)

### Готовые фичи
✅ Регистрация с тестом уровня (A1-C2)  
✅ Диалоги со сценариями  
✅ Дневные лимиты (10 free, unlimited premium)  
✅ Интеграция Claude API с историей  
✅ YuKassa + Telegram Stars  

### Активные задачи
- [x] Разделение: Students vs Adults — единый бот, audience по выбору при /start
- [ ] Валидация платежей
- [ ] Логирование и мониторинг
- [ ] Voice messages (Phase 3)

---

## Фаза 2: SpeakBuddy Schools (будущее)
- [ ] Спецификация: программа по классам
- [ ] Грамматические упражнения + диалоги
- [ ] Система прогресса по темам
- [ ] Адаптированный прайсинг

---

## Различия Students vs Adults

| Аспект | Students | Adults |
|--------|----------|--------|
| **Сценарии** | Экзамены, общежитие, клубы, романтика, спорт, здоровье | Работа, бизнес, семья, путешествия |
| **Язык промпта** | Casual, friendly | Professional, business-ready |
| **Стартовый уровень** | A1 | A2+ |
| **Цена** | одинаковая | одинаковая |

## ✅ Реализация завершена (Вариант A)

### Этап 1: БД — Audience поле ✅
- `User.audience: String(10)` с дефолтом 'adults'
- Миграция: `alembic/versions/003_add_audience.py`

### Этап 2: Регистрация — выбор аудитории ✅
- `ASK_AUDIENCE` состояние добавлено
- Кнопки: "📚 Студент" / "👨‍💼 Взрослый" (на русском)
- Сохранение в `context.user_data["audience"]`

### Этап 3: Сценарии — разделены ✅
```
src/prompts/
├── scenarios_students.py     # Экзамены, общежитие, клубы, романтика, спорт, здоровье
├── scenarios_adults.py       # Работа, бизнес, семья, путешествия, светская беседа, карьера
└── system_prompts.py         # Координация по audience + level
```

### Этап 4: Промпты — адаптированы ✅
- `system_prompts.get_system_prompt(audience, scenario, level)`
- `AUDIENCE_CONTEXT` — описание тона и стиля
- `LEVEL_ADJUSTMENTS` — адаптация A1-C2

### Этап 5: Конфиг — единый токен ✅
```env
TELEGRAM_TOKEN=...             # Один токен, один бот
OPENROUTER_API_KEY=...         # OpenRouter (claude-3-5-sonnet)
```

**Запуск:**
```bash
python -m alembic upgrade head  # Применить миграции
python -m src.main               # Запустить бота
```

---

## Переход на YandexGPT (2026-07-03)

**Цель:** уйти от зарубежных сервисов (OpenRouter → YandexGPT)

### Что сделано
- [x] `src/config.py` — заменены `OPENROUTER_API_KEY` → `YANDEX_API_KEY` + `YANDEX_FOLDER_ID`
- [x] `src/services/claude.py` — endpoint и авторизация переключены на YandexGPT (`Api-Key`)
- [x] `.env.example` — обновлены переменные
- [x] Оптимизация токенов — история обрезается до последних 8 сообщений (`MAX_HISTORY_MESSAGES = 8`)

### Что нужно сделать
- [ ] Зайти на [console.yandex.cloud](https://console.yandex.cloud)
- [ ] Создать сервисный аккаунт → роль `ai.languageModels.user`
- [ ] Создать API-ключ → скопировать в `.env` как `YANDEX_API_KEY`
- [ ] Скопировать Folder ID → в `.env` как `YANDEX_FOLDER_ID`
- [ ] Протестировать бота: `/new` → диалог

### Настройки модели
```
# src/config.py
LLM_MODEL: str = "yandexgpt-lite/latest"   # дешевле
# или
LLM_MODEL: str = "yandexgpt/latest"         # качество выше
```

---

## 📋 Следующие шаги

- [ ] **Шаг 1** — Создать бота в BotFather
  - Читай: [CREATE_BOTS_GUIDE.md](CREATE_BOTS_GUIDE.md)
  - Сохрани токен в .env как TELEGRAM_TOKEN

- [ ] **Шаг 2** — Настроить YandexGPT (см. раздел выше)

- [ ] **Шаг 3** — Запустить и протестировать
  - `python -m alembic upgrade head`
  - `python -m src.main`
  - Проверить: /start → выбор аудитории → тест уровня → сценарии

---

**Статус:** 🎉 АРХИТЕКТУРА ГОТОВА (готовимся к тестированию)  
**Обновлено:** 2026-07-03
