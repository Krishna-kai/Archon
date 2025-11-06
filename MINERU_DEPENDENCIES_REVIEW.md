# MinerU Dependencies Review

**Date**: 2025-01-06
**Purpose**: Review MinerU installation, dependencies, and requirements for the text extraction fix

---

## Installation Source

**Package**: `mineru[full]>=2.6.4`
**Installed Version**: `2.6.4`
**Source**: Official PyPI (`https://pypi.org/simple`)
**Type**: Standard PyPI package (NOT a fork)

### Declaration in pyproject.toml

```toml
# python/pyproject.toml:55
"mineru[full]>=2.6.4",  # MinerU for formula and table extraction
```

---

## Core MinerU Dependencies

MinerU automatically installs these required packages:

### PDF Processing (Critical for our fix)
- **pypdfium2** `4.30.0` ⭐ - **This is what we use for text extraction**
- **pypdf** - PDF manipulation
- **pdfminer-six** - PDF text extraction
- **pdftext** - Text extraction utilities

### Image Processing
- **pillow** `11.3.0` - Image manipulation (for extracted figures)
- **opencv-python** - Computer vision operations
- **scikit-image** - Image processing algorithms

### ML/AI Components
- **huggingface-hub** - Model downloading
- **modelscope** - Model management
- **mineru-vl-utils** `0.1.15` - Vision-language utilities
- **numpy** - Numerical operations

### Utilities
- **beautifulsoup4** - HTML parsing
- **fast-langdetect** - Language detection
- **httpx** - HTTP client
- **loguru** - Logging
- **magika** - File type detection
- **json-repair** - JSON fixing
- **click** - CLI framework
- **boto3** - AWS S3 (for cloud storage)
- **reportlab** - PDF generation
- **requests** - HTTP requests
- **tqdm** - Progress bars

---

## Our Integration Stack

### Text Extraction Fix Dependencies

The fix in `python/src/mineru_service/main.py` uses:

1. **pypdfium2** (from MinerU) ✅ Already installed
   ```python
   pdf_doc = all_pdf_docs[0]  # PdfDocument object
   page = pdf_doc[page_idx]
   textpage = page.get_textpage()
   page_text = textpage.get_text_bounded()  # PyPDFium2 API
   ```

2. **PIL/Pillow** (from MinerU) ✅ Already installed
   ```python
   from PIL import Image
   # For processing extracted images
   ```

3. **FastAPI** (from server dependencies) ✅ Already installed
   ```python
   from fastapi import FastAPI, File, UploadFile
   ```

4. **Pydantic** (from server dependencies) ✅ Already installed
   ```python
   from pydantic import BaseModel
   ```

### Service Architecture

```
MinerU Service (port 8055)
├── FastAPI server (uvicorn)
├── MinerU backend
│   ├── doc_analyze() → Returns (infer_results, all_pdf_docs, ...)
│   └── PdfDocument objects (pypdfium2)
└── Response models (Pydantic)
```

---

## No Additional Dependencies Needed

### For Text Extraction Fix ✅

All required libraries are already installed via:
- `mineru[full]>=2.6.4` → Brings pypdfium2, PIL, numpy
- FastAPI/Pydantic → Already in server dependencies

### What We're Using

**Before Fix** (Broken):
- Tried to read from `layout_dets['text']` ❌ (doesn't exist)

**After Fix** (Working):
- Using `pypdfium2.PdfDocument` API ✅ (already available)
- No new imports needed
- No additional packages required

---

## Dependency Groups

### Server Group (pyproject.toml:36-74)

Contains MinerU and all dependencies:
```toml
server = [
    "mineru[full]>=2.6.4",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "pypdf2>=3.0.1",      # Additional PDF tools
    "pdfplumber>=0.11.6",
    "pymupdf>=1.24.0",
    # ... other dependencies
]
```

### All Group (pyproject.toml:119-159)

For local development/testing:
- Includes all server dependencies
- Adds test dependencies
- Used with `uv sync --group all`

---

## Installation Commands

### Fresh Install
```bash
cd python
uv sync --group server  # Installs mineru[full] and dependencies
```

### Verify Installation
```bash
uv pip show mineru
uv pip show pypdfium2
uv pip list | grep -E "(mineru|pypdfium2|pillow)"
```

### Current State
```
mineru                 2.6.4     ✅ Installed
pypdfium2             4.30.0     ✅ Installed (via mineru)
pillow                11.3.0     ✅ Installed (via mineru)
fastapi               0.121.0    ✅ Installed (via server)
pydantic              2.11.10    ✅ Installed (via server)
```

---

## Architecture Notes

### Why MinerU[full]?

The `[full]` extra installs:
- All ML models for formula extraction (MFR)
- OCR components for table extraction
- Additional vision models
- GPU acceleration support (MPS on macOS)

### What We Actually Use

**For Current Fix**:
- ✅ `pypdfium2` - Text extraction from PDF
- ✅ `PIL/Pillow` - Image processing
- ⚠️ Formula/Table extraction - Not yet used (TODO)

**For Future Enhancements**:
- ⏳ MinerU's MFR (Mathematical Formula Recognition)
- ⏳ MinerU's table OCR
- ⏳ Layout analysis from `layout_dets`

---

## Platform-Specific Notes

### Apple Silicon (macOS)

MinerU supports MPS (Metal Performance Shaders) for GPU acceleration:
```python
device: str = Form("mps")  # Apple GPU
```

Configuration in pyproject.toml:
```toml
# PyTorch CPU-only index (lines 11-14)
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
```

**Note**: We use CPU-only PyTorch to reduce dependencies. MPS acceleration is available but optional.

---

## Summary

### ✅ Ready to Deploy

1. **All dependencies installed** via `mineru[full]>=2.6.4`
2. **No new packages needed** for text extraction fix
3. **pypdfium2 available** as transitive dependency from MinerU
4. **Fix uses existing APIs** - no breaking changes

### 📋 Installation Checklist

- [x] MinerU 2.6.4 installed from official PyPI
- [x] pypdfium2 4.30.0 available (transitive)
- [x] Pillow 11.3.0 available (transitive)
- [x] FastAPI server dependencies installed
- [x] Text extraction working with pypdfium2

### 🎯 No Action Required

The fix works with existing dependencies. No additional packages needed.
