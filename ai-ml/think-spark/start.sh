#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT=8505
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/streamlit.log"
PID_FILE="$LOG_DIR/streamlit.pid"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Already running on http://localhost:$PORT (PID $(cat "$PID_FILE"))"
    open "http://localhost:$PORT" 2>/dev/null || true
    exit 0
fi

if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

[ -f "$SCRIPT_DIR/.env" ] || echo "Warning: .env not found — you can enter API keys directly in the sidebar."

echo "Starting ThinkSpark on http://localhost:$PORT …"
nohup streamlit run "$SCRIPT_DIR/app.py" \
    --server.port $PORT \
    --server.headless true \
    --browser.gatherUsageStats false \
    > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
sleep 1.5
echo "Started. Log: $LOG_FILE"
open "http://localhost:$PORT" 2>/dev/null || echo "Open http://localhost:$PORT in your browser."
exit 0
