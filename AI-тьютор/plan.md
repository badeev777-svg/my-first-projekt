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
- [ ] Разделение: Students vs Adults (промпты, сценарии, ценообразование)
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

### Этап 5: Конфиг — разные токены ✅
```env
AUDIENCE=students|adults        # Выбор аудитории
TELEGRAM_TOKEN_STUDENTS=...    # Токен для студентов
TELEGRAM_TOKEN_ADULTS=...      # Токен для взрослых
TELEGRAM_TOKEN=...             # Fallback
```

**Запуск:**
```bash
AUDIENCE=students python -m src.main  # Бот для студентов
AUDIENCE=adults python -m src.main    # Бот для взрослых
```

---

## 📋 Следующие шаги

- [ ] **Шаг 1** — Создать двух ботов в BotFather
  - Читай: [CREATE_BOTS_GUIDE.md](CREATE_BOTS_GUIDE.md)
  - Сохрани токены

- [ ] **Шаг 2** — Заполнить .env
  - TELEGRAM_TOKEN_STUDENTS
  - TELEGRAM_TOKEN_ADULTS
  - ANTHROPIC_API_KEY (Claude)

- [ ] **Шаг 3** — Тестировать
  - `AUDIENCE=students python -m src.main`
  - `AUDIENCE=adults python -m src.main`
  - Проверить: /start → выбор аудитории → тест уровня → сценарии

---

**Статус:** 🎉 АРХИТЕКТУРА ГОТОВА (готовимся к тестированию)  
**Обновлено:** 2026-05-23
