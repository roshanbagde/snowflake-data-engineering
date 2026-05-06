#!/bin/bash
cd "$(dirname "$0")"
PID_FILE=".streamlit.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" && rm -f "$PID_FILE" && echo "AgentAlpha stopped."
    else
        rm -f "$PID_FILE" && echo "Stale PID removed."
    fi
else
    pkill -f "streamlit run app.py" 2>/dev/null && echo "AgentAlpha stopped." || echo "Not running."
fi
