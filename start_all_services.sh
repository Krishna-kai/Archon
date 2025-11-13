#!/bin/bash
# Archon Native Services Startup Script
# Starts all native Mac services for Archon

echo "🚀 Starting Archon Native Services..."
echo ""

# Create logs directory if it doesn't exist
mkdir -p ~/logs

# Start Ollama (if not already running)
if ! lsof -i:11434 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting Ollama..."
    /Applications/Ollama.app/Contents/MacOS/Ollama serve > ~/logs/ollama.log 2>&1 &
    sleep 2
    echo "✅ Ollama started"
else
    echo "✅ Ollama already running"
fi

# Start Ollama-MLX
if ! lsof -i:9008 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting Ollama-MLX..."
    cd ~/Projects/archon/services/ollama-mlx
    nohup python app.py > ~/logs/ollama-mlx.log 2>&1 &
    sleep 2
    echo "✅ Ollama-MLX started"
else
    echo "✅ Ollama-MLX already running"
fi

# Start MinerU-MLX
if ! lsof -i:9006 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting MinerU-MLX..."
    cd ~/Projects/archon/services/mineru-mlx
    nohup uvicorn app:app --host 0.0.0.0 --port 9006 --reload > ~/logs/mineru-mlx.log 2>&1 &
    sleep 2
    echo "✅ MinerU-MLX started"
else
    echo "✅ MinerU-MLX already running"
fi

# Start Nexa
if ! lsof -i:9009 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting Nexa..."
    nohup nexa serve --host 0.0.0.0:9009 > ~/logs/nexa.log 2>&1 &
    sleep 2
    echo "✅ Nexa started"
else
    echo "✅ Nexa already running"
fi

echo ""
echo "✅ All services started!"
echo ""
echo "Verifying services..."
sleep 3

# Check inference gateway health
curl -s http://localhost:9100/health | python3 -m json.tool

echo ""
echo "Service logs available in ~/logs/"
echo "  - ~/logs/ollama.log"
echo "  - ~/logs/ollama-mlx.log"
echo "  - ~/logs/mineru-mlx.log"
