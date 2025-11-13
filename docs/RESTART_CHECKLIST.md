# Archon Machine Restart Checklist

**Last Updated**: 2025-11-13

## After Restart - 3-Step Verification

### Wait: 2-3 minutes after login for services to initialize

---

## Step 1: Check LaunchAgents ✅

```bash
launchctl list | grep -E "(ollama|archon)"
```

**Expected**: Should see 5-6 services listed with status codes 0 or -15

---

## Step 2: Check Docker Services ✅

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Expected**: Should see 4 services with "(healthy)" status:
- archon-ui
- archon-mcp
- archon-server
- inference-gateway

---

## Step 3: Verify Backend Health ✅

```bash
curl -s http://localhost:9100/health | python3 -m json.tool
```

**Expected Output**:
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

---

## ⚠️ If Something's Wrong

### Docker Not Running?
```bash
open -a Docker
# Wait 30 seconds, then re-check
```

### LaunchAgent Failed?
```bash
# Run the startup script
~/Projects/archon/start_all_services.sh
```

### Specific Service Down?
```bash
# Check logs
tail -50 ~/Projects/archon/services/mineru-mlx/logs/stderr.log
tail -50 ~/logs/nexa-stderr.log

# Restart LaunchAgent
launchctl stop com.archon.mineru-mlx
launchctl start com.archon.mineru-mlx
```

---

## Port Reference

| Service | Port | Health Check |
|---------|------|--------------|
| Ollama | 11434 | `curl http://localhost:11434/api/tags` |
| Ollama-MLX | 9008 | `curl http://localhost:9008/health` |
| MinerU-MLX | 9006 | `curl http://localhost:9006/health` |
| Nexa | 9009 | `curl http://localhost:9009/` |
| OCRmyPDF | 9002 | `curl http://localhost:9002/health` |
| Inference Gateway | 9100 | `curl http://localhost:9100/health` |
| Archon Server | 9181 | `curl http://localhost:9181/health` |
| Archon MCP | 9051 | `curl http://localhost:9051/health` |
| Archon UI | 9737 | `http://localhost:9737` |

---

## Full Documentation

See `docs/SERVICE_MANAGEMENT.md` for:
- Detailed troubleshooting
- Service architecture
- Manual service management
- Docker restart procedures
