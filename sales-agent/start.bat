@echo off
chcp 65001 >nul
cd /d "%~dp0"
where uv >nul 2>nul || (echo Не найдена программа uv. Установите её: https://docs.astral.sh/uv/ & pause & exit /b 1)
if not exist .env copy .env.example .env >nul
uv sync || (pause & exit /b 1)
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/"
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
pause
