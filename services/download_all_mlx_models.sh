#!/bin/bash
# Download all MLX models for both services
# Run this before first use to pre-cache models

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🔽 MLX Services - Model Download"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "This script will download models for:"
echo "  • DeepSeek-OCR MLX (~4-6 GB)"
echo "  • MinerU MLX (~500 MB - 1 GB)"
echo ""
echo "Total time: ~5-15 minutes (depending on internet speed)"
echo "Total space: ~5-7 GB"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

read -p "📥 Start download? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⏭️  Download cancelled"
    exit 0
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "1️⃣  DeepSeek-OCR MLX Model Download"
echo "════════════════════════════════════════════════════════════"
echo ""

# Download DeepSeek-OCR model
cd "$SCRIPT_DIR/deepseek-ocr-mlx"

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv || python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Download model
python download_model.py

DEEPSEEK_STATUS=$?

echo ""
echo "════════════════════════════════════════════════════════════"
echo "2️⃣  MinerU MLX Models Download"
echo "════════════════════════════════════════════════════════════"
echo ""

# Download MinerU models
cd "$SCRIPT_DIR/mineru-mlx"

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv || python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Download models
python download_models.py

MINERU_STATUS=$?

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📊 Download Summary"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ $DEEPSEEK_STATUS -eq 0 ]; then
    echo "✅ DeepSeek-OCR MLX: Models ready"
else
    echo "⚠️  DeepSeek-OCR MLX: Check output above"
fi

if [ $MINERU_STATUS -eq 0 ]; then
    echo "✅ MinerU MLX: Models ready"
else
    echo "⚠️  MinerU MLX: Check output above"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 Next Steps"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Start DeepSeek-OCR MLX service:"
echo "  cd $SCRIPT_DIR/deepseek-ocr-mlx"
echo "  ./start_service.sh"
echo ""
echo "Start MinerU MLX service:"
echo "  cd $SCRIPT_DIR/mineru-mlx"
echo "  ./start_service.sh"
echo ""
echo "Or start both in separate terminals!"
echo ""
