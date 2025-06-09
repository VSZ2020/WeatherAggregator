#!/bin/bash
set -e

# === НАСТРОЙКИ ===
REPO_URL="https://github.com/VSZ2020/WeatherAggregator.git"
BASE_DIR="/home/user/deploy"
RELEASES_DIR="$BASE_DIR/releases"
RUNNER="$BASE_DIR/app_runner/run_app.sh"
DEPLOY_LOG="$BASE_DIR/deploy.log"
PORT_1=8001
PORT_2=8002
# TELEGRAM_BOT_TOKEN="your_bot_token"
# TELEGRAM_CHAT_ID="your_chat_id"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
NEW_RELEASE="$RELEASES_DIR/release_$TIMESTAMP"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$DEPLOY_LOG"
}

# send_telegram() {
#     curl -s -X POST https://api.telegram.org/bot"$TELEGRAM_BOT_TOKEN"/sendMessage \
#         -d chat_id="$TELEGRAM_CHAT_ID" \
#         -d text="$1"
# }

log "[*] Деплой начался: $TIMESTAMP"
send_telegram "🚀 Новый деплой запущен в $TIMESTAMP"

# === Определяем текущий порт ===
if sudo nginx -T | grep -q "$PORT_1"; then
  NEW_PORT=$PORT_2
  OLD_PORT=$PORT_1
else
  NEW_PORT=$PORT_1
  OLD_PORT=$PORT_2
fi

log "[*] Клонируем репозиторий из $REPO_URL"
git clone "$REPO_URL" "$NEW_RELEASE"

log "[*] Устанавливаем виртуальное окружение"
python3 -m venv "$NEW_RELEASE/venv"
source "$NEW_RELEASE/venv/bin/activate"
pip install --upgrade pip
pip install -r "$NEW_RELEASE/requirements.txt"

log "[*] Запускаем новое приложение на порту $NEW_PORT"
$RUNNER "$NEW_RELEASE" "$NEW_PORT"

log "[*] Обновляем nginx на порт $NEW_PORT"
sudo sed -i "s/127.0.0.1:$OLD_PORT/127.0.0.1:$NEW_PORT/" /etc/nginx/sites-available/fastapi
sudo systemctl reload nginx

log "[*] Обновляем симлинк на новую версию"
ln -sfn "$NEW_RELEASE" "$BASE_DIR/current"

log "[*] Останавливаем старую версию на порту $OLD_PORT"
OLD_RELEASE=$(readlink "$BASE_DIR/current")
if [ -f "$OLD_RELEASE/uvicorn.pid" ]; then
  kill "$(cat "$OLD_RELEASE/uvicorn.pid")" || log "⚠️ Не удалось остановить старую версию"
  rm "$OLD_RELEASE/uvicorn.pid"
fi

log "[*] Очистка старых релизов (старше 7 дней)"
find "$RELEASES_DIR" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

log "[✓] Деплой завершён: $NEW_RELEASE на порту $NEW_PORT"
# send_telegram "✅ Деплой завершён\nПапка: $NEW_RELEASE\nПорт: $NEW_PORT"