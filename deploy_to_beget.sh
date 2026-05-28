#!/bin/bash
# Deploy lead-parser to Beget VPS

HOST="155.212.208.194"
USER="root"
PROJECT_PATH="/root/lead-parser"

echo "📦 Подготовка проекта для загрузки..."
cd "c:/Users/User/OneDrive/Документы/Projekt/my-first-projekt/lead-parser"

echo "🚀 Загружаем проект на VPS..."
# Создать директорию на сервере
ssh ${USER}@${HOST} "mkdir -p ${PROJECT_PATH}"

# Загрузить файлы (исключая .venv и data)
echo "📁 Загружаем основные файлы..."
scp -r \
  -o StrictHostKeyChecking=accept-new \
  --exclude=".venv" \
  --exclude="data" \
  --exclude="__pycache__" \
  --exclude=".pytest_cache" \
  ./* \
  ${USER}@${HOST}:${PROJECT_PATH}/

echo "✅ Файлы загружены!"
echo ""
echo "🐳 Проверяем Docker на сервере..."
ssh ${USER}@${HOST} "docker --version && docker ps"

echo ""
echo "🔨 Собираем Docker образ на сервере..."
ssh ${USER}@${HOST} "cd ${PROJECT_PATH} && docker build -t lead-parser ."

echo ""
echo "🚀 Запускаем контейнер..."
ssh ${USER}@${HOST} "docker run -d -p 8000:8000 --env-file ${PROJECT_PATH}/.env.local --name lead-parser-app lead-parser"

echo ""
echo "✅ Контейнер запущен!"
ssh ${USER}@${HOST} "docker logs lead-parser-app"

echo ""
echo "📍 Открыть в браузере:"
echo "   http://155.212.208.194:8000/leads/"
