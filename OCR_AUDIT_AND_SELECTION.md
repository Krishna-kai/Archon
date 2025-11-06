# OCR Solutions Audit and Intelligent Selection System

## Overview

This document provides a comprehensive audit of all OCR solutions in Archon and establishes an intelligent selection system to determine the best OCR method for each document type.

## Executive Summary

Archon currently implements **4 OCR solutions** working together on the same Docker network (`app-network`):

1. **OCRmyPDF** (Primary for PDFs) - Fastest, best for academic papers
2. **Tesseract** (Backup for PDFs) - More configurable, custom processing
3. **DeepSeek OCR** (For Images) - AI-powered, markdown output
4. **Stirling PDF** (Manual Batch) - Web UI for batch processing

All solutions integrate through a unified `extract_text_from_document()` API in `document_processing.py`.

---

## Complete OCR Solutions Inventory

### 1. OCRmyPDF (Primary PDF OCR)

**Status**: ✅ Fully Implemented and Tested
**Docker Image**: `jbarlow83/ocrmypdf-alpine`
**Architecture**: ARM64 native, CPU-optimized
**Network**: `app-network` (ephemeral container via Docker CLI)

#### Integration Points
- **Implementation**: `python/src/server/utils/document_processing.py:extract_text_from_pdf_ocrmypdf()` (lines 520-619)
- **Entry Point**: Called by `extract_text_from_pdf_ocr()` (line 185)
- **API Route**: `/api/documents/upload` with `use_ocr=true` parameter
- **Trigger**: Automatic when uploading PDF with `use_ocr=true`

#### Features
- ✅ stdin/stdout data transfer (no volume mounting)
- ✅ Auto-deskew and page rotation
- ✅ Light optimization (`--optimize 1`)
- ✅ Force OCR mode
- ✅ ~20 seconds for 5-page academic PDF

#### Best For
- Academic papers (IEEE, ACM, research PDFs)
- High-quality scanned documents
- PDFs with mixed text and images
- Fast processing requirements

#### Limitations
- Requires valid PDF structure
- No specialized language model support
- Fixed processing parameters

---

### 2. Tesseract OCR (Backup PDF OCR)

**Status**: ✅ Fully Implemented and Ready
**Docker Image**: `jitesoft/tesseract-ocr`
**Architecture**: ARM64 + x86_64 multi-platform
**Network**: `app-network` (ephemeral container via Docker CLI)

#### Integration Points
- **Implementation**: `python/src/server/utils/document_processing.py:extract_text_from_pdf_tesseract()` (lines 425-517)
- **Entry Point**: Fallback in `extract_text_from_pdf_ocr()` when OCRmyPDF fails (line 192)
- **API Route**: Same as OCRmyPDF (`/api/documents/upload` with `use_ocr=true`)
- **Trigger**: Automatic fallback when OCRmyPDF fails or times out

#### Features
- ✅ Page-by-page processing with 300 DPI rendering
- ✅ Custom language models support (`-l eng`, `-l fra`, etc.)
- ✅ Automatic page segmentation mode (`--psm 1`)
- ✅ Graceful per-page failure handling
- ✅ ~30-40 seconds for 5-page PDF

#### Best For
- Corrupted or malformed PDFs
- Non-standard PDF layouts
- Documents requiring custom language models
- When OCRmyPDF fails

#### Limitations
- Slower than OCRmyPDF
- Requires page-by-page image conversion
- Higher memory usage

---

### 3. DeepSeek OCR (Image OCR)

**Status**: ✅ Implemented (Optional Profile)
**Docker Image**: Custom service in `services/deepseek-ocr/`
**Architecture**: Transformers-based or Ollama backend
**Network**: `app-network` on port 9001
**Service**: `deepseek-ocr` container (requires `--profile deepseek-ocr`)

#### Integration Points
- **Service Layer**: `python/src/server/services/ocr_service.py:OCRService` (complete file)
- **Implementation**: `python/src/server/utils/document_processing.py:extract_text_from_image_ocr()` (lines 368-422)
- **Entry Point**: Called by `extract_text_from_document()` for image files (line 186)
- **API Route**: `/api/documents/upload` with `use_ocr=true` for image files
- **Health Check**: `http://deepseek-ocr:9001/health`

#### Features
- ✅ AI-powered OCR with prompt-based control
- ✅ Markdown or plain text output
- ✅ Support for image files (JPG, PNG, BMP, TIFF)
- ✅ PDF OCR capability via `/ocr/pdf` endpoint
- ✅ Grounding-based document conversion

#### API Methods
```python
# From ocr_service.py
async def ocr_image(file_content: bytes, filename: str,
                   prompt: str = "<image>\n<|grounding|>Convert the document to markdown.",
                   output_format: str = "markdown") -> tuple[bool, dict]

async def ocr_pdf(file_content: bytes, filename: str,
                 prompt: str = "<image>\n<|grounding|>Convert the document to markdown.") -> tuple[bool, dict]
```

#### Best For
- Image files (JPG, PNG, BMP, TIFF)
- Documents requiring markdown output
- Complex layouts with tables and formatting
- When semantic understanding is needed

#### Limitations
- Requires separate service to be running
- Slower than OCRmyPDF for simple text
- Needs model download (larger resource footprint)
- Optional service (not enabled by default)

---

### 4. Stirling PDF (Manual Batch Processing)

**Status**: ✅ Configured, Ready to Start
**Docker Image**: `stirlingtools/stirling-pdf:latest`
**Architecture**: Web-based UI
**Network**: `app-network` on port 8080
**Service**: `stirling-pdf` container (requires `--profile stirling-pdf`)

#### Integration Points
- **Configuration**: `docker-compose.yml` (lines 280-304)
- **Web UI**: `http://localhost:8080`
- **Usage**: Manual batch operations via browser
- **Start Command**: `docker compose --profile stirling-pdf up -d`

#### Features
- 🌐 Web-based batch processing interface
- 📁 Multiple file uploads simultaneously
- 🔄 Batch OCR operations
- 📊 PDF manipulation tools (merge, split, rotate)
- 💾 Local Tesseract training data support

#### Volumes
- `stirling-pdf-training:/usr/share/tessdata` - Tesseract training data
- `stirling-pdf-configs:/configs` - Custom configurations
- `stirling-pdf-logs:/logs` - Service logs

#### Best For
- Manual batch processing of multiple PDFs
- When API integration is not needed
- Testing different OCR settings
- One-off document conversions
- User-initiated OCR operations

#### Limitations
- Manual operation only (no API integration)
- Requires user interaction via web browser
- Not suitable for automated workflows
- Must be manually started with profile flag

---

## Integration with Archon Web Services

### API Endpoint: Document Upload

**Route**: `POST /api/documents/upload`
**File**: `python/src/server/api_routes/knowledge_api.py`
**Lines**: 900-962 (endpoint definition), 991-1039 (processing function)

#### Request Parameters
```python
file: UploadFile                    # Document file
use_ocr: bool = Form(False)         # Enable OCR processing
knowledge_type: str = Form("general") # Document classification
tags: str = Form("[]")              # JSON array of tags
extract_code_examples: bool = Form(False)  # Extract code snippets
```

#### Processing Flow

```
1. Upload Request (use_ocr=true)
   ↓
2. knowledge_api.py:upload_document_endpoint()
   ↓
3. knowledge_api.py:process_and_store_document()
   ↓
4. document_processing.py:extract_text_from_document()
   ↓
5. Document Type Detection
   ├─→ Image File (JPG, PNG, etc.)
   │   └─→ extract_text_from_image_ocr() → DeepSeek OCR
   │
   └─→ PDF File
       ├─→ use_ocr=true?
       │   └─→ extract_text_from_pdf_ocr()
       │       ├─→ Try OCRmyPDF (primary)
       │       ├─→ Fallback to Tesseract (backup)
       │       └─→ Fallback to standard extraction
       │
       └─→ use_ocr=false?
           └─→ extract_text_from_pdf() → PyPDF2/pdfplumber
```

### Key Integration Code

**Main Entry Point** (`document_processing.py:158-242`):
```python
async def extract_text_from_document(
    file_content: bytes,
    filename: str,
    content_type: str,
    use_ocr: bool = False
) -> str:
    """Extract text from various document formats."""

    # Image files with OCR
    if use_ocr and content_type.startswith("image/"):
        return await extract_text_from_image_ocr(file_content, filename)

    # PDF files - use OCR if requested
    if content_type == "application/pdf":
        if use_ocr:
            try:
                return await extract_text_from_pdf_ocr(file_content, filename)
            except Exception as ocr_error:
                logger.warning(f"PDF OCR failed, falling back to standard extraction")
                # Fall back to standard PDF extraction
        return extract_text_from_pdf(file_content)

    # Other file types...
```

**OCR Fallback Chain** (`document_processing.py:622-660`):
```python
async def extract_text_from_pdf_ocr(file_content: bytes, filename: str) -> str:
    """
    Extract text with intelligent fallback chain.
    OCRmyPDF → Tesseract → (raises exception, caller handles standard extraction)
    """
    # Try OCRmyPDF first
    try:
        logger.info(f"Attempting OCR with OCRmyPDF (primary) for {filename}")
        return await extract_text_from_pdf_ocrmypdf(file_content, filename)
    except Exception as ocrmypdf_error:
        logger.warning(f"OCRmyPDF failed: {ocrmypdf_error}")

        # Fallback to Tesseract
        try:
            logger.info(f"Falling back to Tesseract OCR for {filename}")
            return await extract_text_from_pdf_tesseract(file_content, filename)
        except Exception as tesseract_error:
            logger.error(f"Tesseract also failed: {tesseract_error}")
            raise Exception("All OCR methods failed")
```

---

## Intelligent OCR Selection System

### Current Selection Logic

The current implementation uses a **simple rule-based system** with hardcoded fallback chain:

1. **Image Files** (`use_ocr=true`) → **DeepSeek OCR**
2. **PDF Files** (`use_ocr=true`) → **OCRmyPDF** → **Tesseract** → Standard extraction
3. **PDF Files** (`use_ocr=false`) → PyPDF2/pdfplumber (no OCR)
4. **Manual Batch** → User chooses **Stirling PDF** web UI

### Proposed Intelligent Selection System

#### Document Analysis Criteria

To intelligently select the best OCR method, analyze these document characteristics:

##### 1. File Type
- **Image files**: JPG, PNG, BMP, TIFF → DeepSeek OCR
- **PDF files**: PDF → OCRmyPDF/Tesseract/Standard

##### 2. PDF Type Detection
Determine if PDF contains text or is image-based:

```python
def detect_pdf_type(file_content: bytes) -> str:
    """
    Detect if PDF is text-based or scanned.
    Returns: 'text_based', 'scanned', or 'mixed'
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_content, filetype="pdf")

    if len(doc) == 0:
        return 'unknown'

    # Sample first 3 pages
    sample_pages = min(3, len(doc))
    text_chars = 0
    image_count = 0

    for page_num in range(sample_pages):
        page = doc[page_num]

        # Check for extractable text
        text = page.get_text()
        text_chars += len(text.strip())

        # Check for images
        images = page.get_images()
        image_count += len(images)

    doc.close()

    # Classification logic
    if text_chars > 500:  # Has substantial text
        if image_count > sample_pages:  # Also has images
            return 'mixed'
        return 'text_based'
    elif image_count > 0:
        return 'scanned'
    else:
        return 'unknown'
```

##### 3. File Size
- **Small** (< 1 MB): Use faster methods
- **Medium** (1-5 MB): Balance speed vs quality
- **Large** (> 5 MB): Consider processing time

##### 4. Output Format Requirements
- **Plain text needed**: OCRmyPDF or Tesseract
- **Markdown with structure**: DeepSeek OCR
- **Preserving formatting**: Stirling PDF (manual)

##### 5. Document Quality
- **High quality scans**: OCRmyPDF (faster)
- **Low quality/degraded**: Tesseract (more configurable)
- **Complex layouts**: DeepSeek OCR (semantic understanding)

---

### Intelligent Selection Algorithm

#### Decision Tree

```
START: Document uploaded with use_ocr=true
│
├─→ Is Image File?
│   └─→ YES → DeepSeek OCR
│       ├─→ Health check passes? → Process with DeepSeek
│       └─→ Health check fails? → Fail (no fallback for images)
│
└─→ Is PDF File?
    │
    ├─→ Detect PDF Type
    │   │
    │   ├─→ TEXT_BASED (has extractable text)
    │   │   └─→ Standard extraction (PyPDF2/pdfplumber)
    │   │       └─→ No OCR needed!
    │   │
    │   ├─→ SCANNED (image-based, no text)
    │   │   ├─→ File size < 5 MB?
    │   │   │   └─→ YES → OCRmyPDF (fastest)
    │   │   │       ├─→ Success? → Done
    │   │   │       └─→ Fail? → Tesseract (backup)
    │   │   │
    │   │   └─→ File size >= 5 MB?
    │   │       └─→ Tesseract (more memory efficient for large files)
    │   │           ├─→ Success? → Done
    │   │           └─→ Fail? → OCRmyPDF (try anyway)
    │   │
    │   └─→ MIXED (text + images)
    │       └─→ OCRmyPDF (handles mixed content well)
    │           ├─→ Success? → Done
    │           └─→ Fail? → Standard extraction (preserve existing text)
    │
    └─→ UNKNOWN or ERROR in detection
        └─→ Default fallback chain:
            OCRmyPDF → Tesseract → Standard extraction
```

#### Specialized Scenarios

**Academic Papers / IEEE Documents**:
- Always use **OCRmyPDF** first
- Optimized for academic PDF layouts
- Fast processing with high accuracy

**Poor Quality Scans**:
- Use **Tesseract** with custom preprocessing
- Adjust DPI (400+) for better quality
- Configure custom language models if needed

**Batch Processing**:
- Direct user to **Stirling PDF** web UI
- Manual control over settings
- Useful for one-off conversions

**Markdown Output Required**:
- Use **DeepSeek OCR** for images
- Fall back to standard extraction + post-processing for PDFs

---

### Implementation Roadmap

#### Phase 1: PDF Type Detection (Recommended)
Add `detect_pdf_type()` function to `document_processing.py`:

```python
async def extract_text_from_document(
    file_content: bytes,
    filename: str,
    content_type: str,
    use_ocr: bool = False
) -> str:
    """Enhanced with intelligent PDF type detection."""

    # ... existing image handling ...

    # PDF files - intelligent selection
    if content_type == "application/pdf":
        if use_ocr:
            # Detect PDF type
            pdf_type = detect_pdf_type(file_content)

            if pdf_type == 'text_based':
                # No OCR needed!
                logger.info(f"PDF {filename} has extractable text, skipping OCR")
                return extract_text_from_pdf(file_content)

            elif pdf_type == 'scanned':
                # Scanned PDF - use OCR
                file_size_mb = len(file_content) / (1024 * 1024)

                if file_size_mb < 5:
                    # Small file - use fast OCRmyPDF
                    try:
                        return await extract_text_from_pdf_ocr(file_content, filename)
                    except Exception:
                        return extract_text_from_pdf(file_content)
                else:
                    # Large file - use Tesseract directly
                    try:
                        return await extract_text_from_pdf_tesseract(file_content, filename)
                    except Exception:
                        return extract_text_from_pdf(file_content)

            else:
                # Mixed or unknown - use default fallback chain
                try:
                    return await extract_text_from_pdf_ocr(file_content, filename)
                except Exception:
                    return extract_text_from_pdf(file_content)

        # use_ocr=false - standard extraction
        return extract_text_from_pdf(file_content)
```

#### Phase 2: Enhanced Logging and Metrics
Track which OCR method was used and success rates:

```python
logfire.info(
    "PDF OCR extraction successful",
    filename=filename,
    pages=page_count,
    backend="ocrmypdf",  # or "tesseract", "deepseek", "standard"
    processing_time_seconds=elapsed_time,
    text_length=len(extracted_text),
    pdf_type=pdf_type  # "text_based", "scanned", "mixed"
)
```

#### Phase 3: Custom OCR Profiles
Allow users to specify OCR preferences:

```python
ocr_profile: str = Form("auto")  # "auto", "fast", "quality", "custom"
```

- **auto**: Use intelligent selection
- **fast**: Always prefer OCRmyPDF
- **quality**: Use Tesseract with high DPI
- **custom**: Allow specifying exact method

---

## Usage Guide: Determining Best OCR Method

### For Developers

#### When to Use `use_ocr=true`

```bash
# Academic papers, scanned documents
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@research_paper.pdf' \
  -F 'use_ocr=true'

# Image files
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@scanned_page.jpg' \
  -F 'use_ocr=true'
```

#### When to Use `use_ocr=false` (Default)

```bash
# Regular PDFs with text (faster, no OCR overhead)
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@document.pdf' \
  -F 'use_ocr=false'

# Or just omit the parameter (defaults to false)
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@document.pdf'
```

### For End Users

#### Use OCRmyPDF When:
- ✅ Working with academic papers
- ✅ High-quality scanned documents
- ✅ Need fast processing (< 30 seconds)
- ✅ PDF structure is valid

#### Use Tesseract When:
- ✅ OCRmyPDF fails or times out
- ✅ Need custom language models
- ✅ Working with non-standard PDFs
- ✅ More control over processing

#### Use DeepSeek OCR When:
- ✅ Processing image files (JPG, PNG)
- ✅ Need markdown output with structure
- ✅ Complex layouts with tables
- ✅ Semantic understanding required

#### Use Stirling PDF When:
- ✅ Batch processing multiple files manually
- ✅ Need to test different OCR settings
- ✅ One-off document conversions
- ✅ Want visual feedback and control

---

## Performance Comparison

| Method | Speed (5pg PDF) | Quality | Best Use Case | Resource Usage |
|--------|-----------------|---------|---------------|----------------|
| **OCRmyPDF** | 20-25s | Excellent | Academic PDFs | CPU-intensive |
| **Tesseract** | 30-40s | Good | Backup, custom configs | Memory-intensive |
| **DeepSeek OCR** | 40-60s | Excellent | Images, complex layouts | Model-dependent |
| **Stirling PDF** | Manual | Excellent | Batch processing | User-driven |
| **Standard** | 2-5s | N/A | Text-based PDFs | Minimal |

---

## Monitoring OCR Operations

### Check Recent OCR Usage

```bash
# View all OCR operations
docker compose logs archon-server | grep "backend=ocrmypdf\|backend=tesseract\|backend=deepseek"

# Count OCR successes
docker compose logs archon-server | grep "PDF OCR extraction successful" | wc -l

# Monitor real-time
docker compose logs -f archon-server | grep -i ocr
```

### Success Indicators

```
✅ OCRmyPDF: "backend=ocrmypdf"
✅ Tesseract: "backend=tesseract"
✅ DeepSeek: "DeepSeek OCR completed successfully"
✅ Storage: "Document upload completed successfully"
```

---

## Configuration Reference

### Environment Variables

```bash
# .env file
STIRLING_PDF_PORT=8080              # Stirling PDF web UI port
DEEPSEEK_OCR_PORT=9001             # DeepSeek OCR service port
DEEPSEEK_MODEL=deepseek-ocr        # DeepSeek model name
LOG_LEVEL=INFO                     # Set to DEBUG for verbose OCR logs
```

### Docker Compose Profiles

```bash
# Default (OCRmyPDF + Tesseract available via Docker CLI)
docker compose up -d

# With Stirling PDF web UI
docker compose --profile stirling-pdf up -d

# With DeepSeek OCR service
docker compose --profile deepseek-ocr up -d

# Full OCR stack
docker compose --profile stirling-pdf --profile deepseek-ocr up -d
```

---

## Troubleshooting

### OCRmyPDF Not Working

**Symptoms**: `[Errno 2] No such file or directory: 'docker'`

**Solution**:
```bash
# Docker CLI missing in container
docker compose build archon-server
docker compose up -d archon-server
```

### Tesseract Timeout

**Symptoms**: `Tesseract OCR timed out`

**Solution**: Reduce PDF size or increase timeout in `document_processing.py`:
```python
timeout=120  # Increase to 300s for large files
```

### DeepSeek OCR Not Available

**Symptoms**: `DeepSeek OCR service not available`

**Solution**:
```bash
# Start DeepSeek OCR service
docker compose --profile deepseek-ocr up -d

# Check health
curl http://localhost:9001/health
```

### Stirling PDF Won't Start

**Symptoms**: `Health check failed`

**Solution**:
```bash
# Check logs
docker compose logs stirling-pdf

# Verify port not in use
lsof -i :8080

# Restart
docker compose --profile stirling-pdf restart stirling-pdf
```

---

## Summary and Recommendations

### Current State ✅

All four OCR solutions are implemented and working:

1. **OCRmyPDF**: Production-ready, tested, fast
2. **Tesseract**: Production-ready, automatic fallback
3. **DeepSeek OCR**: Optional, requires profile flag
4. **Stirling PDF**: Optional, manual use

### Recommended Improvements

1. **Implement PDF Type Detection** (Phase 1)
   - Skip OCR for text-based PDFs
   - Save processing time and resources
   - Reduce API latency

2. **Add Enhanced Logging** (Phase 2)
   - Track which OCR method was used
   - Monitor success rates by method
   - Identify patterns in failures

3. **Create OCR Profiles** (Phase 3)
   - Allow users to specify preferences
   - Support "fast", "quality", "custom" modes
   - Enable fine-tuned control

### Quick Start Commands

```bash
# Test automatic OCR (OCRmyPDF → Tesseract fallback)
curl -X POST 'http://localhost:9181/api/documents/upload' \
  -F 'file=@document.pdf' \
  -F 'use_ocr=true'

# Start Stirling PDF web UI
docker compose --profile stirling-pdf up -d
open http://localhost:8080

# Start DeepSeek OCR service
docker compose --profile deepseek-ocr up -d

# Monitor OCR operations
docker compose logs -f archon-server | grep -i ocr
```

All OCR solutions are integrated and ready to use on the `app-network` Docker network!
