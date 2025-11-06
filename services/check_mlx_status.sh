#!/bin/bash
# Check status of all MLX services

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🔍 Archon MLX Services Status"
echo "════════════════════════════════════════════════════════════"
echo ""

# Function to check service health
check_service() {
    local name=$1
    local port=$2
    local url="http://localhost:$port/health"

    echo -n "🔹 $name (Port $port): "

    if response=$(curl -s -m 2 "$url" 2>/dev/null); then
        if echo "$response" | grep -q '"status".*"healthy"'; then
            echo "✅ HEALTHY"
            # Show additional info if jq is available
            if command -v jq &> /dev/null; then
                echo "$response" | jq -r '   "   Version: \(.version // "N/A")\n   Backend: \(.backend // "N/A")"' 2>/dev/null || true
            fi
        else
            echo "⚠️  RESPONDING (but not healthy)"
        fi
    else
        echo "❌ NOT RUNNING"

        # Check if port is in use by something else
        if lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "   ⚠️  Port $port is in use by another process"
        else
            echo "   💡 Start with: cd ~/Projects/archon/services/$3 && ./start_service.sh"
        fi
    fi
    echo ""
}

# Check both MLX services
check_service "DeepSeek-OCR MLX" 9005 "deepseek-ocr-mlx"
check_service "MinerU MLX" 9006 "mineru-mlx"

# Show running processes
echo "════════════════════════════════════════════════════════════"
echo "📋 Running MLX Processes"
echo "════════════════════════════════════════════════════════════"
echo ""

if pgrep -f "uvicorn app:app.*9005" > /dev/null; then
    echo "✅ DeepSeek-OCR MLX process running:"
    ps aux | grep "[u]vicorn app:app.*9005" | awk '{printf "   PID: %s, CPU: %s%%, Memory: %s MB\n", $2, $3, int($6/1024)}'
else
    echo "❌ DeepSeek-OCR MLX process not found"
fi

echo ""

if pgrep -f "uvicorn app:app.*9006" > /dev/null; then
    echo "✅ MinerU MLX process running:"
    ps aux | grep "[u]vicorn app:app.*9006" | awk '{printf "   PID: %s, CPU: %s%%, Memory: %s MB\n", $2, $3, int($6/1024)}'
else
    echo "❌ MinerU MLX process not found"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🐳 Docker Services Status"
echo "════════════════════════════════════════════════════════════"
echo ""

if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "archon|ocr|pdf" | head -5; then
    echo ""
    echo "💡 View all: docker ps"
else
    echo "❌ No Docker services running"
    echo "💡 Start with: cd ~/Projects/archon && docker compose up -d"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
