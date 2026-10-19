#!/bin/bash
# QKD Backend Startup Script
# Usage: ./start_backend.sh [host] [port]
# Default: localhost 8080

HOST=${1:-localhost}
PORT=${2:-8080}

echo "Starting QKD Backend Server..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "API Docs will be available at: http://$HOST:$PORT/docs"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run the server
python -m uvicorn backend.app:app --reload --host "$HOST" --port "$PORT"
