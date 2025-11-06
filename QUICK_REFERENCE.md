# Archon Quick Reference

## 🎯 Main Access Points

- **Frontend UI**: http://localhost:9737
- **Backend API**: http://localhost:9181
- **MCP Server**: http://localhost:9051

## 📊 All Archon Ports (CRITICAL - DO NOT CHANGE)

```
9000 - Docling OCR
9001 - LaTeX OCR  
9002 - OCRmyPDF
9003 - Stirling PDF
9004 - Parser Service
9051 - MCP Server
9052 - AI Agents (optional)
9181 - Backend API
9737 - Frontend UI
8053 - Agent Work Orders (optional)
8055 - MinerU (native Mac)
7100 - Marker PDF (optional)
```

## ⚠️ Ports to AVOID (Used by Other Projects)

```
5432 - Postgres (internal)
6333-6334 - Qdrant
6379 - Redis (internal)
8001 - n8n (via Caddy)
8002 - Open WebUI (via Caddy)
8004 - Caddy HTTP
8005 - Chamilo LMS
8008 - Neo4j (via Caddy)
8080 - Mediversity LMS
```

## 🚀 Start Commands

```bash
# Default (Server + MCP + Frontend)
docker compose up -d

# With AI Agents
docker compose --profile agents up -d

# With Work Orders
docker compose --profile work-orders up -d

# Check status
docker ps
docker compose ps
```

## 🔍 Check Service Health

```bash
curl http://localhost:9181/health  # Backend
curl http://localhost:9051/health  # MCP
curl http://localhost:9737         # Frontend
```

## 📝 Files to Check

- `.env` - Port configuration
- `docker-compose.yml` - Service definitions
- `PORT_MAPPING.md` - Full reference
