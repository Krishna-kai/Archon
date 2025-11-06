# OCRmyPDF Implementation

## Overview

Archon uses OCRmyPDF as the primary OCR engine for extracting text from PDF documents. OCRmyPDF is optimized for Apple Silicon (M1/M2/M3/M4) with native ARM64 support and CPU-based processing.

## Why OCRmyPDF?

### Key Advantages
- **Native ARM64 Support**: No emulation needed on Apple Silicon Macs
- **CPU-Optimized**: No GPU required, uses all available CPU cores efficiently
- **Academic PDF Focused**: Specifically designed for academic papers like IEEE documents
- **Mature & Reliable**: Industry-standard OCR solution based on Tesseract
- **Docker-Based**: Clean containerized deployment with minimal dependencies

### Comparison with DeepSeek OCR
OCRmyPDF replaced DeepSeek OCR for the following reasons:
- Better ARM64 compatibility (no x86_64 emulation overhead)
- No GPU requirements (DeepSeek required NVIDIA GPU or slow CPU mode)
- More reliable for academic PDFs with complex layouts
- Faster processing times on Mac M4 hardware
- Simpler deployment (single Docker container vs multi-service setup)

## Architecture

### Implementation Location
**File**: `python/src/server/utils/document_processing.py`

**Functions**:
- `extract_text_from_pdf_ocrmypdf()` - Main OCRmyPDF integration
- `extract_text_from_pdf_ocr()` - Wrapper that calls OCRmyPDF

### Docker Integration
OCRmyPDF runs as a containerized process using the `jbarlow83/ocrmypdf-alpine` image.

**Image**: `jbarlow83/ocrmypdf-alpine`
**Architecture**: ARM64 native
**Data Transfer**: stdin/stdout (no volume mounting required)

### Process Flow
1. PDF bytes received from upload API
2. PDF sent to OCRmyPDF container via stdin
3. OCRmyPDF processes PDF with:
   - `--deskew`: Straighten skewed pages
   - `--rotate-pages`: Auto-rotate pages to correct orientation
   - `--optimize 1`: Light optimization for faster processing
   - `--force-ocr`: Force OCR even if text already exists
4. OCR'd PDF returned via stdout
5. PyMuPDF extracts text from OCR'd PDF
6. Text returned with page markers (`--- Page N ---`)

### Dependencies

**Python Packages** (`python/pyproject.toml`):
- `pymupdf>=1.24.0` - For text extraction from OCR'd PDFs

**Docker Requirements** (`python/Dockerfile.server`):
- `docker.io` - Docker CLI for running OCRmyPDF container

**External Container**:
- `jbarlow83/ocrmypdf-alpine` - OCRmyPDF processing engine

## Implementation Details

### Key Code
```python
async def extract_text_from_pdf_ocrmypdf(file_content: bytes, filename: str) -> str:
    """
    Extract text from PDF files using OCRmyPDF (ARM64-native, CPU-optimized).
    Uses stdin/stdout for data transfer to avoid volume mounting issues between containers.
    """
    cmd = [
        "docker", "run", "--rm", "-i",
        "jbarlow83/ocrmypdf-alpine",
        "--deskew",           # Straighten pages
        "--rotate-pages",     # Auto-rotate pages
        "--optimize", "1",    # Light optimization
        "--force-ocr",        # Force OCR even if text exists
        "-", "-"              # stdin -> stdout
    ]

    result = subprocess.run(
        cmd,
        input=file_content,     # Send PDF to stdin
        capture_output=True,    # Capture stdout and stderr
        timeout=300             # 5 minute timeout
    )

    # Extract text from OCR'd PDF using PyMuPDF
    # ... (see source code for full implementation)
```

### stdin/stdout Approach
The implementation uses stdin/stdout for data transfer instead of volume mounting:

**Why?**
- Volume mounting doesn't work between containers (archon-server → OCRmyPDF)
- Temp directories inside containers are not accessible to sibling containers
- stdin/stdout is simpler and more reliable

**How?**
- PDF bytes passed to `subprocess.run()` with `input=file_content`
- OCRmyPDF reads from stdin with `-` argument
- OCRmyPDF writes to stdout with second `-` argument
- Result captured in `result.stdout` as bytes

### Text Extraction
PyMuPDF (fitz) is used to extract text from the OCR'd PDF:

```python
doc = fitz.open(temp_path)
text_parts = []

for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")

doc.close()
extracted_text = "\n".join(text_parts)
```

## Performance

### Benchmarks (Mac M4)
- **5-page academic PDF**: ~20 seconds
- **Processing speed**: ~4 seconds per page
- **Text quality**: Comparable to standard PDF extraction, better for scanned documents
- **CPU usage**: Utilizes all available cores efficiently

### Optimization Flags
- `--deskew`: Improves accuracy for skewed scans
- `--rotate-pages`: Auto-corrects orientation
- `--optimize 1`: Balances speed vs quality (level 1 = light optimization)
- `--force-ocr`: Ensures consistent OCR processing

**Note**: `--remove-background` flag is NOT used (not implemented in current version)

## Configuration

### Environment Variables
No specific environment variables required. OCRmyPDF integration works out-of-box.

### Docker Socket
The archon-server container must have access to the Docker socket to run OCRmyPDF containers:

**docker-compose.yml**:
```yaml
archon-server:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

### Container Requirements
The archon-server container needs:
1. Docker CLI installed (`docker.io` package)
2. PyMuPDF installed (`pymupdf` package)
3. Access to Docker socket

## Usage

### API Endpoint
OCRmyPDF is automatically used when uploading documents with `use_ocr=true`:

```bash
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@document.pdf' \
  -F 'use_ocr=true' \
  -F 'knowledge_type=technical'
```

### Processing Flow
1. Document upload API receives PDF with `use_ocr=true`
2. `extract_text_from_pdf_ocr()` called
3. OCRmyPDF processes PDF via Docker container
4. Text extracted with PyMuPDF
5. Text chunked and stored in vector database

## Logging

### Success Logs
```
INFO | Using OCRmyPDF to extract text from PDF: document.pdf
INFO | Running OCRmyPDF on document.pdf (1447275 bytes)
INFO | OCRmyPDF completed successfully for document.pdf
INFO | PDF OCR extraction successful | filename=document.pdf | pages=5 | length=23012 | backend=ocrmypdf
```

### Error Logs
Errors fall back to standard PDF extraction:
```
WARNING | PDF OCR failed for document.pdf, falling back to standard extraction: [error details]
```

## Troubleshooting

### Common Issues

#### 1. Docker Not Available
**Error**: `[Errno 2] No such file or directory: 'docker'`

**Solution**: Rebuild archon-server with Docker CLI:
```bash
docker compose build archon-server
docker compose up -d archon-server
```

#### 2. OCRmyPDF Image Not Found
**Error**: `Unable to find image 'jbarlow83/ocrmypdf-alpine:latest'`

**Solution**: Pull the image:
```bash
docker pull jbarlow83/ocrmypdf-alpine
```

#### 3. Timeout Errors
**Error**: `OCR processing timed out after 5 minutes`

**Solution**: Increase timeout in `document_processing.py` or process smaller PDFs

#### 4. Empty Output
**Error**: `OCRmyPDF returned empty output`

**Solution**: Check PDF is valid and not corrupted. OCRmyPDF may fail on certain PDF formats.

## Testing

### Manual Test
```bash
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@test.pdf' \
  -F 'use_ocr=true' \
  -F 'knowledge_type=technical' \
  -F 'tags=["test","ocrmypdf"]'
```

### Verify Logs
```bash
docker compose logs -f archon-server | grep -i ocrmypdf
```

Look for:
- "Using OCRmyPDF to extract text from PDF"
- "OCRmyPDF completed successfully"
- "backend=ocrmypdf"

## Maintenance

### Updating OCRmyPDF
Pull the latest image:
```bash
docker pull jbarlow83/ocrmypdf-alpine:latest
```

No code changes required unless API changes.

### Monitoring
Check OCR performance via logs:
- Processing time per page
- Success/failure rates
- Text extraction quality

## Future Improvements

### Potential Enhancements
- Add `--clean` flag when implemented (removes halftone artifacts)
- Implement `--remove-background` when available
- Add progress callbacks for long-running OCR operations
- Cache OCR'd PDFs to avoid reprocessing
- Support custom Tesseract language models
- Parallel processing for multi-page PDFs

### Performance Tuning
- Adjust `--optimize` level based on use case
- Add DPI configuration for image quality
- Implement batch processing for multiple PDFs
- Add CPU core limits for resource management

## Related Files

### Core Implementation
- `python/src/server/utils/document_processing.py` - OCRmyPDF integration
- `python/pyproject.toml` - Python dependencies
- `python/Dockerfile.server` - Docker CLI installation

### API Layer
- `python/src/server/api_routes/knowledge_api.py` - Upload endpoint
- `python/src/server/services/storage/storage_services.py` - Document storage

### Configuration
- `docker-compose.yml` - Docker socket mount
- `.env` - Environment variables (none required for OCRmyPDF)

## References

- OCRmyPDF Documentation: https://ocrmypdf.readthedocs.io/
- Docker Image: https://hub.docker.com/r/jbarlow83/ocrmypdf/
- PyMuPDF Documentation: https://pymupdf.readthedocs.io/
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
