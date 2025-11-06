# OCR Services Integration Guide

## Overview

Archon now integrates with two OCR services through the microservices architecture:
- **Docling OCR** - IBM's document parsing service (optimal for scanned documents and complex layouts)
- **OCRmyPDF** - Tesseract-based OCR (optimal for adding searchable text layer to scanned PDFs)

Both services are optional and use Docker Compose profiles for deployment.

## Architecture

### Service Discovery

OCR services are integrated through Archon's service discovery system (`python/src/server/config/service_discovery.py`):

```python
# Ports (with defaults)
DOCLING_OCR_PORT=9000
OCRMYPDF_PORT=9002

# Docker container names
docling-ocr
ocrmypdf-service

# Service discovery URLs
get_docling_ocr_url()  # Returns http://docling-ocr:9000 (Docker) or http://localhost:9000 (Local)
get_ocrmypdf_url()     # Returns http://ocrmypdf-service:9002 (Docker) or http://localhost:9002 (Local)
```

### HTTP-Based Communication

All services communicate via HTTP using service discovery for automatic URL resolution.

## Deployment

### Starting OCR Services

```bash
# Start all services including OCR
docker compose --profile ocr up -d

# Or start individual OCR services
docker compose --profile ocr up -d docling-ocr
docker compose --profile ocr up -d ocrmypdf-service

# Stop OCR services
docker compose stop docling-ocr ocrmypdf-service
```

### Environment Variables

Add to `.env` (optional - uses defaults if not set):

```bash
# Docling OCR Port (default: 9000)
DOCLING_OCR_PORT=9000

# OCRmyPDF Port (default: 9002)
OCRMYPDF_PORT=9002
```

## Using Docling OCR Service

### Via Service Client (Python)

```python
from src.server.services.docling_service import get_docling_client

# Get client instance
docling = get_docling_client()

# Check availability
if docling.is_available():
    # Process PDF
    result = await docling.process_pdf(
        file_content=pdf_bytes,
        filename="document.pdf",
        output_format="markdown",  # text, markdown, html, doctags
        do_ocr=True,
        include_tables=True
    )

    # Process image
    result = await docling.process_image(
        file_content=image_bytes,
        filename="scan.png",
        output_format="text",
        include_tables=True
    )

    # Health check
    health = await docling.health_check()
```

### Via MCP Tools (AI IDEs)

MCP tools are available to AI IDEs (Claude Code, Cursor, Windsurf):

```python
# Process PDF
archon:docling_process_pdf(
    file_path="/path/to/document.pdf",
    output_format="markdown",
    do_ocr=True,
    include_tables=True
)

# Process Image
archon:docling_process_image(
    file_path="/path/to/scan.png",
    output_format="text",
    include_tables=True
)

# Health Check
archon:docling_health()
```

### Via HTTP Direct

```bash
# Process PDF
curl -X POST http://localhost:9000/ocr/pdf \
  -F "file=@document.pdf" \
  -F "output_format=text" \
  -F "do_ocr=true" \
  -F "include_tables=true"

# Process Image
curl -X POST http://localhost:9000/ocr/image \
  -F "file=@scan.png" \
  -F "output_format=markdown" \
  -F "include_tables=true"

# Health Check
curl http://localhost:9000/health
```

## When to Use Each OCR Service

### Docling OCR (Port 9000)
**Best For:**
- ✅ Scanned documents requiring OCR
- ✅ Complex layouts with tables
- ✅ Multi-column documents
- ✅ Markdown generation with structure preservation
- ✅ Table structure recognition

**Not Optimal For:**
- ❌ Text-based PDFs (use PyMuPDF direct instead - 19,000x faster)
- ❌ Simple text extraction

**Performance:**
- Text-based PDFs: ~10s (returns empty - not suitable)
- Scanned PDFs: ~15-30s (excellent quality with structure)

### OCRmyPDF (Port 9002)
**Best For:**
- ✅ Adding searchable text layer to scanned PDFs
- ✅ Batch OCR processing
- ✅ Preserving original PDF structure

**Performance:**
- ~0.6s per page (6,192 words/second)
- Production-ready with stdin/stdout pattern

### PyMuPDF (Built-in)
**Best For:**
- ✅ Text-based PDFs (95% of documents)
- ✅ Fast text extraction

**Performance:**
- ~0.01s per page (263,124 words/second)
- Perfect for research papers, articles, reports

## Service Discovery Integration

### Adding New OCR Services

To add a new OCR service:

1. **Update Service Discovery** (`python/src/server/config/service_discovery.py`):
```python
# Add port
new_ocr_port = os.getenv("NEW_OCR_PORT", "9003")

self.DEFAULT_PORTS = {
    # ... existing ports
    "new_ocr": int(new_ocr_port) if new_ocr_port else None,
}

# Add service name mapping
SERVICE_NAMES = {
    # ... existing names
    "new_ocr": "new-ocr-service",
}

# Add convenience function
def get_new_ocr_url() -> str | None:
    return get_discovery().get_service_url("new_ocr")
```

2. **Create Service Client** (`python/src/server/services/new_ocr_service.py`):
```python
from ..config.service_discovery import get_new_ocr_url, is_service_available

class NewOcrServiceClient:
    def is_available(self) -> bool:
        return is_service_available("new_ocr")

    async def process(self, file_content: bytes, filename: str) -> dict:
        url = get_new_ocr_url()
        # ... HTTP call to service
```

3. **Add MCP Tools** (`python/src/mcp_server/features/new_ocr/`):
```python
def register_new_ocr_tools(mcp: FastMCP):
    @mcp.tool()
    async def new_ocr_process(ctx: Context, file_path: str) -> str:
        # Tool implementation
```

4. **Register in MCP Server** (`python/src/mcp_server/mcp_server.py`):
```python
from src.mcp_server.features.new_ocr import register_new_ocr_tools
register_new_ocr_tools(mcp)
```

## Troubleshooting

### Docling Service Not Available

```bash
# Check if service is running
docker ps | grep docling-ocr

# Start with OCR profile
docker compose --profile ocr up -d docling-ocr

# Check logs
docker logs docling-ocr

# Health check
curl http://localhost:9000/health
```

### Service Discovery Issues

```python
from src.server.config.service_discovery import get_discovery

discovery = get_discovery()

# Check if service is configured
if discovery.is_service_available("docling_ocr"):
    url = discovery.get_service_url("docling_ocr")
    print(f"Docling URL: {url}")
```

### Port Conflicts

If default ports are in use, override in `.env`:

```bash
# Use different ports
DOCLING_OCR_PORT=9010
OCRMYPDF_PORT=9012
```

## Testing Integration

### Test Service Discovery

```bash
# From inside archon-server container
docker compose exec archon-server python -c "
from src.server.config.service_discovery import get_discovery

discovery = get_discovery()
print('Docling available:', discovery.is_service_available('docling_ocr'))
print('Docling URL:', discovery.get_service_url('docling_ocr'))
"
```

### Test Service Client

```bash
# From inside archon-server container
docker compose exec archon-server python -c "
import asyncio
from src.server.services.docling_service import get_docling_client

async def test():
    client = get_docling_client()
    print('Available:', client.is_available())
    health = await client.health_check()
    print('Health:', health)

asyncio.run(test())
"
```

### Test MCP Tools

Use the MCP testing UI at `http://localhost:8051` or test via Claude Code:

```
Use the archon:docling_health tool to check if Docling OCR is available
```

## Performance Comparison

| Method | Words/Second | Use Case |
|--------|-------------|----------|
| **PyMuPDF** | 263,124 | Text-based PDFs (95% of docs) |
| **OCRmyPDF** | 6,192 | Scanned PDFs |
| **Docling** | ~250 | Scanned docs with complex layouts |

## API Endpoints

### Docling OCR (Port 9000)

- `POST /ocr/pdf` - Process PDF document
- `POST /ocr/image` - Process image document
- `POST /ocr/batch` - Batch processing
- `POST /convert/document` - Generic converter
- `GET /health` - Health check

### OCRmyPDF (Port 9002)

- `POST /process` - Process PDF with OCR
- `GET /health` - Health check

## Files Modified

### Service Discovery
- `python/src/server/config/service_discovery.py` - Added Docling and OCRmyPDF services

### Service Clients
- `python/src/server/services/docling_service.py` - Created Docling HTTP client

### MCP Integration
- `python/src/mcp_server/features/docling/` - Created MCP tools directory
- `python/src/mcp_server/features/docling/__init__.py` - Module initialization
- `python/src/mcp_server/features/docling/docling_tools.py` - MCP tool implementations
- `python/src/mcp_server/mcp_server.py` - Registered Docling tools

## Next Steps

1. Start OCR services: `docker compose --profile ocr up -d`
2. Test integration: Use MCP tools or service clients
3. Monitor performance: Check logs and health endpoints
4. Optimize usage: Use appropriate service for each document type

## Additional Resources

- [Docling GitHub](https://github.com/DS4SD/docling)
- [OCRmyPDF Documentation](https://ocrmypdf.readthedocs.io/)
- [Archon Service Discovery](../python/src/server/config/service_discovery.py)
- [Previous OCR Testing Results](/tmp/docling_issue_summary.md)
