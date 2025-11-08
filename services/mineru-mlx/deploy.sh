#!/bin/bash
# MinerU OCR Service - Production Deployment Script

set -e

echo "🚀 Deploying MinerU OCR Service..."

# Check if Docker network exists, create if not
if ! docker network inspect aiundecided-network &>/dev/null; then
    echo "📡 Creating Docker network..."
    docker network create aiundecided-network
fi

# Stop and remove existing container
echo "🛑 Stopping existing service..."
docker-compose down 2>/dev/null || true

# Build and start
echo "🔨 Building Docker image..."
docker-compose build

echo "▶️  Starting service..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for service to be healthy..."
for i in {1..30}; do
    if curl -sf http://localhost:9006/health &>/dev/null; then
        echo "✅ Service is healthy!"
        docker-compose ps
        echo ""
        echo "🌐 Access URLs:"
        echo "  Local:    http://localhost:9006/ui"
        echo "  External: https://ocr.aiundecided.com/ui"
        exit 0
    fi
    sleep 2
done

echo "❌ Service failed to start"
docker-compose logs
exit 1
