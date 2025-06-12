#!/bin/bash
APP_DIR=$1
PORT=$2
LOG_FILE="/var/log/weather_agg_$PORT.log"

echo "[*] Запуск приложения из $APP_DIR на порту $PORT"
cd "$APP_DIR"
source venv/bin/activate
nohup uvicorn app:app --host 127.0.0.1 --port "$PORT" > "$LOG_FILE" 2>&1 &
echo $! > "$APP_DIR/uvicorn.pid"