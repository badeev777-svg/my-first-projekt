@echo off
cd /d "%~dp0"
start "" http://localhost:8001
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
