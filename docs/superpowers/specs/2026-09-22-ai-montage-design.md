# ai-montage — дизайн v1

**Дата:** 2026-09-22
**Статус:** утверждён к планированию

## Цель

Новый отдельный проект `ai-montage` — локальный движок AI-монтажа видео, минимальный рабочий цикл: от исходного видео до проверенного MP4, без обязательных платных API. Источник требований: PDF-гайд "AI Montage / Field Guide" (12-этапный процесс, 3-слойная архитектура движка).

**Кому и зачем:** пользователю для сборки коротких вертикальных роликов (Reels/Shorts) двумя маршрутами из одного движка — Talking-Head (спикер в кадре) и Motion-Reel (без камеры, только графика).

**Критерий готовности v1:** движок собирает нейтральное синтетическое demo-видео в `final/demo.mp4`, проходит `qa` (полный decode, верные FPS/длительность/звук) без участия человека на техническом уровне — только явное `approve` перед финальным рендером.

## Расположение и стек

- Путь: `c:\Users\User\Documents\Projekt\my-first-projekt\ai-montage`
- Node.js 20+ (JavaScript, без TypeScript в v1 — меньше сборочной сложности)
- React + Remotion 4 (программные сцены, рендер через Chromium)
- Python 3 + venv + faster-whisper (локальная транскрипция с таймкодами слов)
- FFmpeg / FFprobe (монтаж, измерение, финальный MP4)
- AJV + JSON Schema (валидация монтажного листа до рендера)

Ничего из этого не установлено на машине заранее — `check-env` диагностирует, установку по факту выполняет агент в сессии с подтверждением пользователя (см. security-заметку в CLAUDE.md).

## Архитектура: 3 слоя

1. **Тема** (`remotion/src/Theme.js`) — цвета, шрифты, safe-zone, радиусы, характер движения. Отвечает "как выглядит".
2. **Композиция** (`remotion/src/scenes/*.jsx`) — React-компоненты сцен, знают только как рисовать данные, которые им передали.
3. **Монтажный лист** (JSON) — что и когда показать: таймкоды, тексты, типы сцен, звуковые режимы. Не знает про тему.

Слои не смешиваются: один и тот же JSON-план можно отрендерить в другой теме без пересборки сцен.

## Типы сцен v1 (закрывают оба маршрута)

| Тип | Что рисует | Маршрут |
|---|---|---|
| `speaker` | Видео спикера + анимированные субтитры по словам | Talking-Head |
| `title-card` | Крупный смысловой заголовок/подзаголовок, motion-графика | Motion-Reel, Talking-Head |
| `b-roll` | Статичное изображение или видео-вставка поверх/вместо основного плана | оба |

Комбинация `speaker` + `title-card` + `b-roll` = Talking-Head-ролик. Комбинация `title-card` + `b-roll` без `speaker` = Motion-Reel. Один движок, разная последовательность сцен в JSON-плане — не два разных кодовых пути.

## Структура репозитория

```
ai-montage/
  package.json
  requirements.txt              # python-зависимости (faster-whisper и т.д.)
  scripts/
    cli.js                      # точка входа: node scripts/cli.js <command>
    check-env.js                # диагностика node/python/ffmpeg/ffprobe
    new-project.js              # создаёт projects/<id>/ + ffprobe-паспорт входа
    transcribe.js                # вызывает python/transcribe.py
    validate.js                 # AJV-проверка JSON-плана по schema
    preview.js                  # быстрый Remotion-рендер в previews/
    approve.js                  # фиксирует конкретную версию брифа
    render.js                   # финальный Remotion + ffmpeg рендер
    qa.js                       # ffprobe decode-check финального MP4
  python/
    transcribe.py                # faster-whisper: видео/аудио -> transcript.json
  remotion/
    src/
      Root.jsx
      Theme.js
      scenes/
        SpeakerScene.jsx
        TitleCardScene.jsx
        BRollScene.jsx
  schema/
    edit-plan.schema.json
  test/
    validate-brief.test.js       # assert-проверка валидного/невалидного брифа
  projects/                      # рабочие папки роликов, gitignored кроме .gitkeep
    <project-id>/
      input/ transcript/ brief/ assets/ previews/ renders/ final/
  README.md
  .gitignore
```

## Поток данных (стадии CLI)

`check-env` → `new-project --id <id> --input <path>` (создаёт папку, снимает ffprobe-паспорт исходника) → `transcribe --id <id>` (пишет `transcript/transcript.json` с таймкодом каждого слова) → **бриф собирается в чате с AI-агентом** из транскрипта + цели пользователя, сохраняется как `brief/v01.json` → `validate --id <id> --file brief/v01.json` (AJV против schema, стоп при ошибке) → `preview --id <id> --brief brief/v01.json` (быстрый Remotion-рендер, не финал) → `approve --id <id> --version v01` (копирует в `brief/v01-approved.json`, дальше файл не перезаписывается) → `render --id <id>` (полный Remotion + FFmpeg рендер из approved-брифа, звук сводится через FFmpeg) → `qa --id <id>` (ffprobe: полный decode без ошибок, FPS/длительность/наличие звука совпадают с брифом).

Версии брифов и рендеров не перезаписываются — каждый approve и render создаёт новый файл с версией в имени.

## JSON-план монтажа (упрощённая схема)

```json
{
  "projectId": "demo-01",
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "audioTrack": "master.mp4",
  "scenes": [
    { "type": "speaker", "start": 0, "end": 6.4, "audioMode": "sync" },
    { "type": "title-card", "start": 6.4, "end": 9.0, "title": "...", "subtitle": "...", "audioMode": "mute" },
    { "type": "b-roll", "start": 9.0, "end": 12.0, "media": "assets/clip.mp4", "audioMode": "mute" }
  ]
}
```

`schema/edit-plan.schema.json` требует: `type` — один из трёх известных, `start < end`, обязательные поля по типу сцены (`title` для `title-card`, `media` для `b-roll`), сцены не должны иметь дыр/наложений (проверяется в `validate.js` отдельно от JSON Schema, т.к. это кросс-элементное правило).

## Обработка ошибок

Каждая CLI-команда проверяет наличие результата предыдущего шага (ffprobe-паспорт входа, `transcript.json`, `*-approved.json`) и останавливается с понятным русскоязычным сообщением, если файла нет — не угадывает, не создаёт пустышки, не пропускает шаг молча. `render` отказывается запускаться без approved-брифа. `check-env` никогда не запускает установку сама — только печатает диагноз и рекомендацию.

## Тестирование

- `test/validate-brief.test.js` — assert-скрипт (без внешнего test-фреймворка) на паре примеров: валидный брифом проходит, брифом с дырой между сценами/отсутствующим обязательным полем — падает с понятной ошибкой.
- Приёмочный прогон v1: `check-env` → генерация нейтрального synthetic-видео (тестовый паттерн + тон через FFmpeg, без реальных материалов пользователя) → полный цикл команд до `final/demo.mp4` → `qa` подтверждает decode + корректные FPS/длительность/звук.
- Реальное видео со спикером пользователь предоставит позже отдельным прогоном — вне рамок v1.

## Явно вне рамок v1

Sidechain/ducking музыки, OpenCV-перекадрирование под лицо, Tesseract OCR, Pexels API, ElevenLabs, Playwright QA-робот — всё это из гайда, но добавляется отдельными итерациями поверх той же 3-слойной архитектуры, не меняя её.
