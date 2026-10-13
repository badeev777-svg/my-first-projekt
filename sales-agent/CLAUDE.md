# sales-agent

ИИ-продажник Badeev Agency по ТЗ [ai-sales-build-brief.md](ai-sales-build-brief.md): движок + сменный каталог (`content/`), GigaChat3.5 через cloud.ru, гибридный маршрутизатор, 6 навыков в `skills/`.

- Спецификация: [docs/superpowers/specs/2026-10-13-sales-agent-design.md](docs/superpowers/specs/2026-10-13-sales-agent-design.md)
- План и статус: [PLAN.md](PLAN.md)

## Правила
- Ничего не придумываем: цены, сроки, результаты — только из `content/` с `approved: true`.
- Цены считает код, не модель. Переходы состояний и создание заявок — только код.
- Ключи только в `.env` (не в git). Подключение к cloud.ru — как в `../rag-demo/app/cloudru.py`.
- Граница v1 — локальный прототип; деплой, каналы, CRM — только с согласия Александра.
- `../Manager-saler/` — старая версия, к удалению; не развивать.
