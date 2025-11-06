# Archon Complete Architecture

## System Overview

Archon is a microservices-based system with Docker containers for core services and a native Mac service for MinerU (GPU-accelerated PDF processing).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOCKER: ARCHON UI                                │
│                         Container: archon-ui                             │
│                         Port: 9737 (external)                            │
│                         Tech: React + Vite                               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ REST API + WebSocket
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DOCKER: ARCHON SERVER                               │
│                      Container: archon-server                            │
│                      Port: 9181 (external: 8181)                         │
│                      Tech: FastAPI + Socket.IO                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Core Features:                                                  │    │
│  │ • Project & Task Management                                     │    │
│  │ • Knowledge Base (RAG)                                          │    │
│  │ • Document Processing                                           │    │
│  │ • Progress Tracking                                             │    │
│  │ • Web Crawling                                                  │    │
│  └────────────────────────────────────────────────────────────────┘    │
└──────┬──────────────────┬──────────────────┬───────────────────────────┘
       │                  │                  │
       │ REST             │ REST             │ REST
       ▼                  ▼                  ▼
┌─────────────┐  ┌─────────────────┐  ┌──────────────────────────────────┐
│   DOCKER:   │  │    DOCKER:      │  │   NATIVE MAC SERVICE:            │
│ ARCHON MCP  │  │ OCR SERVICES    │  │   MINERU SERVICE                 │
│             │  │                 │  │                                  │
│ Port: 9051  │  │ ┌─────────────┐ │  │ Port: 8055                       │
│             │  │ │ parser-     │ │  │ Tech: FastAPI + MinerU           │
│ Tech: MCP   │  │ │ service     │ │  │ GPU: Apple Silicon MPS           │
│ Protocol    │  │ │ Port: 9004  │ │  │                                  │
│ (Claude)    │  │ └─────────────┘ │  │ Features:                        │
│             │  │                 │  │ • Advanced PDF extraction        │
│             │  │ ┌─────────────┐ │  │ • Chart data extraction          │
│             │  │ │ docling-ocr │ │  │ • Formula recognition            │
│             │  │ │ Port: 9000  │ │  │ • Table extraction               │
│             │  │ └─────────────┘ │  │ • Image extraction               │
│             │  │                 │  │                                  │
│             │  │ ┌─────────────┐ │  │ Connected via:                   │
│             │  │ │ latex-ocr   │ │  │ host.docker.internal:8055        │
│             │  │ │ Port: 9001  │ │  └──────────────────────────────────┘
│             │  │ └─────────────┘ │
│             │  │                 │
│             │  │ ┌─────────────┐ │
│             │  │ │ ocrmypdf-   │ │
│             │  │ │ service     │ │
│             │  │ │ Port: 9002  │ │
│             │  │ └─────────────┘ │
│             │  │                 │
│             │  │ ┌─────────────┐ │
│             │  │ │ stirling-   │ │
│             │  │ │ pdf         │ │
│             │  │ │ Port: 9003  │ │
│             │  │ └─────────────┘ │
└─────────────┘  └─────────────────┘
```

## Service Communication Matrix

| From Service | To Service | Protocol | URL | Purpose |
|-------------|------------|----------|-----|---------|
| **User Browser** | archon-ui | HTTP | `http://localhost:9737` | Web interface |
| **archon-ui** | archon-server | REST + WS | `http://archon-server:9181` | All API calls |
| **archon-server** | archon-mcp | REST | `http://archon-mcp:9051` | MCP tool execution |
| **archon-server** | parser-service | REST | `http://parser-service:9004` | PDF parsing (basic) |
| **archon-server** | docling-ocr | REST | `http://docling-ocr:9000` | Document OCR |
| **archon-server** | latex-ocr | REST | `http://latex-ocr:9001` | Formula extraction |
| **archon-server** | ocrmypdf-service | REST | `http://ocrmypdf-service:9002` | PDF OCR |
| **archon-server** | stirling-pdf | REST | `http://stirling-pdf:8080` | Batch PDF processing |
| **archon-server** | mineru-service | REST | `http://host.docker.internal:8055` | **Advanced PDF + Charts** |
| **parser-service** | docling-ocr | REST | `http://docling-ocr:9000` | Orchestrated OCR |
| **parser-service** | latex-ocr | REST | `http://latex-ocr:9001` | Orchestrated formulas |

## Port Mapping Reference

### External Ports (Accessible from Mac)
| Port | Service | Purpose |
|------|---------|---------|
| **9737** | archon-ui | Web interface |
| **9181** | archon-server | Main API server |
| **9051** | archon-mcp | MCP protocol server |
| **8055** | mineru-service (native) | Advanced PDF processing |
| **9000** | docling-ocr | Document OCR |
| **9001** | latex-ocr | LaTeX formula extraction |
| **9002** | ocrmypdf-service | OCRmyPDF wrapper |
| **9003** | stirling-pdf | Stirling PDF tools |
| **9004** | parser-service | Parser orchestrator |

### Internal Docker Network
All services communicate via `app-network` bridge network using container names as hostnames.

## Service Groupings

### 🎯 Core Archon Services (Always Running)
```
archon-ui          → Web interface (React)
archon-server      → Main API (FastAPI + Socket.IO)
archon-mcp         → MCP protocol server
```

### 📄 OCR Services (Profile: `ocr`)
```
parser-service     → Orchestrates docling + latex-ocr
docling-ocr        → General document OCR (ARM64 native)
latex-ocr          → Formula to LaTeX conversion (ARM64 native)
ocrmypdf-service   → Docker-based OCRmyPDF wrapper
stirling-pdf       → Web-based batch PDF processing
```

### 🚀 Advanced OCR Services (Profile: `advanced-ocr`)
```
marker-pdf         → PDF to Markdown with formulas & tables
mineru-service     → (Docker x86 option - NOT RECOMMENDED)
```

### 💻 Native Mac Services (Outside Docker)
```
mineru-service     → Advanced PDF + chart extraction (Apple GPU)
                     Port: 8055
                     Started: bash start_mineru_service.sh
```

### 🤖 AI Agents (Profile: `agents`)
```
archon-agents      → ML/Reranking service
                     Port: 9052
```

### 📋 Work Orders (Profile: `work-orders`)
```
archon-agent-work-orders → Workflow execution service
                            Port: 9053
```

## Data Flow: PDF Processing with MinerU

### User uploads PDF for advanced processing:

```
1. User Browser
   │ POST /api/knowledge/upload
   ▼
2. Archon UI (9737)
   │ FormData with PDF file
   ▼
3. Archon Server (9181)
   │ Receives file, detects advanced processing needed
   │ POST http://host.docker.internal:8055/process
   ▼
4. MinerU Service (8055) 🚀 NATIVE MAC - GPU ACCELERATED
   │ • Uses Apple Silicon MPS GPU
   │ • Extracts text, formulas, tables, images
   │ • Extracts chart data from images
   │ • Returns structured markdown + images
   ▼
5. Archon Server (9181)
   │ Stores results in Supabase
   │ Updates progress
   ▼
6. Archon UI (9737)
   │ Polls for completion
   │ Displays results to user
   ▼
7. User Browser
   │ Views extracted content + charts
```

## Starting Services

### Start Core Stack (UI + Server + MCP)
```bash
docker compose up -d
```

### Start with OCR Services
```bash
docker compose --profile ocr up -d
```

### Start with Advanced OCR (Marker only)
```bash
docker compose --profile advanced-ocr up -d marker-pdf
```

### Start Native MinerU Service (RECOMMENDED for Mac)
```bash
cd /Users/krishna/Projects/archon/python
bash start_mineru_service.sh
```
Runs on port 8055, accessible to Docker containers via `host.docker.internal:8055`

## Integration Points for MinerU

### Backend Changes Needed
**File**: `python/src/server/api_routes/knowledge_api.py`

Add endpoint to call native MinerU service:
```python
@router.post("/knowledge/process-advanced")
async def process_advanced_pdf(file: UploadFile):
    """Process PDF with native MinerU service"""

    # Call native service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://host.docker.internal:8055/process",
            files={"file": (file.filename, file.file, file.content_type)},
            data={
                "extract_charts": "true",
                "device": "mps",
                "lang": "en"
            }
        )

    result = response.json()
    # Store in database, return to UI
    return result
```

### Frontend Changes Needed
**File**: `archon-ui-main/src/features/knowledge/services/knowledgeService.ts`

Add method to call advanced processing:
```typescript
export const knowledgeService = {
  // ... existing methods ...

  async processAdvancedPdf(file: File): Promise<ProcessResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post(
      '/knowledge/process-advanced',
      formData
    );

    return response.data;
  }
}
```

## Performance Comparison

### MinerU Native (Apple GPU) vs Docker Services

| Metric | Native MinerU | parser-service | docling-ocr | marker-pdf |
|--------|---------------|----------------|-------------|------------|
| **Speed** | ⚡ ~60s (13 pages) | ~45s | ~30s | ~90s |
| **GPU** | ✅ Apple MPS | ❌ CPU only | ❌ CPU only | ❌ CPU only |
| **Charts** | ✅ Extracts data | ❌ No | ❌ No | ⚠️ Limited |
| **Formulas** | ✅ High accuracy | ⚠️ Basic | ⚠️ Basic | ✅ Good |
| **Tables** | ✅ Excellent | ⚠️ Basic | ⚠️ Basic | ✅ Good |
| **Setup** | Manual start | Auto | Auto | Auto |
| **Management** | Separate process | Docker | Docker | Docker |

## Health Check URLs

All services expose health endpoints:

| Service | Health Check URL |
|---------|-----------------|
| archon-ui | http://localhost:9737 |
| archon-server | http://localhost:9181/health |
| archon-mcp | http://localhost:9051/health |
| mineru-service | http://localhost:8055/health |
| parser-service | http://localhost:9004/health |
| docling-ocr | http://localhost:9000/health |
| latex-ocr | http://localhost:9001/ |
| ocrmypdf-service | http://localhost:9002/health |
| stirling-pdf | http://localhost:9003/api/v1/info/status |

## Testing the Complete Stack

### 1. Check All Services Are Running
```bash
# Check Docker services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check native MinerU service
curl http://localhost:8055/health
```

### 2. Test MinerU Service Directly
```bash
curl -X POST http://localhost:8055/process \
  -F "file=@/path/to/test.pdf" \
  -F "device=mps" \
  -F "extract_charts=true" \
  -F "lang=en"
```

### 3. Test End-to-End via UI
1. Open http://localhost:9737
2. Navigate to Knowledge Base
3. Upload a PDF with charts
4. Select "Advanced Processing (MinerU)"
5. Wait for processing
6. View extracted text, formulas, tables, and chart data

## Docker Network Configuration

### Bridge Network: `app-network`
All Docker containers communicate via this network:
- DNS resolution: Container names resolve to IP addresses
- Internal communication: No exposed ports needed between containers
- External access: Only explicitly mapped ports are accessible from host

### Host Access: `host.docker.internal`
Special Docker hostname that allows containers to access services running on the host Mac:
- Docker services → Native MinerU: `http://host.docker.internal:8055`
- Configured in docker-compose.yml with `extra_hosts`

## Volumes and Persistence

### Model Caches (Large, Persistent)
- `docling-models` - HuggingFace models for docling
- `latex-ocr-models` - pix2tex models for LaTeX OCR
- `marker-models` - Marker PDF models
- `mineru-models` - MinerU models (Docker option only)

### Temporary Storage
- `ocrmypdf-temp` - Temp files for OCRmyPDF
- `docling-temp` - Temp files for docling processing

### Configuration Storage
- `stirling-pdf-configs` - Stirling PDF settings
- `stirling-pdf-training` - Tesseract training data
- `stirling-pdf-logs` - Log files

## Environment Variables

Key environment variables in `.env`:

```bash
# Ports
ARCHON_SERVER_PORT=8181      # Internal: 8181, External: 9181
ARCHON_MCP_PORT=8051         # Internal: 8051, External: 9051
ARCHON_UI_PORT=3737          # Internal: 3737, External: 9737
MINERU_PORT=8055             # Native service port

# API Keys
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
OPENAI_API_KEY=...

# Logging
LOG_LEVEL=INFO
```

## Next Steps for Integration

1. ✅ Native MinerU service created and tested
2. ✅ Docker compose updated with alternative option
3. ✅ Documentation completed
4. ⏳ **Update archon-server to call native MinerU service**
5. ⏳ **Add UI option for advanced processing**
6. ⏳ **Test end-to-end with chart extraction**
7. ⏳ **Monitor performance and error handling**

## Recommended Setup for Development

```bash
# Terminal 1: Start Docker services
cd /Users/krishna/Projects/archon
docker compose --profile ocr up -d

# Terminal 2: Start native MinerU service
cd /Users/krishna/Projects/archon/python
bash start_mineru_service.sh

# Terminal 3: Monitor logs
docker compose logs -f archon-server

# Access UI
open http://localhost:9737
```
