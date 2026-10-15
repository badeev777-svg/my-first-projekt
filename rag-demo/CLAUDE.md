# rag-demo

Демо для встреч с клиентами: загрузка PDF/DOCX в браузере → ответы по документам со ссылкой на источник. Модели — cloud.ru Foundation Models (bge-m3, bge-reranker-v2-m3, GigaChat3.5-Reasoning).

- Спецификация: [docs/superpowers/specs/2026-09-26-rag-demo-design.md](docs/superpowers/specs/2026-09-26-rag-demo-design.md)
- План и статус: [PLAN.md](PLAN.md)

## Правила
- Ничего не придумываем: бот отвечает только по документам; мы в коде/доках не пишем непроверенных фактов.
- Файлы клиентов не пишутся на диск и не логируются.
- Ключи только в `.env` (не в git).
- Подключение к cloud.ru — как в `../lead-parser/app/config.py` (OpenAI-совместимый API).
