#!/bin/bash
# Start MinerU Native Service

echo "Starting MinerU Native Service on port 8055..."
echo "Using Apple Silicon GPU (MPS) acceleration"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment and run service
uv run python -m src.mineru_service.main
