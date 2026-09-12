# Content-Agent Subagent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать глобальный саб-агент Claude Code `content-agent`, установить три источника маркетинговых/SMM-скиллов глобально, и проверить, что агент виден и корректно ограничен по правам.

**Architecture:** Три CLI-установки скиллов/плагина в `~/.claude` (глобально) + один новый markdown-файл саб-агента `~/.claude/agents/content-agent.md`. Никакого кода/тестов в привычном смысле — верификация через CLI-команды листинга и ручной тестовый вызов агента.

**Tech Stack:** Claude Code CLI (`claude plugin`), `npx skills` CLI, Markdown с YAML frontmatter.

**Spec:** [docs/superpowers/specs/2026-09-12-content-agent-subagent-design.md](../specs/2026-09-12-content-agent-subagent-design.md)

---

### Task 1: Установить Marketing Skills (coreyhaines31)

**Files:**
- Затрагивает: `~/.claude/skills/` (создаётся CLI-инструментом, путь не трогаем вручную)

- [ ] **Step 1: Запустить установку**

Run:
```bash
npx skills add coreyhaines31/marketingskills -g -a claude-code -y
```
Expected: команда завершается без ошибок (exit code 0), в выводе упоминается установка скиллов в глобальную директорию Claude Code.

- [ ] **Step 2: Проверить, что скиллы появились**

Run:
```bash
ls ~/.claude/skills | grep -i -E "seo|copywrit|conversion|growth" | head -5
```
Expected: непустой список — хотя бы несколько директорий/файлов с маркетинговыми скиллами.

- [ ] **Step 3: Commit**

Установка глобальная (вне git-репозитория) — коммитить нечего, пропускаем git commit для этого таска.

---

### Task 2: Установить Social Media Skills

**Files:**
- Затрагивает: `~/.claude/skills/`

- [ ] **Step 1: Запустить установку**

Run:
```bash
npx skills add social-media-skills/skills -g -a claude-code -s '*' -y
```
Expected: exit code 0, лог установки всех (`-s '*'`) скиллов из репозитория.

- [ ] **Step 2: Проверить, что скиллы появились**

Run:
```bash
ls ~/.claude/skills | grep -i -E "platform|brand-voice|content-calendar" | head -5
```
Expected: непустой список скиллов из категорий Foundation/Planning/Platform playbooks.

- [ ] **Step 3: Commit**

Глобальная установка — пропускаем git commit.

---

### Task 3: Установить Knowledge Work Plugins (marketing)

**Files:**
- Затрагивает: `~/.claude/plugins/` (marketplace + установленный плагин)

- [ ] **Step 1: Добавить marketplace**

Run:
```bash
claude plugin marketplace add anthropics/knowledge-work-plugins
```
Expected: exit code 0, подтверждение добавления marketplace `knowledge-work-plugins`.

- [ ] **Step 2: Установить плагин marketing**

Run:
```bash
claude plugin install marketing@knowledge-work-plugins
```
Expected: exit code 0, подтверждение установки плагина `marketing`.

- [ ] **Step 3: Проверить установку**

Run:
```bash
claude plugin list
```
Expected: в списке присутствует `marketing@knowledge-work-plugins` со статусом enabled/installed.

- [ ] **Step 4: Commit**

Глобальная установка — пропускаем git commit.

---

### Task 4: Создать файл саб-агента `content-agent`

**Files:**
- Create: `~/.claude/agents/content-agent.md`

- [ ] **Step 1: Проверить, что директория существует**

Run:
```bash
ls ~/.claude/agents/
```
Expected: директория существует (там уже могут быть другие саб-агенты типа `code-reviewer.md`, `designer.md` — см. системный список агентов проекта).

- [ ] **Step 2: Создать файл агента**

Создать `~/.claude/agents/content-agent.md` со следующим содержимым:

```markdown
---
name: content-agent
description: Пишет маркетинговый и SMM-контент для проектов пользователя (посты, треды, анонсы, кейсы) под конкретную платформу — Telegram, LinkedIn, X и т.д. Используй проактивно, когда пользователь просит написать пост, анонс фичи, контент-план или маркетинговый текст про один из его проектов.
tools: Read, Grep, Glob, WebSearch, WebFetch, Write
---

Ты — контент-маркетолог, отвечающий за продвижение проектов пользователя: SpeakBuddy (AI-тьютор английского в Telegram), Content Agent Bot (мультиагентный SMM-бот), primerka (виртуальная примерка), tg-beauty-catalog, портфолио и другие проекты из `knowledge/projects.md`.

## Перед написанием текста

1. Прочитай `knowledge/projects.md` в корне проекта пользователя (если доступен), чтобы понять, о каком проекте речь, его статус и аудиторию.
2. Если пользователь назвал конкретный проект — прочитай его `CLAUDE.md` и/или `Plan.md`/`README.md`, чтобы понять актуальные фичи и статус (production/в разработке).
3. Используй установленные скиллы по цепочке: foundation (бренд-войс/аудитория) → planning (контент-план) → writing (сам текст) → platform playbook (формат под конкретную платформу — Telegram/LinkedIn/X/Instagram и т.д.).

## Правила

- Язык по умолчанию — русский. Пиши на английском только если пользователь явно попросил (например, документация для международной аудитории).
- Готовый текст выдавай прямо в ответе.
- Черновик сохраняй в файл ТОЛЬКО по явной просьбе пользователя ("сохрани", "оформи в файл", "запиши черновик"). Путь: `<project>/content-drafts/YYYY-MM-DD-<slug>.md`, где `<project>` — корень текущего проекта, `<slug>` — короткий kebab-case заголовок поста.
- Никогда не редактируй код, конфиги, `.env` или любые файлы вне `content-drafts/`. У тебя нет доступа к Bash и Edit — не пытайся выполнять команды или менять существующий код.
- Если не хватает контекста о проекте (нет `knowledge/projects.md` и пользователь не описал проект) — спроси у пользователя, о чём именно писать, вместо того чтобы выдумывать факты о проекте.
```

- [ ] **Step 3: Проверить синтаксис frontmatter**

Run:
```bash
head -5 ~/.claude/agents/content-agent.md
```
Expected: видны три строки frontmatter (`---`, `name:`, `description:`, `tools:`, `---`) без опечаток в YAML.

- [ ] **Step 4: Commit**

Файл в `~/.claude` — не часть git-репозитория проекта, коммитить в проектный репозиторий не нужно. Пропускаем git commit.

---

### Task 5: Проверить, что агент виден и ограничен по правам

**Files:**
- Не создаёт и не изменяет файлы проекта.

- [ ] **Step 1: Убедиться, что агент появился в списке доступных**

В новой сессии Claude Code (или после перезапуска текущей) агент `content-agent` должен появиться в системном списке "Available agent types for the Agent tool" наравне с `code-reviewer`, `designer` и т.д. Проверить визуально в следующем системном промпте — специальной команды для листинга саб-агентов нет.

- [ ] **Step 2: Тестовый вызов на реальной задаче**

Вызвать через Agent tool с `subagent_type: "content-agent"` задачу вида: "напиши короткий анонс-пост для Telegram про то, что SpeakBuddy перешёл в Phase 2" (без слова "сохрани").
Expected: агент возвращает готовый текст поста на русском в ответе, НЕ создаёт файлов (т.к. сохранение не запрашивалось), не пытается использовать Bash/Edit.

- [ ] **Step 3: Тестовый вызов с сохранением черновика**

Повторить похожий запрос, но с фразой "...и сохрани черновик".
Expected: агент создаёт файл `content-drafts/<дата>-<slug>.md` в текущем проекте с текстом поста, ничего больше не меняет.

- [ ] **Step 4: Ревью прав доступа**

Run:
```bash
grep -A3 "^tools:" ~/.claude/agents/content-agent.md
```
Expected: список инструментов строго `Read, Grep, Glob, WebSearch, WebFetch, Write` — без `Bash` и `Edit`.

- [ ] **Step 5: Commit**

Нет изменений в git-репозитории проекта (кроме возможного тестового `content-drafts/` файла из Step 3 — по желанию пользователя можно закоммитить или удалить как тестовый артефакт). Ничего коммитить автоматически не требуется.

---

## Self-Review Notes

- **Spec coverage:** установка трёх источников скиллов (Task 1-3), создание файла агента с точным содержимым frontmatter и тела (Task 4), проверка видимости/прав/поведения (Task 5) — покрывает все разделы спеки.
- **No placeholders:** все команды и содержимое файла агента даны полностью, без TBD.
- **Consistency:** путь `~/.claude/agents/content-agent.md`, набор tools и путь черновиков `<project>/content-drafts/` совпадают со спекой и между тасками.
