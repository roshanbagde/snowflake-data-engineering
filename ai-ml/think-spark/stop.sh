#!/usr/bin/env bash
PID_FILE="$(cd "$(dirname "$0")" && pwd)/logs/streamlit.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")" && rm "$PID_FILE"
    echo "ThinkSpark stopped."
else
    pkill -f "streamlit run.*think-spark" 2>/dev/null && echo "Stopped." || echo "Not running."
fi
exit 0
