#!/bin/bash
# stop.sh - Stop Security Department Daemon on port 7000

PORT=7000
PIDS=$(lsof -ti :$PORT 2>/dev/null || true)

if [ -n "$PIDS" ]; then
    echo "Stopping Security Department processes on port $PORT (PIDs: $PIDS)..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    sleep 1
    echo "✓ All processes on port $PORT stopped."
else
    echo "No process running on port $PORT."
fi
