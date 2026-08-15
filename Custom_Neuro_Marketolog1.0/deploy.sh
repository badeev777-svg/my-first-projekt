#!/bin/bash
# deploy.sh — Установка Нейро-Маркетолога на чистый Ubuntu VPS
# Запуск: bash deploy.sh  (от root, из корня проекта)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/neuro-marketolog"
SERVICE_NAME="neuro-marketolog"
PORT=8001

# ── Заголовок ────────────────────────────────────────────────────────────────

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║      Нейро-Маркетолог — Установка       ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Проверки ─────────────────────────────────────────────────────────────────

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Ошибка: запустите от root (sudo bash deploy.sh)${NC}"
  exit 1
fi

if [ ! -f "web/requirements.txt" ]; then
  echo -e "${RED}Ошибка: запустите скрипт из корня проекта (там где deploy.sh)${NC}"
  exit 1
fi

# ── Параметры ─────────────────────────────────────────────────────────────────

echo -e "${YELLOW}Введите параметры установки:${NC}\n"

read -rp "Домен сайта (например: ai.client-domain.ru): " DOMAIN
read -rp "Email для SSL-сертификата (Let's Encrypt): " SSL_EMAIL
echo ""
read -rp "cloud.ru Foundation Models API Key: " CLOUD_RU_KEY
echo ""
read -rp "Контактная ссылка клиента (https://t.me/username): " CONTACT_LINK
echo ""
read -rp "Логин админ-панели (НЕ 'admin'): " ADMIN_LOGIN
while [ -z "$ADMIN_LOGIN" ] || [ "$ADMIN_LOGIN" = "admin" ]; do
  read -rp "Логин не должен быть пустым или 'admin'. Введите ещё раз: " ADMIN_LOGIN
done
ADMIN_PASSWORD="$(openssl rand -base64 18)"
echo -e "  Сгенерирован пароль админ-панели: ${GREEN}${ADMIN_PASSWORD}${NC} (сохраните его — он не хранится больше нигде)"
echo ""
read -rp "Имя агента [Нейро-Маркетолог]: " AGENT_NAME
AGENT_NAME="${AGENT_NAME:-Нейро-Маркетолог}"

read -rp "Инициалы агента (2-3 символа) [НМ]: " AGENT_INITIALS
AGENT_INITIALS="${AGENT_INITIALS:-НМ}"

read -rp "Название компании/агентства: " AGENCY_NAME

read -rp "Слоган (под названием в footer) [AI-автоматизация бизнеса]: " AGENCY_TAGLINE
AGENCY_TAGLINE="${AGENCY_TAGLINE:-AI-автоматизация бизнеса}"

read -rp "MAX-ссылка клиента (оставьте пустым если нет): " MAX_LINK

read -rp "Режим только чат — без лендинга, автостарт? [y/N]: " CHAT_ONLY_INPUT
CHAT_ONLY_MODE="false"
[[ "${CHAT_ONLY_INPUT,,}" == "y" ]] && CHAT_ONLY_MODE="true"

echo ""
echo -e "${YELLOW}Параметры:${NC}"
echo "  Домен:        $DOMAIN"
echo "  Агент:        $AGENT_NAME ($AGENT_INITIALS)"
echo "  Агентство:    $AGENCY_NAME"
echo "  Контакт:      $CONTACT_LINK"
echo "  Chat-only:    $CHAT_ONLY_MODE"
echo ""
read -rp "Продолжить? [Y/n]: " CONFIRM
[[ "${CONFIRM,,}" == "n" ]] && exit 0

# ── Системные пакеты ──────────────────────────────────────────────────────────

echo -e "\n${YELLOW}[1/6] Устанавливаю системные пакеты...${NC}"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx curl

# ── Копирование проекта ───────────────────────────────────────────────────────

echo -e "${YELLOW}[2/6] Копирую проект в $INSTALL_DIR...${NC}"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='web/.env' --exclude='bot/.env' \
  ./ "$INSTALL_DIR/"

# ── Python venv + зависимости ─────────────────────────────────────────────────

echo -e "${YELLOW}[3/6] Создаю виртуальное окружение и устанавливаю зависимости...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/web/requirements.txt"

# ── .env ──────────────────────────────────────────────────────────────────────

echo -e "${YELLOW}[4/6] Создаю .env...${NC}"
cat > "$INSTALL_DIR/web/.env" <<EOF
CLOUD_RU_API_KEY=$CLOUD_RU_KEY
MODEL=ai-sage/GigaChat3.5-432B-A28B
MAX_TOKENS=14000

AGENT_NAME=$AGENT_NAME
AGENT_INITIALS=$AGENT_INITIALS
AGENCY_NAME=$AGENCY_NAME
AGENCY_TAGLINE=$AGENCY_TAGLINE
CONTACT_LINK=$CONTACT_LINK
MAX_LINK=$MAX_LINK
CHAT_ONLY_MODE=$CHAT_ONLY_MODE

ADMIN_LOGIN=$ADMIN_LOGIN
ADMIN_PASSWORD=$ADMIN_PASSWORD
ADMIN_URL=https://$DOMAIN/admin

TG_BOT_TOKEN=
TG_CHAT_ID=
MAX_BOT_TOKEN=
MAX_USER_ID=0
EOF
chmod 600 "$INSTALL_DIR/web/.env"

# ── Systemd сервис ────────────────────────────────────────────────────────────

echo -e "${YELLOW}[5/6] Настраиваю systemd сервис...${NC}"
cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Neuro Marketolog — $AGENCY_NAME
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/web
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port $PORT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo -e "${RED}Ошибка: сервис не запустился. Проверьте: journalctl -u $SERVICE_NAME -n 30${NC}"
  exit 1
fi
echo -e "  Сервис запущен ✓"

# ── Nginx + SSL ───────────────────────────────────────────────────────────────

echo -e "${YELLOW}[6/6] Настраиваю nginx и SSL...${NC}"

cat > "/etc/nginx/sites-available/$SERVICE_NAME" <<EOF
limit_req_zone \$binary_remote_addr zone=${SERVICE_NAME}_api:10m rate=10r/m;

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    client_max_body_size 1M;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location /api/ {
        limit_req zone=${SERVICE_NAME}_api burst=5 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location /admin/ {
        limit_req zone=${SERVICE_NAME}_api burst=5 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/$SERVICE_NAME" "/etc/nginx/sites-enabled/$SERVICE_NAME"
nginx -t
systemctl reload nginx

certbot --nginx -d "$DOMAIN" \
  --non-interactive --agree-tos \
  --email "$SSL_EMAIL" \
  --redirect
echo -e "  SSL получен ✓"

# ── Готово ────────────────────────────────────────────────────────────────────

echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════╗"
echo "║          Установка завершена!            ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  Сайт:    ${GREEN}https://$DOMAIN${NC}"
echo -e "  Агент:   $AGENT_NAME"
echo -e "  Контакт: $CONTACT_LINK"
echo ""
echo -e "  Управление сервисом:"
echo -e "    systemctl status $SERVICE_NAME"
echo -e "    systemctl restart $SERVICE_NAME"
echo -e "    journalctl -u $SERVICE_NAME -f"
echo ""
echo -e "  Конфиг:  $INSTALL_DIR/web/.env"
echo ""
