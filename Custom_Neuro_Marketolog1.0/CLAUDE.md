# Custom Neuro Marketolog — Project Context

## Что это
Веб-продукт + Telegram-бот: персональный AI-маркетолог для клиентов Badeev Agency.
Клиент проходит 15-минутную диагностику, в конце получает CTA с выходом на Александра.

## Архитектура
- **GPT_SYSTEM/** — инструкции и knowledge base для 3-агентного пайплайна.
  В продакшене (бот и веб-версия для клиентов) подключён и вызывается только агент 1 —
  GPT_2 и GPT_3 являются частью личного/внутреннего контура (не для клиентской поставки,
  не импортируются кодом веб-приложения)
  - `GPT_1_NeuroMarketing/Instructions.txt` — промпт Нейро-Маркетолога (используется в боте и веб-версии, продакшн)
  - `GPT_2_AI_Architect/Instructions.txt` — промпт AI-Архитектора (личный контур, не задействован в проде)
  - `GPT_3_AI_Sales_Engineer/Instructions.txt` — промпт AI Sales Engineer (личный контур, не задействован в проде)
  - `knowledge/` — база знаний по темам (marketing, sales, ai_agents, crm, automation, cases, offers, templates)
- **bot/** — Telegram-бот (aiogram 3.x), агент Нейро-Маркетолога
- **web/** — FastAPI + лендинг + встроенный чат
  - `web/app/` — FastAPI backend (config, agent, routers/chat)
  - `web/static/` — index.html, style.css, chat.js

## Стек
| Слой | Технология |
|------|-----------|
| Backend | FastAPI + uvicorn |
| LLM | OpenRouter → claude-sonnet-4-6 |
| Telegram | aiogram 3.x |
| Frontend | Vanilla HTML/CSS/JS (тёмная тема, Inter font) |
| Сессии | Cookie UUID, in-memory dict |
| Config | pydantic-settings (.env) |

## Ключевые константы
- `HANDOFF_MARKER = "ВХОДНЫЕ ДАННЫЕ ДЛЯ AI-АРХИТЕКТОРА"` — детект завершения диагностики
- После handoff → `finished: true` → в ответ добавляется `contact_link` → CTA-блок в UI
- `CONTACT_LINK=https://t.me/badeev777` в .env

## Запуск (web)
```bash
cd web
cp .env.example .env  # вставить OPENROUTER_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Запуск (bot)
```bash
cd bot
cp .env.example .env  # BOT_TOKEN + OPENROUTER_API_KEY
pip install -r requirements.txt
python main.py
```
