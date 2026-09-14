#!/bin/bash
# start.sh - Launch Security Department Command Suite on port 7000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT=7000

# Kill any existing process on port 7000
PID=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$PID" ]; then
    echo "Terminating existing process on port $PORT (PID: $PID)..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
fi

echo "Starting Security Department Daemon on 0.0.0.0:$PORT..."
nohup ./venv/bin/python manage.py runserver 0.0.0.0:$PORT --noreload > security_dept.log 2>&1 &

NEW_PID=$!
echo "Security Dept daemon launched with PID: $NEW_PID"
sleep 2

if ps -p $NEW_PID > /dev/null; then
    echo "✓ Security Department Suite successfully started and listening on http://0.0.0.0:$PORT"
    exit 0
else
    echo "✗ Failed to start Security Department Suite. Log output:"
    tail -n 25 security_dept.log
    exit 1
fi
