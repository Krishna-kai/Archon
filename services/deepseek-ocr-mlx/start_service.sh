#!/bin/bash

# DeepSeek-OCR MLX Service Startup Script
# For Mac M4 with Apple Metal GPU acceleration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting DeepSeek-OCR MLX Service..."
echo "📍 Working directory: $SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv || python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Check if MLX is installed
if ! python -c "import mlx" 2>/dev/null; then
    echo "❌ MLX not installed!"
    echo "Installing MLX framework..."
    pip install mlx mlx-vlm
fi

# Set environment variables
export PORT=${PORT:-9005}
export MODEL_NAME=${MODEL_NAME:-"mlx-community/DeepSeek-OCR-8bit"}
export PYTHONUNBUFFERED=1

echo ""
echo "🌐 Starting server on port $PORT..."
echo "📦 Model: $MODEL_NAME"
echo "🔥 GPU: Apple Metal (M4)"
echo "📝 Logs: Will appear below..."
echo ""
echo "Press Ctrl+C to stop the service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start uvicorn server
uvicorn app:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info

# The server will keep running until stopped with Ctrl+C
