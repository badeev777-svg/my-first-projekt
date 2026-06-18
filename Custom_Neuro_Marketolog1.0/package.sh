#!/usr/bin/env bash
# Создаёт чистый архив проекта для передачи клиенту.
# Запуск: bash package.sh [имя_клиента]
# Пример: bash package.sh salon_beauty_moscow
set -euo pipefail

CLIENT="${1:-client}"
DATE=$(date +%Y%m%d)
ARCHIVE="neuro-marketolog-${CLIENT}-${DATE}.tar.gz"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Упаковка проекта: $ARCHIVE"

tar -czf "$ARCHIVE" \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='.env' \
  --exclude='*.egg-info' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='node_modules' \
  --exclude='CLAUDE.md' \
  --exclude='PLAN.md' \
  --exclude='memory.md' \
  --exclude='PROMPT_v2.0.md' \
  --exclude='AGENT_1_Neuro_Marketer.md' \
  --exclude='AGENT_2_AI_Architect.md' \
  --exclude='AGENT_3_AI_Sales_Engineer.md' \
  --exclude='KNOWLEDGE_BASE.md' \
  --exclude='KNOWLEDGE_1_Marketing.md' \
  --exclude='KNOWLEDGE_2_Architecture.md' \
  --exclude='KNOWLEDGE_3_Sales.md' \
  --exclude='package.sh' \
  -C "$SCRIPT_DIR" \
  GPT_SYSTEM \
  web \
  bot \
  docs \
  deploy.sh \
  nginx_neuro.conf \
  rate_limit.conf

SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo ""
echo "✓ Архив готов: $ARCHIVE ($SIZE)"
echo ""
echo "Состав архива:"
tar -tzf "$ARCHIVE" | head -40
echo "..."
echo ""
echo "Передайте клиенту:"
echo "  1. Файл: $ARCHIVE"
echo "  2. Инструкция по развёртыванию: docs/CLIENT_GUIDE.md (внутри архива)"
echo "  3. Для запуска деплоя: tar xzf $ARCHIVE && bash deploy.sh"
