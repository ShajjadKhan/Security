#!/bin/bash
# start.sh - Launch Security Department Production Daemon (Gunicorn) on port 7000
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT=${PORT:-8001}
mkdir -p logs
mkdir -p staticfiles media

# Locate virtual environment
if [ -d "$SCRIPT_DIR/venv" ]; then
    VENV_PY="$SCRIPT_DIR/venv/bin/python"
    VENV_GUNICORN="$SCRIPT_DIR/venv/bin/gunicorn"
elif [ -d "/home/shajjad/security_venv" ]; then
    VENV_PY="/home/shajjad/security_venv/bin/python"
    VENV_GUNICORN="/home/shajjad/security_venv/bin/gunicorn"
else
    VENV_PY="python3"
    VENV_GUNICORN="gunicorn"
fi

# Ensure static files are gathered
echo "Gathering static files..."
"$VENV_PY" manage.py collectstatic --noinput

# Kill any existing process on port
PID=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo "Terminating existing process on port $PORT (PID: $PID)..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
fi

echo "Starting Production Gunicorn Daemon on 127.0.0.1:$PORT..."
GUNICORN_BIND="127.0.0.1:$PORT" nohup "$VENV_GUNICORN" config.wsgi:application -c gunicorn.conf.py > logs/startup.log 2>&1 &

sleep 2

# Verify Gunicorn is running on port 7000
if lsof -i :$PORT > /dev/null 2>&1; then
    NEW_PID=$(lsof -ti :$PORT | head -n 1)
    echo "✓ Security Department Suite running in production on http://0.0.0.0:$PORT (PID: $NEW_PID)"
    exit 0
else
    echo "✗ Failed to start Gunicorn on port $PORT. Log output:"
    cat logs/startup.log
    if [ -f logs/gunicorn_error.log ]; then
        tail -n 25 logs/gunicorn_error.log
    fi
    exit 1
fi
