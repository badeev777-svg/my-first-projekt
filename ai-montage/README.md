# ai-montage

Локальный AI-движок монтажа коротких вертикальных роликов (Talking-Head и Motion-Reel) без обязательных платных API. Смысл сначала, кадры потом: движок разделяет тему, композицию (React/Remotion-сцены) и монтажный лист (JSON) — один и тот же план можно пересобрать в другой теме без переделки сцен.

## Установка

1. Убедитесь, что установлены: Node.js 20+, Python 3, FFmpeg (с ffprobe в PATH).
2. Проверьте окружение:
   ```
   node scripts/cli.js check-env
   ```
3. Установите JS-зависимости: `npm install`
4. Создайте Python-окружение и поставьте faster-whisper:
   ```
   python -m venv python/venv
   python/venv/Scripts/pip install -r requirements.txt
   ```
   (первый запуск транскрипции скачает модель Whisper, это может занять несколько минут)

## Быстрый старт: нейтральное demo

```
npm run demo
```

Соберёт синтетическое тестовое видео, прогонит его через весь цикл и положит результат в `projects/demo-01/final/demo-01.mp4`.

## Полный цикл для своего видео

```
node scripts/cli.js new-project --id my-video --input C:\path\to\video.mp4
node scripts/cli.js transcribe --id my-video
```

Дальше вместе с AI-агентом (Claude Code/Codex) на основе `projects/my-video/transcript/transcript.json` и вашей цели собирается монтажный лист `projects/my-video/brief/v01.json` (формат — `schema/edit-plan.schema.json`).

```
node scripts/cli.js validate --id my-video --file projects/my-video/brief/v01.json
node scripts/cli.js preview --id my-video --brief projects/my-video/brief/v01.json
node scripts/cli.js approve --id my-video --version v01
node scripts/cli.js render --id my-video --version v01
node scripts/cli.js qa --id my-video --version v01
```

Финал появится в `projects/my-video/final/my-video.mp4` только после успешного `qa`.

## Структура

- `scripts/` — CLI-диспетчер и его команды
- `python/` — локальная транскрипция (faster-whisper)
- `remotion/` — тема, сцены и композиция (React/Remotion)
- `schema/` — JSON Schema монтажного листа
- `projects/` — рабочие папки роликов (не в git)

## Тесты

```
npm test
```

Часть тестов (transcribe, remotion render, demo) — интеграционные: требуют реальных ffmpeg/ffprobe/faster-whisper/Remotion-Chromium и могут занять несколько минут при первом запуске.

## Вне рамок v1

Sidechain/ducking музыки, OpenCV-кадрирование под лицо, Tesseract OCR, Pexels API, ElevenLabs, Playwright QA — добавляются отдельными итерациями поверх той же 3-слойной архитектуры.
