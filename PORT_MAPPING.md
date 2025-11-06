# Archon Port Mapping & Service Reference

**Last Updated:** 2025-11-06
**Purpose:** Master reference for all ports to prevent conflicts

---

## 🎯 ARCHON CORE SERVICES

### Main Services (Always Running)

| Service Name | Container Name | Image | External Port | Internal Port | Access URL | Status |
|--------------|----------------|-------|---------------|---------------|------------|--------|
| **Backend API** | archon-server | archon-archon-server | **9181** | 9181 | http://localhost:9181 | ✅ HEALTHY |
| **MCP Server** | archon-mcp | archon-archon-mcp | **9051** | 9051 | http://localhost:9051 | ✅ HEALTHY |
| **Frontend UI** | archon-ui | archon-archon-frontend | **9737** | 3737 | http://localhost:9737 | ✅ HEALTHY |

### Optional Services (Profile-based)

| Service Name | Container Name | External Port | Internal Port | Profile | Status |
|--------------|----------------|---------------|---------------|---------|--------|
| **AI Agents** | archon-agents | 9052 | 9052 | `agents` | ⚪ Not Started |
| **Agent Work Orders** | archon-agent-work-orders | 8053 | 8053 | `work-orders` | ⚪ Not Started |

---

## 🔍 ARCHON OCR/PROCESSING SERVICES

| Service Name | Container Name | Image | External Port | Internal Port | Purpose | Status |
|--------------|----------------|-------|---------------|---------------|---------|--------|
| **Docling OCR** | docling-ocr | archon-docling-ocr | **9000** | 9000 | Document layout analysis | ✅ HEALTHY |
| **LaTeX OCR** | latex-ocr | d50b4baa6bf4 | **9001** | 9001 | Mathematical formula OCR | ✅ HEALTHY |
| **OCRmyPDF** | ocrmypdf-service | archon-ocrmypdf-service | **9002** | 9001 | PDF OCR processing | ✅ HEALTHY |
| **Stirling PDF** | stirling-pdf | stirlingtools/stirling-pdf:latest | **9003** | 8080 | PDF manipulation | ✅ HEALTHY |
| **Parser Service** | parser-service | archon-parser-service | **9004** | 9004 | Document parsing | ✅ HEALTHY |
| **DeepSeek-OCR MLX** | (Native Mac) | N/A | **9005** | 9005 | Vision-language OCR (Apple Metal GPU) | 🔵 Native Service |
| **MinerU MLX** | (Native Mac) | N/A | **9006** | 9006 | PDF processing with formulas/tables (Apple Metal GPU) | 🔵 Native Service |

### Advanced OCR Services (Profile: `advanced-ocr`)

| Service Name | External Port | Internal Port | Purpose | Status |
|--------------|---------------|---------------|---------|--------|
| **Marker PDF** | 7100 | 7000 | PDF to Markdown with formulas | ⚪ Not Started |

---

## 💾 ARCHON DATABASE & STORAGE

| Service Name | Container Name | Image | External Port | Internal Port | Purpose | Status |
|--------------|----------------|-------|---------------|---------------|---------|--------|
| **PostgreSQL (pgvector)** | rag_postgres_local | pgvector/pgvector:pg15 | **5433** | 5432 | Local vector DB | ✅ HEALTHY |
| **Supabase Cloud** | N/A | N/A | 443 (HTTPS) | N/A | Cloud database | ✅ Connected |

**Supabase URL:** `https://ttwoultatioehvcugqya.supabase.co`

---

## 🚫 RESERVED PORTS (Other Running Services - DO NOT USE)

### Mediversity LMS Project

| Service | Port | Purpose |
|---------|------|---------|
| mediversity-lms | 8080 | LMS Application |
| mediversity-postgres | 5432 (internal) | Postgres DB |
| mediversity-redis | 6379 (internal) | Redis Cache |

### Local AI Packaged Project

| Service | Port(s) | Purpose |
|---------|---------|---------|
| chamilo-lms | 8005 | Chamilo LMS |
| n8n | 5678 (internal), 8001 (via Caddy) | Workflow automation |
| open-webui | 8080 (internal), 8002 (via Caddy) | AI Chat UI |
| neo4j | 7473-7474, 7687 (internal), 8008 (via Caddy) | Graph database |
| postgres | 5432 (internal) | Database |
| mysql-chamilo | 3306, 33060 (internal) | MySQL database |
| redis | 6379 (internal) | Cache |
| qdrant | 6333-6334 | Vector database |
| caddy | 8001, 8002, 8004, 8008 | Reverse proxy |
| cloudflared | 2000 (internal) | Cloudflare tunnel |

### Twingate

| Service | Purpose |
|---------|---------|
| twingate-connector | Zero Trust Network Access |

---

## 📋 ARCHON PORT ALLOCATION STRATEGY

### Port Ranges

- **9000-9099**: OCR & Processing Services
  - 9000: Docling OCR
  - 9001: LaTeX OCR
  - 9002: OCRmyPDF
  - 9003: Stirling PDF
  - 9004: Parser Service
  - 9005: DeepSeek-OCR MLX (native Mac)
  - 9006: MinerU MLX (native Mac)
  - 9051: MCP Server
  - 9052: AI Agents (optional)

- **9100-9199**: Core Archon Services
  - 9181: Backend API Server

- **9700-9799**: Frontend & UI Services
  - 9737: Frontend UI

- **8000-8099**: Special Services
  - 8053: Agent Work Orders (optional)

- **7000-7099**: Advanced Processing (optional)
  - 7100: Marker PDF

---

## 🔒 ENVIRONMENT VARIABLES (.env)

```bash
# Core Service Ports
ARCHON_SERVER_PORT=9181
ARCHON_MCP_PORT=9051
ARCHON_AGENTS_PORT=9052
ARCHON_UI_PORT=9737
ARCHON_DOCS_PORT=9838

# Optional Service Ports
AGENT_WORK_ORDERS_PORT=8053
MARKER_PORT=7100

# Database
SUPABASE_URL=https://ttwoultatioehvcugqya.supabase.co
SUPABASE_SERVICE_KEY=[configured]

# Native MLX Services (Apple Silicon with Metal GPU)
MINERU_SERVICE_URL=http://host.docker.internal:9006
DEEPSEEK_OCR_MLX_URL=http://localhost:9005

# OCR Engine Selection
OCR_ENGINE=deepseek-mlx
```

---

## 🚀 STARTING SERVICES

### Default Services (Server, MCP, Frontend)
```bash
docker compose up -d
```

### With AI Agents
```bash
docker compose --profile agents up -d
```

### With Agent Work Orders
```bash
docker compose --profile work-orders up -d
```

### With OCR Services
```bash
docker compose --profile ocr up -d
```

### With Advanced OCR (Marker)
```bash
docker compose --profile advanced-ocr up -d
```

---

## 🔍 HEALTH CHECK URLS

| Service | Health Check URL |
|---------|------------------|
| Backend API | http://localhost:9181/health |
| MCP Server | http://localhost:9051/health |
| Frontend UI | http://localhost:9737 |
| Docling OCR | http://localhost:9000/health |
| LaTeX OCR | http://localhost:9001/health |
| OCRmyPDF | http://localhost:9002/health |
| Stirling PDF | http://localhost:9003 |
| Parser Service | http://localhost:9004/health |
| DeepSeek-OCR MLX | http://localhost:9005/health |
| MinerU MLX | http://localhost:9006/health |

---

## 🛠️ TROUBLESHOOTING

### Port Conflicts

If you see port conflicts:

1. Check what's using the port:
   ```bash
   lsof -i :PORT_NUMBER
   ```

2. Stop conflicting services or change Archon ports in `.env`

3. Restart Archon services:
   ```bash
   docker compose down
   docker compose up -d
   ```

### Service Not Starting

1. Check logs:
   ```bash
   docker compose logs SERVICE_NAME
   ```

2. Check health:
   ```bash
   docker ps
   ```

3. Verify .env configuration matches docker-compose.yml

---

## 📝 NOTES

- **DO NOT** use ports 8000-8008 (reserved for other projects)
- **DO NOT** use port 5432 internally (conflicts with other Postgres instances)
- MinerU runs natively on Mac for Apple GPU acceleration (not in Docker)
- All Archon services use `app-network` bridge network
- Frontend proxies API requests to backend (no CORS issues)

---

## 🔄 VERSION HISTORY

- **2025-11-06**: Initial port mapping created
  - Backend: 9181
  - MCP: 9051
  - Frontend: 9737
  - All OCR services: 9000-9004
