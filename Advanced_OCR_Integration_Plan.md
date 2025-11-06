# Advanced OCR Integration Plan
## Formula & Table Extraction for Archon

**Date:** 2025-01-05
**Current Stack:** PyMuPDF, OCRmyPDF, Docling OCR, Stirling PDF
**Objective:** Integrate specialized OCR services for academic papers with formulas and tables

---

## Executive Summary

This plan outlines the integration of three specialized OCR services into Archon to handle advanced content extraction from academic and scientific documents:

1. **Pix2Text** - Mixed content (text + formulas + tables) - Primary solution for IEEE papers
2. **LaTeX-OCR (Texify)** - Mathematical formula extraction with LaTeX output
3. **Surya OCR** - Advanced table recognition and layout analysis

### Current Gap Analysis

**Existing Capabilities:**
- ✅ Text extraction from digital PDFs (PyMuPDF)
- ✅ OCR for scanned documents (OCRmyPDF)
- ✅ Basic table detection (Docling OCR reports 0 tables found in test)
- ✅ Markdown output with structure (Docling OCR)

**Missing Capabilities:**
- ❌ LaTeX formula extraction
- ❌ Mathematical equation recognition
- ❌ Advanced table structure parsing
- ❌ Mixed content handling (formulas embedded in text)
- ❌ Cell-level table data extraction

---

## Proposed Architecture

### Service Stack Overview

```
Archon OCR Stack (Enhanced)
├── General Purpose OCR
│   ├── PyMuPDF (Port: native) - Fast text extraction
│   ├── OCRmyPDF (Port: 9002) - Scanned documents
│   ├── Docling OCR (Port: 9000) - Document parsing
│   └── Stirling PDF (Port: 9003) - Batch processing UI
│
└── Advanced Content Extraction (NEW)
    ├── Pix2Text (Port: 9004) - Mixed content extraction
    ├── LaTeX-OCR (Port: 9005) - Formula specialization
    └── Surya OCR (Port: 9006) - Table recognition
```

### Port Assignments

| Service | Port | Profile | Purpose |
|---------|------|---------|---------|
| Docling OCR | 9000 | ocr | Document parsing |
| OCRmyPDF | 9002 | ocr | Scanned docs |
| Stirling PDF | 9003 | ocr | Batch UI |
| **Pix2Text** | 9004 | advanced-ocr | **Formulas + Tables** |
| **LaTeX-OCR** | 9005 | advanced-ocr | **Math formulas** |
| **Surya OCR** | 9006 | advanced-ocr | **Table extraction** |

---

## Phase 1: Service Evaluation & Selection

### 1.1 Pix2Text Analysis

**Strengths:**
- Free Mathpix alternative
- 90%+ accuracy on LaTeX formulas
- Structured table detection
- Docker support with official image
- Handles mixed content (text + formulas + tables)
- Returns markdown with embedded LaTeX

**Technical Specifications:**
```yaml
Image: breezedeus/pix2text:latest
Size: ~2-3GB
Memory: 2-4GB RAM recommended
API: REST with multipart/form-data
Output Formats: markdown, JSON with structured data
```

**Use Cases:**
- IEEE research papers (your histopathology paper)
- Academic papers with mathematical content
- Scientific documents with tables and equations
- Mixed content extraction

**Implementation Complexity:** ⭐⭐⭐ (Medium)

---

### 1.2 LaTeX-OCR (Texify) Analysis

**Strengths:**
- Specialized for mathematical formulas
- High accuracy on complex equations
- Official Docker image available
- Lightweight compared to Pix2Text
- Direct LaTeX output

**Technical Specifications:**
```yaml
Image: lukasblecher/pix2tex:api
Size: ~1-2GB
Memory: 1-2GB RAM
API: REST with image input
Output: LaTeX code strings
```

**Use Cases:**
- Documents with heavy mathematical content
- Formula-only extraction
- When Pix2Text formulas need verification
- Supplementary to main OCR

**Implementation Complexity:** ⭐⭐ (Low-Medium)

---

### 1.3 Surya OCR Analysis

**Strengths:**
- State-of-the-art table recognition
- Layout analysis capabilities
- Cell-level extraction
- Bounding box detection
- Python library (not Docker-native)

**Technical Specifications:**
```yaml
Type: Python library (surya-ocr)
Size: ~500MB-1GB models
Memory: 2-3GB RAM
API: Custom Python integration
Output: Structured table data with cells
```

**Use Cases:**
- Complex table structures
- Multi-column tables
- Tables with merged cells
- Academic paper tables with numbers

**Implementation Complexity:** ⭐⭐⭐⭐ (High - requires custom containerization)

---

## Phase 2: Implementation Strategy

### 2.1 Recommended Approach: Tiered Integration

**Tier 1 Priority: Pix2Text** (Immediate Value)
- Handles 80% of use cases
- Mixed content extraction
- Single service for formulas + tables
- Established Docker image

**Tier 2 Priority: LaTeX-OCR** (Formula Enhancement)
- Specialized formula extraction
- Complements Pix2Text
- Quick to deploy
- Validation/fallback for Pix2Text formulas

**Tier 3 Priority: Surya OCR** (Advanced Tables)
- Complex table structures
- More development required
- Custom containerization
- Evaluate after Tier 1-2 results

---

## Phase 3: Docker Integration Plan

### 3.1 Docker Compose Configuration

Add to `/Users/krishna/Projects/archon/docker-compose.yml`:

```yaml
# Advanced OCR Services
services:
  # Pix2Text - Mixed Content (Formulas + Tables)
  pix2text-ocr:
    profiles:
      - advanced-ocr
    image: breezedeus/pix2text:latest
    container_name: pix2text-ocr
    restart: unless-stopped
    ports:
      - "${PIX2TEXT_PORT:-9004}:8503"
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - app-network
    volumes:
      - pix2text-models:/root/.pix2text  # Model cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8503/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s  # Longer startup for model loading

  # LaTeX-OCR - Formula Specialization
  latex-ocr:
    profiles:
      - advanced-ocr
    image: lukasblecher/pix2tex:api
    container_name: latex-ocr
    restart: unless-stopped
    ports:
      - "${LATEX_OCR_PORT:-9005}:8502"
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - app-network
    volumes:
      - latex-ocr-models:/app/models  # Model cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8502/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Surya OCR - Advanced Table Recognition (Custom)
  surya-ocr:
    profiles:
      - advanced-ocr
    build:
      context: ./services/surya
      dockerfile: Dockerfile
    container_name: surya-ocr
    restart: unless-stopped
    ports:
      - "${SURYA_OCR_PORT:-9006}:9006"
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - app-network
    volumes:
      - surya-models:/app/models  # Model cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9006/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s

volumes:
  pix2text-models:
  latex-ocr-models:
  surya-models:
```

### 3.2 Environment Variables

Add to `.env`:

```bash
# Advanced OCR Ports
PIX2TEXT_PORT=9004
LATEX_OCR_PORT=9005
SURYA_OCR_PORT=9006
```

---

## Phase 4: Service Implementation

### 4.1 Pix2Text Service Wrapper

Create `/Users/krishna/Projects/archon/python/src/server/services/pix2text_service.py`:

```python
"""
Pix2Text OCR Service Integration
Handles mixed content extraction (text + formulas + tables)
"""
import httpx
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

PIX2TEXT_URL = "http://pix2text-ocr:8503"

async def extract_mixed_content(
    file_content: bytes,
    filename: str,
    output_format: str = "markdown"
) -> Dict[str, Any]:
    """
    Extract text, formulas, and tables using Pix2Text

    Args:
        file_content: PDF file bytes
        filename: Original filename
        output_format: "markdown" or "json"

    Returns:
        {
            "success": bool,
            "text": str,
            "formulas": List[Dict],  # LaTeX formulas with positions
            "tables": List[Dict],    # Structured table data
            "markdown": str,         # Complete markdown output
            "metadata": Dict
        }
    """
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"file": (filename, file_content, "application/pdf")}
            data = {
                "return_format": output_format,
                "extract_tables": "true",
                "formula_detection": "true"
            }

            response = await client.post(
                f"{PIX2TEXT_URL}/predict",
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()

            return {
                "success": True,
                "text": result.get("text", ""),
                "formulas": result.get("formulas", []),
                "tables": result.get("tables", []),
                "markdown": result.get("markdown", ""),
                "metadata": {
                    "service": "pix2text",
                    "formula_count": len(result.get("formulas", [])),
                    "table_count": len(result.get("tables", [])),
                    "output_format": output_format
                }
            }

    except Exception as e:
        logger.error(f"Pix2Text extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "formulas": [],
            "tables": [],
            "markdown": ""
        }
```

### 4.2 LaTeX-OCR Service Wrapper

Create `/Users/krishna/Projects/archon/python/src/server/services/latex_ocr_service.py`:

```python
"""
LaTeX-OCR Service Integration
Specialized mathematical formula extraction
"""
import httpx
import pymupdf
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

LATEX_OCR_URL = "http://latex-ocr:8502"

async def extract_formulas(
    file_content: bytes,
    filename: str,
    dpi: int = 300
) -> Dict[str, Any]:
    """
    Extract LaTeX formulas from PDF

    Args:
        file_content: PDF file bytes
        filename: Original filename
        dpi: Resolution for image conversion

    Returns:
        {
            "success": bool,
            "formulas": List[Dict],  # Page-by-page formulas
            "formula_count": int,
            "text": str             # Regular text content
        }
    """
    try:
        doc = pymupdf.open(stream=file_content, filetype="pdf")
        all_formulas = []
        all_text = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Convert page to high-res image
                pix = page.get_pixmap(dpi=dpi)
                img_data = pix.tobytes("png")

                # Send to LaTeX-OCR
                files = {"file": ("page.png", img_data, "image/png")}
                response = await client.post(
                    f"{LATEX_OCR_URL}/predict/",
                    files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    latex_code = result.get("prediction", "")

                    if latex_code and len(latex_code) > 5:
                        all_formulas.append({
                            "page": page_num + 1,
                            "latex": latex_code,
                            "confidence": result.get("confidence", 0.0)
                        })

                # Extract regular text
                all_text.append(page.get_text())

        doc.close()

        return {
            "success": True,
            "formulas": all_formulas,
            "formula_count": len(all_formulas),
            "text": "\n\n".join(all_text),
            "metadata": {
                "service": "latex-ocr",
                "dpi": dpi,
                "pages_processed": len(doc)
            }
        }

    except Exception as e:
        logger.error(f"LaTeX-OCR extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "formulas": [],
            "formula_count": 0
        }
```

### 4.3 Surya OCR Service Wrapper

Create `/Users/krishna/Projects/archon/services/surya/main.py`:

```python
"""
Surya OCR FastAPI Service
Advanced table recognition with layout analysis
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import io
from PIL import Image
import pymupdf

# Import Surya components
from surya.ocr import run_ocr
from surya.model.detection.model import load_model, load_processor
from surya.table import load_table_model, batch_table_recognition

app = FastAPI(
    title="Surya OCR Service",
    description="Advanced table recognition for Archon"
)

# Load models at startup
det_processor = None
det_model = None
table_model = None

@app.on_event("startup")
async def startup_event():
    global det_processor, det_model, table_model
    print("Loading Surya models...")
    det_processor = load_processor()
    det_model = load_model()
    table_model = load_table_model()
    print("Models loaded successfully")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "surya-ocr",
        "models_loaded": all([det_processor, det_model, table_model])
    }

class TableExtractionResponse(BaseModel):
    success: bool
    tables: List[Dict[str, Any]]
    table_count: int
    error: Optional[str] = None

@app.post("/extract/tables", response_model=TableExtractionResponse)
async def extract_tables(
    file: UploadFile = File(...),
    dpi: int = 300
):
    """Extract tables from PDF using Surya OCR"""
    try:
        content = await file.read()
        doc = pymupdf.open(stream=content, filetype="pdf")
        all_tables = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Convert to PIL Image
            pix = page.get_pixmap(dpi=dpi)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            # Run table detection
            table_results = batch_table_recognition(
                [image],
                table_model,
                det_processor,
                det_model
            )

            for table_result in table_results:
                if table_result.cells:
                    # Convert to structured format
                    table_data = []
                    for row in table_result.rows:
                        row_data = [cell.text for cell in row.cells]
                        table_data.append(row_data)

                    all_tables.append({
                        "page": page_num + 1,
                        "table_data": table_data,
                        "cell_count": len(table_result.cells),
                        "bbox": table_result.bbox,
                        "rows": len(table_data),
                        "columns": len(table_data[0]) if table_data else 0
                    })

        doc.close()

        return TableExtractionResponse(
            success=True,
            tables=all_tables,
            table_count=len(all_tables)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9006)
```

Create `/Users/krishna/Projects/archon/services/surya/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Surya OCR and dependencies
RUN pip install --no-cache-dir \
    surya-ocr \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    pymupdf \
    Pillow

# Copy service code
COPY main.py /app/main.py

# Expose port
EXPOSE 9006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:9006/health || exit 1

# Run service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9006"]
```

---

## Phase 5: API Integration

### 5.1 New API Endpoints

Add to `/Users/krishna/Projects/archon/python/src/server/api_routes/advanced_ocr_api.py`:

```python
"""
Advanced OCR API Endpoints
Handles formula and table extraction
"""
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

from ..services import pix2text_service, latex_ocr_service

router = APIRouter(prefix="/api/advanced-ocr", tags=["advanced-ocr"])

@router.post("/extract/mixed")
async def extract_mixed_content(
    file: UploadFile = File(...),
    output_format: str = Form("markdown")
):
    """
    Extract text, formulas, and tables using Pix2Text
    Best for: IEEE papers, academic documents with mixed content
    """
    content = await file.read()
    result = await pix2text_service.extract_mixed_content(
        content,
        file.filename,
        output_format
    )
    return JSONResponse(content=result)

@router.post("/extract/formulas")
async def extract_formulas(
    file: UploadFile = File(...),
    dpi: int = Form(300)
):
    """
    Extract LaTeX formulas using specialized LaTeX-OCR
    Best for: Mathematical papers, equation-heavy documents
    """
    content = await file.read()
    result = await latex_ocr_service.extract_formulas(
        content,
        file.filename,
        dpi
    )
    return JSONResponse(content=result)

@router.post("/extract/tables")
async def extract_tables(
    file: UploadFile = File(...)
):
    """
    Extract tables using Surya OCR
    Best for: Complex tables, multi-column data
    """
    import httpx

    async with httpx.AsyncClient(timeout=300.0) as client:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await client.post(
            "http://surya-ocr:9006/extract/tables",
            files=files
        )
        response.raise_for_status()
        return response.json()
```

---

## Phase 6: Testing Strategy

### 6.1 Test Documents

Create test suite with various document types:

1. **Formula-heavy document** - Your histopathology paper (has some equations)
2. **Table-heavy document** - Research paper with data tables
3. **Mixed content document** - IEEE paper with formulas and tables
4. **Comparison document** - Same doc through all services

### 6.2 Comparison Script

Update `/Users/krishna/Projects/archon/python/scripts/compare_advanced_ocr.py`:

```python
"""
Advanced OCR Service Comparison
Tests Pix2Text, LaTeX-OCR, and Surya against existing services
"""
import asyncio
import httpx
from pathlib import Path
import time

async def test_pix2text(pdf_path: str):
    """Test Pix2Text mixed content extraction"""
    print("Testing Pix2Text...")
    start = time.time()

    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (Path(pdf_path).name, f.read(), "application/pdf")}

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "http://localhost:9004/predict",
                files=files,
                data={
                    "return_format": "markdown",
                    "extract_tables": "true",
                    "formula_detection": "true"
                }
            )
            result = response.json()

        elapsed = time.time() - start

        return {
            "service": "Pix2Text",
            "success": True,
            "time": elapsed,
            "formulas": len(result.get("formulas", [])),
            "tables": len(result.get("tables", [])),
            "text_length": len(result.get("text", "")),
            "markdown_length": len(result.get("markdown", ""))
        }

    except Exception as e:
        return {
            "service": "Pix2Text",
            "success": False,
            "error": str(e),
            "time": time.time() - start
        }

async def test_latex_ocr(pdf_path: str):
    """Test LaTeX-OCR formula extraction"""
    print("Testing LaTeX-OCR...")
    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(pdf_path, "rb") as f:
                files = {"file": (Path(pdf_path).name, f.read(), "application/pdf")}

            response = await client.post(
                "http://localhost:8181/api/advanced-ocr/extract/formulas",
                files=files
            )
            result = response.json()

        elapsed = time.time() - start

        return {
            "service": "LaTeX-OCR",
            "success": result.get("success", False),
            "time": elapsed,
            "formula_count": result.get("formula_count", 0),
            "formulas": result.get("formulas", [])
        }

    except Exception as e:
        return {
            "service": "LaTeX-OCR",
            "success": False,
            "error": str(e),
            "time": time.time() - start
        }

async def test_surya_ocr(pdf_path: str):
    """Test Surya table extraction"""
    print("Testing Surya OCR...")
    start = time.time()

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(pdf_path, "rb") as f:
                files = {"file": (Path(pdf_path).name, f.read(), "application/pdf")}

            response = await client.post(
                "http://localhost:9006/extract/tables",
                files=files
            )
            result = response.json()

        elapsed = time.time() - start

        return {
            "service": "Surya OCR",
            "success": result.get("success", False),
            "time": elapsed,
            "table_count": result.get("table_count", 0),
            "tables": result.get("tables", [])
        }

    except Exception as e:
        return {
            "service": "Surya OCR",
            "success": False,
            "error": str(e),
            "time": time.time() - start
        }

async def main():
    pdf_path = "/Users/krishna/Downloads/Krishna-Mahendra Experiement/Histopathology Project/Research Papers/Copy of Cell Nucleus Segmentation in Color Histopathological Imagery Using Convolutional Networks.pdf"

    results = await asyncio.gather(
        test_pix2text(pdf_path),
        test_latex_ocr(pdf_path),
        test_surya_ocr(pdf_path)
    )

    print("\n" + "="*80)
    print("ADVANCED OCR COMPARISON RESULTS")
    print("="*80)

    for result in results:
        print(f"\n{result['service']}:")
        print(f"  Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
        print(f"  Time: {result['time']:.2f}s")

        if result['success']:
            if 'formulas' in result:
                print(f"  Formulas: {result.get('formula_count', result.get('formulas', 0))}")
            if 'tables' in result:
                print(f"  Tables: {result.get('table_count', result.get('tables', 0))}")
        else:
            print(f"  Error: {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 7: Service Selection Matrix

### 7.1 Decision Tree

```
Document Type Assessment
│
├─ Contains Mathematical Formulas?
│  ├─ YES → Use Pix2Text (primary) + LaTeX-OCR (validation)
│  └─ NO → Continue
│
├─ Contains Complex Tables?
│  ├─ YES → Use Pix2Text (primary) + Surya (if tables fail)
│  └─ NO → Use existing OCR stack
│
└─ Standard Text Document → PyMuPDF or OCRmyPDF
```

### 7.2 Service Recommendations

| Document Type | Primary Service | Fallback | Notes |
|--------------|-----------------|----------|-------|
| IEEE Papers | Pix2Text | LaTeX-OCR + Surya | Mixed content |
| Math-heavy | LaTeX-OCR | Pix2Text | Formula focus |
| Table-heavy | Pix2Text | Surya | Structure priority |
| Standard Text | PyMuPDF | OCRmyPDF | Speed priority |
| Scanned Docs | OCRmyPDF | Docling | OCR required |

---

## Phase 8: Resource Requirements

### 8.1 Disk Space

| Service | Image Size | Model Cache | Total |
|---------|-----------|-------------|-------|
| Pix2Text | 2-3GB | 1-2GB | ~5GB |
| LaTeX-OCR | 1-2GB | 500MB | ~2.5GB |
| Surya | 1GB | 500MB-1GB | ~2GB |
| **Total New** | | | **~9.5GB** |

### 8.2 Memory Requirements

| Service | Idle | Processing | Peak |
|---------|------|------------|------|
| Pix2Text | 500MB | 2-4GB | 4GB |
| LaTeX-OCR | 200MB | 1-2GB | 2GB |
| Surya | 300MB | 2-3GB | 3GB |
| **Total New** | 1GB | 5-9GB | 9GB |

**Recommendation:** Allocate 12-16GB RAM for full advanced OCR stack

### 8.3 Processing Performance Estimates

Based on test document (5-page IEEE paper):

| Service | Est. Time | Formula Detection | Table Detection |
|---------|-----------|-------------------|-----------------|
| Pix2Text | 15-30s | ✅ Excellent | ✅ Good |
| LaTeX-OCR | 10-20s | ✅ Excellent | ❌ N/A |
| Surya | 20-40s | ❌ N/A | ✅ Excellent |
| Combined | 45-90s | ✅✅ Best | ✅✅ Best |

---

## Phase 9: Implementation Timeline

### Sprint 1: Foundation (Week 1)
- ✅ Day 1-2: Pix2Text Docker setup and testing
- ✅ Day 3-4: LaTeX-OCR Docker setup and testing
- ✅ Day 5: API endpoint development
- ✅ Day 6-7: Basic integration testing

### Sprint 2: Advanced Features (Week 2)
- ✅ Day 1-3: Surya OCR custom container development
- ✅ Day 4-5: Service wrapper implementation
- ✅ Day 6-7: Comprehensive testing

### Sprint 3: Optimization (Week 3)
- ✅ Day 1-2: Performance tuning
- ✅ Day 3-4: Error handling and fallbacks
- ✅ Day 5: Documentation
- ✅ Day 6-7: Client demo preparation

---

## Phase 10: Success Metrics

### 10.1 Performance KPIs

| Metric | Target | Critical |
|--------|--------|----------|
| Formula Detection Rate | >85% | >70% |
| Table Extraction Accuracy | >90% | >80% |
| Processing Time (5-page doc) | <60s | <120s |
| Service Uptime | >99% | >95% |

### 10.2 Quality Metrics

- LaTeX formula accuracy: Compare against manual extraction
- Table structure preservation: Cell alignment, merged cells
- Mixed content handling: Text flow around formulas

---

## Phase 11: Risk Assessment

### 11.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Large model download times | Medium | High | Pre-download during build |
| Memory constraints | High | Medium | Implement request queuing |
| Docker image compatibility | Medium | Low | Test on Mac M4 ARM64 |
| API changes in services | Low | Low | Pin specific versions |

### 11.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Increased resource usage | Medium | High | Profile-based activation |
| Slower processing | Medium | Medium | Async processing with queues |
| Model updates breaking | Low | Medium | Version pinning in Docker |

---

## Phase 12: Cost-Benefit Analysis

### 12.1 Implementation Costs

- Development time: 3 weeks (1 developer)
- Infrastructure: 10GB additional storage, 8GB RAM
- Testing: 1 week
- Documentation: 2-3 days

**Total Effort:** ~25-30 developer days

### 12.2 Benefits

**Quantitative:**
- Formula extraction: 0% → 85%+ (new capability)
- Table accuracy: ~60% → 90%+ (Docling detected 0 tables)
- Academic paper support: Complete solution

**Qualitative:**
- Competitive differentiation
- Academic/research market entry
- Premium service tier potential

---

## Phase 13: Rollout Strategy

### 13.1 Deployment Approach

**Option A: Gradual Rollout (Recommended)**
1. Week 1: Deploy Pix2Text to staging
2. Week 2: Add LaTeX-OCR after Pix2Text validation
3. Week 3: Add Surya if needed based on results
4. Week 4: Production deployment with monitoring

**Option B: Full Stack Deployment**
- Deploy all three services simultaneously
- Higher risk, faster time to market
- Requires more testing resources

### 13.2 Profile Strategy

```bash
# Start basic OCR only
docker compose --profile ocr up -d

# Add advanced OCR when needed
docker compose --profile ocr --profile advanced-ocr up -d

# Or combine all in one profile
docker compose --profile full-ocr up -d
```

---

## Phase 14: Monitoring & Observability

### 14.1 Metrics to Track

```python
# Service health metrics
- Request count per service
- Average processing time
- Error rate
- Formula detection success rate
- Table extraction accuracy

# Resource metrics
- Memory usage per service
- CPU utilization
- Disk I/O
- Model loading time
```

### 14.2 Logging Strategy

```python
# Structured logging
{
    "service": "pix2text",
    "document_id": "uuid",
    "processing_time": 23.5,
    "formulas_found": 12,
    "tables_found": 3,
    "success": true,
    "error": null
}
```

---

## Phase 15: Next Steps

### Immediate Actions Required

1. **Stakeholder Approval**
   - Review implementation plan
   - Approve resource allocation
   - Confirm priority (Tier 1, 2, or 3)

2. **Environment Preparation**
   - Verify Docker resources available
   - Ensure network connectivity for image pulls
   - Allocate storage for model caches

3. **Development Kickoff**
   - Create feature branch
   - Set up development environment
   - Begin Tier 1 (Pix2Text) implementation

### Questions for Decision

1. **Priority:** Deploy all three services or start with Pix2Text only?
2. **Timeline:** 3-week full implementation or phased approach?
3. **Resources:** Allocate dedicated development time or part-time?
4. **Testing:** Use your histopathology paper as primary test or need more samples?

---

## Appendix A: Service Comparison Matrix

| Feature | Pix2Text | LaTeX-OCR | Surya OCR | Docling | Current Gap |
|---------|----------|-----------|-----------|---------|-------------|
| Text Extraction | ✅ | ✅ | ✅ | ✅ | None |
| Formula Detection | ✅✅ | ✅✅ | ❌ | ❌ | **HIGH** |
| LaTeX Output | ✅ | ✅✅ | ❌ | ❌ | **HIGH** |
| Table Recognition | ✅ | ❌ | ✅✅ | ⚠️ | **MEDIUM** |
| Mixed Content | ✅✅ | ❌ | ❌ | ✅ | MEDIUM |
| Docker Support | ✅ | ✅ | Custom | ✅ | None |
| Processing Speed | Medium | Fast | Slow | Medium | None |
| Memory Usage | High | Low | High | High | None |

---

## Appendix B: Example API Responses

### Pix2Text Response

```json
{
  "success": true,
  "text": "Cell Nucleus Segmentation in Color...",
  "formulas": [
    {
      "page": 2,
      "latex": "f_k(X) = s_k(W_k X + b_k)",
      "bbox": [100, 200, 300, 250],
      "confidence": 0.92
    }
  ],
  "tables": [
    {
      "page": 4,
      "headers": ["Method", "Error", "Sensitivity"],
      "rows": [
        ["FLDA", "0.0663", "0.9267"],
        ["SVM", "0.0422", "0.9526"]
      ],
      "bbox": [50, 100, 500, 400]
    }
  ],
  "markdown": "# Cell Nucleus Segmentation\n\n$$f_k(X) = s_k(W_k X + b_k)$$\n\n| Method | Error | Sensitivity |\n|--------|-------|-------------|\n| FLDA | 0.0663 | 0.9267 |",
  "metadata": {
    "formula_count": 12,
    "table_count": 3,
    "processing_time": 23.5
  }
}
```

---

## Conclusion

This plan provides a comprehensive roadmap for integrating advanced OCR capabilities into Archon. The phased approach minimizes risk while delivering immediate value through Pix2Text, with optional enhancements via LaTeX-OCR and Surya.

**Recommended Next Step:** Approve Tier 1 (Pix2Text) implementation to validate the approach with your histopathology test document.

---

**Document Version:** 1.0
**Last Updated:** 2025-01-05
**Author:** Archon Development Team
**Status:** Awaiting Approval
