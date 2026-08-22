# Руководство клиента — AI-Маркетолог

## Что вы получили

Персональный AI-консультант, развёрнутый на вашем сервере. Система состоит из:

```
web/                    — веб-приложение (чат на вашем домене)
bot/                    — Telegram-бот (опционально)
GPT_SYSTEM/             — «мозг» системы: инструкции и база знаний
  GPT_1_NeuroMarketing/
    Instructions.txt    — главный промпт вашего AI-маркетолога
  knowledge/            — справочная база: кейсы, методики, шаблоны
deploy.sh               — скрипт первичной установки (уже выполнен)
```

---

## Управление системой

### Проверить, что всё работает
```bash
systemctl status neuro-marketolog
```
Статус `active (running)` — всё в порядке.

### Перезапустить после изменений
```bash
systemctl restart neuro-marketolog
```
Требуется после: изменения `.env`, редактирования `Instructions.txt`, добавления файлов в `knowledge/`.

### Посмотреть логи
```bash
journalctl -u neuro-marketolog -n 50 --no-pager
```

---

## Изменить брендинг

Все настройки — в файле `/opt/neuro-marketolog/web/.env`:

```bash
nano /opt/neuro-marketolog/web/.env
```

| Параметр | Что меняет |
|----------|-----------|
| `AGENT_NAME` | Имя AI в чате (заголовок, аватар) |
| `AGENT_INITIALS` | Аббревиатура в аватаре (2-3 буквы) |
| `AGENCY_NAME` | Название вашей компании (в футере) |
| `AGENCY_TAGLINE` | Подзаголовок компании |
| `CONTACT_LINK` | Ссылка на вас в CTA-кнопке (Telegram, WhatsApp) |
| `CHAT_ONLY_MODE` | `true` — только чат без лендинга |

После изменений: `systemctl restart neuro-marketolog`

---

## Добавить свои кейсы и материалы

База знаний AI-маркетолога — это `.md` файлы в папке `knowledge/`:

```bash
ls /opt/neuro-marketolog/GPT_SYSTEM/knowledge/
```

**Добавить новый кейс:**
1. Создайте файл: `nano /opt/neuro-marketolog/GPT_SYSTEM/knowledge/cases/Cases_MyCompany.md`
2. Напишите в свободном формате: проблема клиента → что сделали → результат
3. Перезапустите: `systemctl restart neuro-marketolog`

Система автоматически подхватит все `.md` файлы из папки `knowledge/` и использует их как контекст в диалоге.

---

## Изменить сценарий диагностики

Главный промпт — в файле:
```bash
nano /opt/neuro-marketolog/GPT_SYSTEM/GPT_1_NeuroMarketing/Instructions.txt
```

Здесь можно:
- Добавить специфику вашей компании, продуктов, географии
- Скорректировать вопросы диагностики
- Изменить критерии квалификации клиента

После изменений: `systemctl restart neuro-marketolog`

---

## Уведомления о завершённых диагностиках

Когда клиент завершает диагностику, система может отправлять уведомление вам в Telegram.

Настройка в `.env`:
```env
TG_BOT_TOKEN=токен_вашего_бота
TG_CHAT_ID=ваш_chat_id
```

Как получить `TG_CHAT_ID`: напишите боту `@userinfobot` в Telegram.

---

## Частые вопросы

**Чат перестал отвечать — что делать?**
```bash
journalctl -u neuro-marketolog -n 20 --no-pager
systemctl restart neuro-marketolog
```

**Как узнать, что кончился лимит API?**
В логах будет ошибка `429` или `402`. Пополните баланс в личном кабинете cloud.ru.

**Как обновить систему до новой версии?**
Свяжитесь с Badeev Agency — мы выполним обновление удалённо.

---

## Поддержка

**Badeev Agency — AI-автоматизация бизнеса**
- Telegram: [@badeev777](https://t.me/badeev777)
- Email: badeev777@gmail.com

Включённая поддержка: 30 дней после установки.
Платная поддержка после 30 дней: по договорённости.
