#!/bin/bash
cd "$(dirname "$0")"
PID_FILE=".streamlit.pid"
LOG_FILE="logs/streamlit.log"
URL="http://localhost:8504"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "AgentAlpha is already running at $URL (PID $PID)"
        open "$URL" 2>/dev/null || true
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi
if [ ! -f "venv/bin/activate" ]; then
    echo "ERROR: venv not found. Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
mkdir -p logs
source venv/bin/activate
nohup streamlit run app.py --server.headless true --server.port 8504 > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Starting AgentAlpha..."
sleep 2
open "$URL" 2>/dev/null || echo "Open your browser at $URL"
echo "App is running at $URL  |  Logs: $LOG_FILE  |  To stop: ./stop.sh"
