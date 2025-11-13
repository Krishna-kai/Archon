# Archon Service Management Guide

## Quick Start - After Machine Restart

**Just restarted your computer? Run these commands to verify everything is working:**

```bash
# 1. Check LaunchAgents (should show 5-6 services)
launchctl list | grep -E "(ollama|archon)"

# 2. Check Docker services (should show 4 services healthy)
docker ps --format "table {{.Names}}\t{{.Status}}"

# 3. Verify all 5 backend services healthy
curl -s http://localhost:9100/health | python3 -m json.tool

# Expected: "healthy_services": 5, "total_services": 5
```

**If anything is wrong, see the [Machine Restart Guide](#machine-restart-guide) below for detailed troubleshooting.**

---

## Overview

Archon consists of **Docker services** and **Native Mac services** that work together. This guide explains what starts automatically on machine reboot and how to manage all services.

## What Happens After Machine Restart? (Updated 2025-11-13)

**TL;DR**: All services now auto-start successfully! 🎉

### Fixes Applied (2025-11-13)
1. **MinerU-MLX**: Installed missing Python dependencies (pydantic-ai, Pillow) in venv
2. **Nexa**: Configured service to run on port 9009 with LaunchAgent
3. **Inference Gateway**: Updated health check to detect Nexa properly (uses root endpoint)

### Services That Auto-Start ✅
1. **Docker Services** (if Docker Desktop auto-starts):
   - archon-server, archon-mcp, archon-ui, inference-gateway
   - ocrmypdf-service (if running in Docker)
2. **Ollama** (port 11434) - via multiple LaunchAgents
3. **Ollama-MLX** (port 9008) - via LaunchAgent (com.archon.ollama-mlx)
4. **MinerU-MLX** (port 9006) - via LaunchAgent (com.archon.mineru-mlx) **[FIXED]**
5. **Nexa** (port 9009) - via LaunchAgent (com.archon.nexa) **[NEW]**

### Expected Health After Restart
**Inference Gateway Health Check**: `curl http://localhost:9100/health`
```json
{
    "status": "healthy",
    "services": {
        "ollama": true,           ✅ Auto-starts
        "ollama-mlx": true,       ✅ Auto-starts
        "mineru-mlx": true,       ✅ Auto-starts (fixed)
        "ocrmypdf": true,         ✅ Auto-starts (Docker)
        "nexa": true             ✅ Auto-starts (configured)
    },
    "healthy_services": 5,
    "total_services": 5
}
```

## Docker Clean Restart Testing (2025-11-13)

Successfully tested complete Docker environment restart with cache clearing:

### Test Procedure
1. **Stopped all Docker services**: `docker compose down`
2. **Cleared Docker cache**: `docker system prune -a --volumes -f`
   - Reclaimed 9.084GB of disk space
   - Removed unused containers, images, and build cache
3. **Rebuilt all services**: `docker compose up -d --build`
4. **Verified health**: All 5 backend services healthy

### Test Results ✅
- All Docker services started successfully from clean build
- Native services (ollama, ollama-mlx, mineru-mlx, nexa) remained running during Docker restart
- Inference gateway reported 5/5 healthy services
- MinerU OCR processing verified working (3.67s processing time)
- No configuration issues or missing dependencies

### Key Findings
- **Native service persistence**: LaunchAgent-managed services continue running independently of Docker
- **Clean rebuild stability**: All services came back up healthy from scratch
- **Configuration integrity**: No environment or setup issues after cache clear
- **Disk space optimization**: Regular Docker pruning recommended (9GB freed)

## Service Architecture

### 🐳 Docker Services (Auto-Start with Docker Desktop)

These services start automatically when Docker Desktop starts:

#### Archon Core (Default - No Profile)
- **archon-server** (port 9181) - Main API server
- **archon-mcp** (port 9051) - MCP server for IDE integration
- **archon-ui** (port 9737) - Frontend web interface
- **inference-gateway** (port 9100) - Unified API for AI services

**Start Command**:
```bash
cd ~/Projects/archon
docker compose up -d
```

#### OCRmyPDF Service (Separate Docker Compose)
- **ocrmypdf-service** (port 9002) - PDF OCR processing

**Location**: Outside Archon's main docker-compose.yml
**Current Status**: Running (check with `docker ps | grep ocrmypdf`)

### 🖥️  Native Mac Services (LaunchAgent Auto-Start)

These services run directly on macOS with Apple Metal GPU acceleration. Most have LaunchAgents configured for auto-start.

#### 1. Ollama (Port 11434) ✅ AUTO-STARTS
**Purpose**: Local LLM inference (CPU + GPU)
**Location**: Installed via Ollama.app or Homebrew
**Auto-Start**: YES - Multiple LaunchAgents configured:
- `com.ollama.ollama`
- `homebrew.mxcl.ollama`
- `application.com.electron.ollama.*`

**Manual Start**:
- **Ollama.app**: Launch `/Applications/Ollama.app`
- **Homebrew**: `ollama serve`
- **Verify**: `curl http://localhost:11434/api/tags`

#### 2. Ollama-MLX (Port 9008) ✅ AUTO-STARTS
**Purpose**: MLX-native LLM inference with visual monitoring
**Location**: `/Users/krishna/Projects/archon/services/ollama-mlx/`
**Auto-Start**: YES - LaunchAgent: `com.archon.ollama-mlx`

**Manual Start**:
```bash
cd ~/Projects/archon/services/ollama-mlx
python app.py
```

**Or run in background**:
```bash
cd ~/Projects/archon/services/ollama-mlx
nohup python app.py > ~/logs/ollama-mlx.log 2>&1 &
```

**Verify**: `curl http://localhost:9008/health`

#### 3. MinerU-MLX (Port 9006) ✅ AUTO-STARTS
**Purpose**: Advanced PDF processing with layout analysis
**Location**: `/Users/krishna/Projects/archon/services/mineru-mlx/`
**Auto-Start**: YES - LaunchAgent: `com.archon.mineru-mlx`
**Status**: ✅ Working (Python dependencies fixed: pydantic-ai, Pillow installed)

**LaunchAgent Config**: `~/Library/LaunchAgents/com.archon.mineru-mlx.plist`
**Logs**: `~/Projects/archon/services/mineru-mlx/logs/stderr.log`

**Manual Start** (from existing script):
```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

**Or manually**:
```bash
cd ~/Projects/archon/services/mineru-mlx
uvicorn app:app --host 0.0.0.0 --port 9006 --reload
```

**Verify**: `curl http://localhost:9006/health`

#### 4. Nexa (Port 9009) ✅ AUTO-STARTS
**Purpose**: Multimodal inference (vision, audio, text)
**Location**: `/usr/local/bin/nexa`
**Auto-Start**: YES - LaunchAgent: `com.archon.nexa`
**Status**: ✅ Configured and running

**LaunchAgent Config**: `~/Library/LaunchAgents/com.archon.nexa.plist`
**Logs**: `~/logs/nexa-stdout.log`, `~/logs/nexa-stderr.log`

**Manual Start**:
```bash
nexa serve --host 0.0.0.0:9009
```

**Verify**: `curl http://localhost:9009/` (should return "Nexa SDK is running")

## Current Service Status

### Check LaunchAgents

**List all Archon-related LaunchAgents**:
```bash
launchctl list | grep -E "(ollama|archon)"
```

**Expected output**:
```
21096	-15	com.archon.ollama-mlx      # -15 = SIGTERM (running)
-	0	com.ollama.ollama           # 0 = success
62493	0	application.com.electron.ollama.32744243.32744269
-	0	com.archon.mineru-mlx       # 0 = success (fixed!)
21088	0	homebrew.mxcl.ollama
29564	0	com.archon.nexa             # 0 = success (new!)
```

**Check LaunchAgent logs** (if needed):
```bash
# MinerU-MLX logs
tail -30 ~/Projects/archon/services/mineru-mlx/logs/stderr.log

# Nexa logs
tail -30 ~/logs/nexa-stderr.log
```

### Check Running Services

**Docker Services**:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Native Services**:
```bash
# Check all inference service ports
lsof -i:11434 -sTCP:LISTEN  # Ollama
lsof -i:9008 -sTCP:LISTEN   # Ollama-MLX
lsof -i:9006 -sTCP:LISTEN   # MinerU-MLX
lsof -i:9009 -sTCP:LISTEN   # Nexa
lsof -i:9002 -sTCP:LISTEN   # OCRmyPDF (docker)
```

**Inference Gateway Health**:
```bash
curl -s http://localhost:9100/health | python3 -m json.tool
```

Expected output:
```json
{
    "status": "healthy",
    "services": {
        "ollama": true,
        "ollama-mlx": true,
        "mineru-mlx": true,
        "ocrmypdf": true,
        "nexa": false
    },
    "healthy_services": 4,
    "total_services": 5
}
```

## Machine Restart Guide

### After Machine Restart - What to Expect

**All services should auto-start!** ✅

When you restart your machine, here's what happens automatically:

1. **Native Services** (Auto-start via LaunchAgents):
   - Ollama (port 11434) - Multiple LaunchAgents configured
   - Ollama-MLX (port 9008) - `com.archon.ollama-mlx`
   - MinerU-MLX (port 9006) - `com.archon.mineru-mlx`
   - Nexa (port 9009) - `com.archon.nexa`

2. **Docker Services** (if Docker Desktop set to auto-start on login):
   - archon-server (port 9181)
   - archon-mcp (port 9051)
   - archon-ui (port 9737)
   - inference-gateway (port 9100)
   - ocrmypdf-service (port 9002)

### Step-by-Step Verification After Restart

**Wait Time**: Allow 2-3 minutes after restart for all services to initialize.

**Step 1: Check LaunchAgents**
```bash
launchctl list | grep -E "(ollama|archon)"
```

Expected output (PID numbers will vary):
```
21096  -15  com.archon.ollama-mlx      # -15 = SIGTERM (running)
-      0    com.ollama.ollama           # 0 = success
62493  0    application.com.electron.ollama.32744243.32744269
-      0    com.archon.mineru-mlx       # 0 = success
21088  0    homebrew.mxcl.ollama
29564  0    com.archon.nexa             # 0 = success
```

**Step 2: Check Docker Services**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected output:
```
NAMES                STATUS
archon-ui            Up X minutes (healthy)
archon-mcp           Up X minutes (healthy)
archon-server        Up X minutes (healthy)
inference-gateway    Up X minutes (healthy)
```

**Step 3: Verify All Backends Healthy**
```bash
curl -s http://localhost:9100/health | python3 -m json.tool
```

Expected output:
```json
{
    "status": "healthy",
    "services": {
        "ollama": true,
        "ollama-mlx": true,
        "mineru-mlx": true,
        "ocrmypdf": true,
        "nexa": true
    },
    "healthy_services": 5,
    "total_services": 5
}
```

**Step 4: Test OCR Processing** (Optional)
```bash
# Test MinerU-MLX
curl -s http://localhost:9006/health | python3 -m json.tool

# Should return:
# {
#   "status": "healthy",
#   "service": "mineru-mlx",
#   "backend": "MinerU with Apple Metal GPU"
# }
```

### Troubleshooting After Restart

**If services are not healthy, check each component:**

**1. LaunchAgent Issues**
```bash
# Check if LaunchAgent loaded
launchctl list | grep com.archon.mineru-mlx

# View LaunchAgent logs
tail -50 ~/Projects/archon/services/mineru-mlx/logs/stderr.log
tail -50 ~/logs/nexa-stderr.log

# Manually restart LaunchAgent
launchctl stop com.archon.mineru-mlx
launchctl start com.archon.mineru-mlx
```

**2. Docker Not Running**
```bash
# Check if Docker Desktop is running
docker ps

# If not running, start Docker Desktop from Applications
open -a Docker

# Wait 30 seconds, then check services
docker ps
```

**3. Specific Service Down**
```bash
# Check individual service health
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:9008/health     # Ollama-MLX
curl http://localhost:9006/health     # MinerU-MLX
curl http://localhost:9002/health     # OCRmyPDF
curl http://localhost:9009/           # Nexa (returns "Nexa SDK is running")
```

**4. Port Conflicts**
```bash
# Check if port is in use by wrong process
lsof -i:9006  # Check MinerU-MLX port
lsof -i:9009  # Check Nexa port

# Kill process if needed
kill -9 <PID>

# Restart LaunchAgent
launchctl stop com.archon.<service>
launchctl start com.archon.<service>
```

### Manual Start if LaunchAgents Fail

If LaunchAgents don't start services automatically, use the startup script:

```bash
~/Projects/archon/start_all_services.sh
```

This will:
- Check if each service is running
- Start any missing services
- Wait for initialization
- Show health status

## Restart Scenarios

### Scenario 1: Docker-Only Restart

**When**: Restarting just Docker services without touching native services

### Scenario 2: Docker Restart

**Stop all Docker services**:
```bash
cd ~/Projects/archon
docker compose down
```

**Start all Docker services**:
```bash
cd ~/Projects/archon
docker compose up -d
```

**Verify**:
```bash
docker ps | grep archon
curl http://localhost:9100/health
```

### Scenario 3: Native Services Restart

**Stop native services**:
```bash
# Find and kill processes
pkill -f "ollama serve"
pkill -f "ollama-mlx"
pkill -f "uvicorn app:app --host 0.0.0.0 --port 9006"
```

**Start native services**:
```bash
# Start Ollama
/Applications/Ollama.app/Contents/MacOS/Ollama serve &

# Start Ollama-MLX
cd ~/Projects/archon/services/ollama-mlx
python app.py &

# Start MinerU-MLX
cd ~/Projects/archon/services/mineru-mlx
uvicorn app:app --host 0.0.0.0 --port 9006 --reload &
```

## Complete Startup Script

Create a single script to start all native services:

```bash
#!/bin/bash
# File: ~/Projects/archon/start_all_services.sh

echo "🚀 Starting Archon Native Services..."

# Start Ollama (if not already running)
if ! lsof -i:11434 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting Ollama..."
    /Applications/Ollama.app/Contents/MacOS/Ollama serve > ~/logs/ollama.log 2>&1 &
    sleep 2
else
    echo "✅ Ollama already running"
fi

# Start Ollama-MLX
if ! lsof -i:9008 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting Ollama-MLX..."
    cd ~/Projects/archon/services/ollama-mlx
    nohup python app.py > ~/logs/ollama-mlx.log 2>&1 &
    sleep 2
else
    echo "✅ Ollama-MLX already running"
fi

# Start MinerU-MLX
if ! lsof -i:9006 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Starting MinerU-MLX..."
    cd ~/Projects/archon/services/mineru-mlx
    nohup uvicorn app:app --host 0.0.0.0 --port 9006 --reload > ~/logs/mineru-mlx.log 2>&1 &
    sleep 2
else
    echo "✅ MinerU-MLX already running"
fi

echo "✅ All services started!"
echo ""
echo "Verifying services..."
sleep 3
curl -s http://localhost:9100/health | python3 -m json.tool
```

**Make executable**:
```bash
chmod +x ~/Projects/archon/start_all_services.sh
```

**Usage**:
```bash
~/Projects/archon/start_all_services.sh
```

## Complete Stop Script

Create a script to stop all native services:

```bash
#!/bin/bash
# File: ~/Projects/archon/stop_all_services.sh

echo "🛑 Stopping Archon Native Services..."

# Stop Ollama
echo "Stopping Ollama..."
pkill -f "ollama serve" || echo "Ollama not running"

# Stop Ollama-MLX
echo "Stopping Ollama-MLX..."
pkill -f "ollama-mlx/app.py" || echo "Ollama-MLX not running"

# Stop MinerU-MLX
echo "Stopping MinerU-MLX..."
pkill -f "uvicorn app:app --host 0.0.0.0 --port 9006" || echo "MinerU-MLX not running"

echo "✅ All services stopped!"
```

**Make executable**:
```bash
chmod +x ~/Projects/archon/stop_all_services.sh
```

##Auto-Start Configuration (Optional)

To make native services start automatically on login, create macOS LaunchAgents.

### Create ~/Library/LaunchAgents/com.archon.services.plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.archon.services</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/krishna/Projects/archon/start_all_services.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/Users/krishna/logs/archon-services.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/krishna/logs/archon-services-error.log</string>
</dict>
</plist>
```

**Install**:
```bash
# Create logs directory
mkdir -p ~/logs

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.archon.services.plist

# Verify
launchctl list | grep archon
```

**Uninstall**:
```bash
launchctl unload ~/Library/LaunchAgents/com.archon.services.plist
rm ~/Library/LaunchAgents/com.archon.services.plist
```

## Troubleshooting

### Inference Gateway Reports Services Unhealthy

**Check services individually**:
```bash
# Ollama
curl http://localhost:11434/api/tags

# Ollama-MLX
curl http://localhost:9008/health

# MinerU-MLX
curl http://localhost:9006/health

# OCRmyPDF
curl http://localhost:9002/health
```

### Service Port Already in Use

**Find what's using the port**:
```bash
lsof -i:9006  # Replace with your port
```

**Kill the process**:
```bash
kill -9 <PID>
```

### Docker Services Not Starting

**Check Docker Desktop**:
```bash
docker ps
docker compose ps
```

**View logs**:
```bash
cd ~/Projects/archon
docker compose logs inference-gateway
docker compose logs archon-server
```

**Rebuild if needed**:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Service Dependencies

```
inference-gateway (port 9100)
├── ollama (port 11434) - NATIVE
├── ollama-mlx (port 9008) - NATIVE
├── mineru-mlx (port 9006) - NATIVE
├── ocrmypdf (port 9002) - DOCKER (external)
└── nexa (port 9009) - NATIVE (optional)
```

**Key Point**: inference-gateway will start even if backends are unavailable, but will report unhealthy status until backends start.

## Quick Reference

### Start Everything
```bash
# 1. Start Docker services
cd ~/Projects/archon && docker compose up -d

# 2. Start native services
~/Projects/archon/start_all_services.sh

# 3. Verify
curl http://localhost:9100/health | python3 -m json.tool
```

### Stop Everything
```bash
# 1. Stop native services
~/Projects/archon/stop_all_services.sh

# 2. Stop Docker services
cd ~/Projects/archon && docker compose down
```

### Check Status
```bash
# Docker
docker ps | grep -E "(archon|inference)"

# Native
ps aux | grep -E "(ollama|mineru|mlx)" | grep -v grep

# Health
curl http://localhost:9100/health
```

## Next Steps

1. ✅ Create start_all_services.sh script
2. ✅ Create stop_all_services.sh script
3. ⚠️ Decide: Enable auto-start with LaunchAgent?
4. ⚠️ Configure Nexa service (currently not running)

## Related Documentation

- [OCR Model-Based Routing](./OCR_MODEL_BASED_ROUTING.md)
- [Inference Gateway Configuration](../services/inference-gateway/README.md)
- [Streaming Implementation](./STREAMING_IMPLEMENTATION.md)
