#!/bin/bash
# Unified MinerU Service Startup Script
# Single service with full features: PDF processing + LLM integration

set -e

echo "════════════════════════════════════════════════════════"
echo "🚀 MinerU Unified Service"
echo "════════════════════════════════════════════════════════"
echo ""

# Configuration
export PORT=${PORT:-9006}
export HOST=${HOST:-0.0.0.0}
export LOG_LEVEL=${LOG_LEVEL:-info}
export PYTHONUNBUFFERED=1

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/mineru-mlx" && pwd)"

# Check if already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✅ Service already running on port $PORT"
    echo "📊 Health: http://localhost:$PORT/health"
    echo "🎯 UI: http://localhost:$PORT"
    echo "📖 API Docs: http://localhost:$PORT/docs"
    exit 0
fi

# Start service
echo "📍 Port: $PORT"
echo "🔥 Backend: MinerU + Ollama LLM"
echo "📊 Features: Text, Formulas, Tables, Images, AI Enhancement"
echo "🖥️  Platform: Apple Silicon with Metal GPU"
echo ""
echo "Starting service..."
echo ""

cd "$SERVICE_DIR"

# Activate venv and start
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start in background
uvicorn app:app --host $HOST --port $PORT --reload > logs/service.log 2>&1 &
SERVICE_PID=$!

# Wait for startup
sleep 3

# Verify health
if curl -sf http://localhost:$PORT/health > /dev/null; then
    echo "✅ Service started successfully!"
    echo ""
    echo "📊 Health: http://localhost:$PORT/health"
    echo "🎯 UI: file://$SERVICE_DIR/mineru_ui.html"
    echo "📖 API Docs: http://localhost:$PORT/docs"
    echo "📝 Logs: $SERVICE_DIR/logs/service.log"
    echo "🔢 PID: $SERVICE_PID"
    echo ""
    echo "To stop: kill $SERVICE_PID"
else
    echo "❌ Service failed to start. Check logs: $SERVICE_DIR/logs/service.log"
    exit 1
fi
