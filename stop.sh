#!/bin/bash
PORT=7000
PID=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$PID" ]; then
    echo "Stopping Security Dept on port $PORT (PID: $PID)..."
    kill -9 $PID 2>/dev/null || true
    echo "Stopped."
else
    echo "No process running on port $PORT."
fi
