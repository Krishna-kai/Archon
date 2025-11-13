#!/bin/bash
# Archon Native Services Stop Script
# Stops all native Mac services for Archon

echo "🛑 Stopping Archon Native Services..."
echo ""

# Stop Ollama
echo "Stopping Ollama..."
if pkill -f "ollama serve" 2>/dev/null; then
    echo "✅ Ollama stopped"
else
    echo "ℹ️  Ollama was not running"
fi

# Stop Ollama-MLX
echo "Stopping Ollama-MLX..."
if pkill -f "ollama-mlx/app.py" 2>/dev/null; then
    echo "✅ Ollama-MLX stopped"
else
    echo "ℹ️  Ollama-MLX was not running"
fi

# Stop MinerU-MLX
echo "Stopping MinerU-MLX..."
if pkill -f "uvicorn app:app --host 0.0.0.0 --port 9006" 2>/dev/null; then
    echo "✅ MinerU-MLX stopped"
else
    echo "ℹ️  MinerU-MLX was not running"
fi

# Stop Nexa
echo "Stopping Nexa..."
if pkill -f "nexa serve" 2>/dev/null; then
    echo "✅ Nexa stopped"
else
    echo "ℹ️  Nexa was not running"
fi

echo ""
echo "✅ All services stopped!"
echo ""
echo "To verify, check:"
echo "  lsof -i:11434  # Ollama"
echo "  lsof -i:9008   # Ollama-MLX"
echo "  lsof -i:9006   # MinerU-MLX"
echo "  lsof -i:9009   # Nexa"
