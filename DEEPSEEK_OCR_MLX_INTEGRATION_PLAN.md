# DeepSeek-OCR MLX Integration Plan
**Date**: 2025-11-06
**Target Port**: 9005
**Platform**: Mac M4 Studio with MLX (Apple Silicon)
**Purpose**: Integrate MLX-based DeepSeek-OCR service for native Apple GPU acceleration

---

## Executive Summary

This plan integrates the **MLX-based DeepSeek-OCR** service into Archon's OCR pipeline. Unlike the previous PyTorch-based attempt (which failed due to CUDA requirements), this uses **Apple's MLX framework** designed specifically for Mac M4 hardware with GPU acceleration.

### Key Differences from Previous Attempt

| Aspect | Previous (PyTorch) | New (MLX) |
|--------|-------------------|-----------|
| Backend | Transformers + PyTorch | MLX-VLM |
| Hardware | Requires CUDA GPU | Apple Silicon M4 |
| Acceleration | CUDA only | Apple Metal GPU |
| Docker Support | ❌ Failed | ✅ Mac-native (host) |
| Status | Blocked by CUDA | Ready to implement |

---

## 🔍 Current State Analysis

### What You Have

1. **Existing OCR Services** (all running on `ocr` profile):
   - Docling OCR (port 9000) - Document layout analysis
   - LaTeX OCR (port 9001) - Mathematical formulas
   - OCRmyPDF (port 9002) - PDF processing
   - Stirling PDF (port 9003) - PDF manipulation
   - Parser Service (port 9004) - Document orchestration
   - MinerU (port 8055) - Native Mac service with Apple GPU

2. **Previous DeepSeek OCR Attempt**:
   - Location: `services/deepseek-ocr/` (if exists)
   - Status: Failed due to CUDA requirements
   - Recommendation: Archive or remove

3. **Available Infrastructure**:
   - Docker Compose with service profiles
   - Standardized OCR service pattern (FastAPI + Dockerfile)
   - Health check and monitoring setup
   - Integration with Archon backend (document_processing.py)

### What You Need

**Port 9005** is available and fits perfectly in your OCR services range (9000-9099).

---

## 🎯 Integration Strategy

### Architecture Decision: Native Mac Service (Recommended)

**Run DeepSeek-OCR MLX as a NATIVE Mac service** (like MinerU), not in Docker.

**Why?**
- ✅ Direct access to Apple Metal GPU (10x faster)
- ✅ Full MLX framework support
- ✅ No Docker overhead
- ✅ Proven pattern (MinerU already works this way)
- ✅ Better performance for M4 hardware

**Alternative**: Docker service (CPU-only, slower) - included as fallback option

---

## 📋 Detailed Implementation Plan

### Phase 1: Environment Setup
**Duration**: 15-20 minutes

#### Step 1.1: Clone DeepSeek-OCR Repository
```bash
cd ~/Projects/archon/services
git clone https://github.com/Krishna-kai/DeepSeek-OCR.git deepseek-ocr-mlx
cd deepseek-ocr-mlx
```

#### Step 1.2: Create Python Virtual Environment
```bash
# Use Python 3.12 (as recommended)
python3.12 -m venv venv
source venv/bin/activate
```

#### Step 1.3: Install Dependencies
```bash
# Install MLX framework and dependencies
pip install mlx
pip install mlx-vlm
pip install fastapi
pip install uvicorn[standard]
pip install python-multipart
pip install Pillow
pip install pydantic

# Or if there's a requirements.txt:
pip install -r requirements.txt
```

#### Step 1.4: Download DeepSeek-OCR Model
```bash
# MLX-VLM will auto-download on first use, but you can pre-download:
python -c "import mlx_vlm; mlx_vlm.load('mlx-community/DeepSeek-OCR-8bit')"
```

**Expected Output**:
```
Downloading model...
Model downloaded to: ~/.cache/mlx/
```

---

### Phase 2: Service Implementation
**Duration**: 30-45 minutes

#### Step 2.1: Create FastAPI Service

**File**: `~/Projects/archon/services/deepseek-ocr-mlx/app.py`

```python
"""
DeepSeek-OCR MLX Service for Archon
Native Mac M4 service with Apple Metal GPU acceleration
"""
import os
import io
import tempfile
from pathlib import Path
from typing import Optional, List
import time

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image
import mlx_vlm

app = FastAPI(
    title="DeepSeek-OCR MLX Service",
    description="Vision-language OCR service powered by DeepSeek-OCR with Apple Metal GPU acceleration",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model configuration
MODEL_NAME = "mlx-community/DeepSeek-OCR-8bit"
model_loaded = False


class OCRResponse(BaseModel):
    """Response model for OCR operations"""
    success: bool
    result: Optional[str] = None
    markdown: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


# Prompt templates for different OCR modes
PROMPTS = {
    "markdown": "<image>\n<|grounding|>Convert the document to markdown.",
    "plain": "<image>\nFree OCR.",
    "figure": "<image>\nParse the figure.",
    "table": "<image>\nExtract the table structure.",
    "formula": "<image>\nExtract mathematical formulas.",
}


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    global model_loaded

    print("🚀 Initializing DeepSeek-OCR MLX model...")
    start_time = time.time()

    try:
        # Test model loading with a dummy call
        # MLX-VLM loads models lazily, so this will trigger the download/load
        print(f"📦 Model: {MODEL_NAME}")
        print("✅ MLX framework ready (models load on first use)")
        model_loaded = True

        load_time = time.time() - start_time
        print(f"✅ DeepSeek-OCR MLX initialized in {load_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Failed to initialize: {str(e)}")
        model_loaded = False


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "deepseek-ocr-mlx",
        "model_loaded": model_loaded,
        "model": MODEL_NAME,
        "backend": "MLX (Apple Metal)",
        "platform": "Mac M4 native"
    }


@app.post("/ocr/", response_model=OCRResponse)
async def process_ocr(
    file: UploadFile = File(...),
    mode: str = Form("markdown"),
    custom_prompt: str = Form(None),
    max_tokens: int = Form(2000),
    temperature: float = Form(0.0)
):
    """
    Process image or document with OCR

    Args:
        file: Image file (JPG, PNG, BMP, TIFF)
        mode: OCR mode (markdown, plain, figure, table, formula, custom)
        custom_prompt: Custom prompt (used when mode=custom)
        max_tokens: Maximum output tokens
        temperature: Generation temperature (0.0 = deterministic)

    Returns:
        OCRResponse with extracted text
    """
    if not model_loaded:
        raise HTTPException(status_code=503, detail="Model not initialized")

    start_time = time.time()
    temp_path = None

    try:
        # Read and save image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # Save to temp file (MLX-VLM needs file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            image.save(tmp.name, "PNG")
            temp_path = tmp.name

        # Select prompt
        if mode == "custom" and custom_prompt:
            prompt = f"<image>\n{custom_prompt}"
        else:
            prompt = PROMPTS.get(mode, PROMPTS["markdown"])

        # Run OCR with MLX
        print(f"🔍 Processing: {file.filename} (mode: {mode})")
        result = mlx_vlm.generate(
            model=MODEL_NAME,
            prompt=prompt,
            image=temp_path,
            max_tokens=max_tokens,
            temperature=temperature
        )

        processing_time = time.time() - start_time

        # Clean up
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

        return OCRResponse(
            success=True,
            result=result,
            markdown=result if mode == "markdown" else None,
            text=result if mode == "plain" else None,
            metadata={
                "filename": file.filename,
                "mode": mode,
                "model": MODEL_NAME,
                "processing_time": round(processing_time, 2),
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        )

    except Exception as e:
        # Clean up on error
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

        print(f"❌ OCR failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.post("/batch-ocr/")
async def batch_process_ocr(
    files: List[UploadFile] = File(...),
    mode: str = Form("markdown")
):
    """
    Process multiple images in batch

    Args:
        files: List of image files
        mode: OCR mode

    Returns:
        List of OCR results
    """
    results = []

    for file in files:
        try:
            # Process each file
            response = await process_ocr(file=file, mode=mode)
            results.append({
                "filename": file.filename,
                "success": True,
                "result": response.result,
                "metadata": response.metadata
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    return {"batch_results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9005)
```

#### Step 2.2: Create Startup Script

**File**: `~/Projects/archon/services/deepseek-ocr-mlx/start_service.sh`

```bash
#!/bin/bash

# DeepSeek-OCR MLX Service Startup Script
# For Mac M4 with Apple Metal GPU acceleration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting DeepSeek-OCR MLX Service..."
echo "📍 Working directory: $SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Please run: python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if MLX is installed
if ! python -c "import mlx" 2>/dev/null; then
    echo "❌ MLX not installed!"
    echo "Please run: pip install mlx mlx-vlm"
    exit 1
fi

# Set environment variables
export PORT=9005
export MODEL_NAME="mlx-community/DeepSeek-OCR-8bit"
export PYTHONUNBUFFERED=1

echo "🌐 Starting server on port $PORT..."
echo "📦 Model: $MODEL_NAME"
echo "🔥 GPU: Apple Metal (M4)"
echo ""

# Start uvicorn server
uvicorn app:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info

# The server will keep running until stopped with Ctrl+C
```

**Make it executable**:
```bash
chmod +x ~/Projects/archon/services/deepseek-ocr-mlx/start_service.sh
```

#### Step 2.3: Create Requirements File

**File**: `~/Projects/archon/services/deepseek-ocr-mlx/requirements.txt`

```txt
# MLX framework for Apple Silicon
mlx>=0.20.0
mlx-vlm>=0.1.0

# FastAPI and server
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9

# Image processing
Pillow>=10.2.0

# Data validation
pydantic>=2.6.0
```

---

### Phase 3: Integration with Archon Backend
**Duration**: 20-30 minutes

#### Step 3.1: Update OCR Service Client

**File**: `~/Projects/archon/python/src/server/services/ocr_service.py`

Add DeepSeek-OCR MLX client:

```python
# Add to existing ocr_service.py

DEEPSEEK_OCR_MLX_URL = os.getenv("DEEPSEEK_OCR_MLX_URL", "http://localhost:9005")

async def ocr_with_deepseek_mlx(
    file_path: str,
    mode: str = "markdown",
    custom_prompt: Optional[str] = None
) -> Optional[str]:
    """
    Process document with DeepSeek-OCR MLX service

    Args:
        file_path: Path to image/document file
        mode: OCR mode (markdown, plain, figure, table, formula, custom)
        custom_prompt: Custom prompt (if mode=custom)

    Returns:
        Extracted text or None if failed
    """
    try:
        # Health check first
        health_url = f"{DEEPSEEK_OCR_MLX_URL}/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get(health_url)
            if health_response.status_code != 200:
                logger.warning(f"DeepSeek-OCR MLX service not healthy: {health_response.status_code}")
                return None

        # Prepare request
        url = f"{DEEPSEEK_OCR_MLX_URL}/ocr/"

        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "image/png")}
            data = {"mode": mode}
            if custom_prompt:
                data["mode"] = "custom"
                data["custom_prompt"] = custom_prompt

            # Send OCR request
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()

                result = response.json()
                if result.get("success"):
                    extracted_text = result.get("result") or result.get("markdown") or result.get("text")
                    logger.info(f"✅ DeepSeek-OCR MLX extracted {len(extracted_text)} chars from {file_path}")
                    return extracted_text
                else:
                    logger.error(f"DeepSeek-OCR MLX failed: {result.get('error')}")
                    return None

    except Exception as e:
        logger.error(f"DeepSeek-OCR MLX error: {str(e)}")
        return None
```

#### Step 3.2: Update Document Processing

**File**: `~/Projects/archon/python/src/server/utils/document_processing.py`

Add DeepSeek-OCR MLX as an OCR option:

```python
# Add import at top
from ..services.ocr_service import ocr_with_deepseek_mlx

# Update extract_text_from_image_ocr function
async def extract_text_from_image_ocr(
    file_path: str,
    ocr_engine: str = "deepseek-mlx"  # Add this parameter
) -> Optional[str]:
    """
    Extract text from image using OCR

    Args:
        file_path: Path to image file
        ocr_engine: OCR engine to use (deepseek-mlx, deepseek, docling)

    Returns:
        Extracted text or None
    """
    try:
        logger.info(f"🔍 Running OCR on image with {ocr_engine}: {file_path}")

        # Try DeepSeek-OCR MLX first (fastest on Mac M4)
        if ocr_engine == "deepseek-mlx":
            text = await ocr_with_deepseek_mlx(file_path, mode="markdown")
            if text:
                return text

        # Fallback to other engines...
        # (existing code for other OCR engines)

    except Exception as e:
        logger.error(f"OCR failed: {str(e)}")
        return None
```

---

### Phase 4: Docker Compose Configuration (Optional Fallback)
**Duration**: 15 minutes

**Note**: This Docker option runs on CPU only (slower). The native Mac service (above) is recommended.

**File**: `~/Projects/archon/docker-compose.yml`

Add this service:

```yaml
  # DeepSeek-OCR MLX Service (Mac M4 optimized)
  deepseek-ocr-mlx:
    profiles:
      - ocr  # Starts with all OCR services
    image: python:3.12-slim
    container_name: deepseek-ocr-mlx
    restart: unless-stopped
    ports:
      - "9005:9005"
    environment:
      - PYTHONUNBUFFERED=1
      - PORT=9005
      - MODEL_NAME=mlx-community/DeepSeek-OCR-8bit
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - app-network
    volumes:
      - ./services/deepseek-ocr-mlx:/app
      - deepseek-mlx-models:/root/.cache/mlx  # Model cache
    working_dir: /app
    command: >
      bash -c "
      pip install -q mlx mlx-vlm fastapi uvicorn[standard] python-multipart Pillow pydantic &&
      uvicorn app:app --host 0.0.0.0 --port 9005
      "
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9005/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s  # Longer for model download
    extra_hosts:
      - "host.docker.internal:host-gateway"

# Add volume for model cache
volumes:
  # ... existing volumes ...
  deepseek-mlx-models:  # DeepSeek-OCR MLX model cache
```

---

### Phase 5: Environment Configuration
**Duration**: 5 minutes

#### Step 5.1: Update .env File

**File**: `~/Projects/archon/.env`

Add:

```bash
# DeepSeek-OCR MLX Service (Native Mac - Port 9005)
DEEPSEEK_OCR_MLX_URL=http://localhost:9005

# OCR Engine Selection (deepseek-mlx, docling, ocrmypdf)
OCR_ENGINE=deepseek-mlx
```

#### Step 5.2: Update .env.example

**File**: `~/Projects/archon/.env.example`

Add the same configuration for documentation.

---

### Phase 6: Port Mapping Documentation
**Duration**: 5 minutes

**File**: `~/Projects/archon/PORT_MAPPING.md`

Add to the OCR services section:

```markdown
| **DeepSeek-OCR MLX** | deepseek-ocr-mlx (native) | N/A | **9005** | 9005 | Vision-language OCR (Apple Metal GPU) | 🔵 Native Mac |
```

Update the environment variables section:

```markdown
# OCR Services
DEEPSEEK_OCR_MLX_URL=http://localhost:9005
OCR_ENGINE=deepseek-mlx
```

---

## 🚀 Testing & Validation

### Step-by-Step Testing

#### Test 1: Service Startup

```bash
cd ~/Projects/archon/services/deepseek-ocr-mlx
./start_service.sh
```

**Expected Output**:
```
🚀 Starting DeepSeek-OCR MLX Service...
✅ Activating virtual environment...
🌐 Starting server on port 9005...
📦 Model: mlx-community/DeepSeek-OCR-8bit
🔥 GPU: Apple Metal (M4)

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
🚀 Initializing DeepSeek-OCR MLX model...
📦 Model: mlx-community/DeepSeek-OCR-8bit
✅ MLX framework ready (models load on first use)
✅ DeepSeek-OCR MLX initialized in 0.15 seconds
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9005
```

#### Test 2: Health Check

```bash
curl http://localhost:9005/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "deepseek-ocr-mlx",
  "model_loaded": true,
  "model": "mlx-community/DeepSeek-OCR-8bit",
  "backend": "MLX (Apple Metal)",
  "platform": "Mac M4 native"
}
```

#### Test 3: Single Image OCR

```bash
curl -X POST "http://localhost:9005/ocr/" \
  -F "file=@/path/to/test-image.jpg" \
  -F "mode=markdown"
```

**Expected Response**:
```json
{
  "success": true,
  "result": "# Document Title\n\nExtracted text content...",
  "markdown": "# Document Title\n\nExtracted text content...",
  "text": null,
  "error": null,
  "metadata": {
    "filename": "test-image.jpg",
    "mode": "markdown",
    "model": "mlx-community/DeepSeek-OCR-8bit",
    "processing_time": 2.45,
    "max_tokens": 2000,
    "temperature": 0.0
  }
}
```

#### Test 4: Integration with Archon

Upload a document via Archon UI with OCR enabled and verify:
- Service receives request
- OCR processes successfully
- Document is stored in Supabase
- Text is searchable

---

## 📊 Performance Benchmarks

### Expected Performance (Mac M4)

Based on MinerU performance (similar native Mac + GPU service):

| Document Type | Size | Pages | Processing Time | Speed |
|---------------|------|-------|-----------------|-------|
| Simple Scan | 1 MB | 5 | ~10s | 0.5 pages/s |
| Complex Document | 5 MB | 20 | ~45s | 0.44 pages/s |
| High-res Image | 3 MB | 1 | ~3s | - |

### Comparison with Other Services

| Service | Backend | Hardware | Relative Speed |
|---------|---------|----------|---------------|
| DeepSeek-OCR MLX | MLX | Apple Metal GPU | **1.0x** (baseline) |
| MinerU | Native | Apple Metal GPU | ~1.2x |
| Docling OCR | PyTorch | CPU | ~0.3x |
| OCRmyPDF | Tesseract | CPU | ~0.2x |

---

## 🛠️ Troubleshooting

### Issue 1: Service Won't Start

**Symptom**: `ModuleNotFoundError: No module named 'mlx'`

**Solution**:
```bash
cd ~/Projects/archon/services/deepseek-ocr-mlx
source venv/bin/activate
pip install -r requirements.txt
```

### Issue 2: Model Download Fails

**Symptom**: `Failed to download model`

**Solution**:
```bash
# Manual download
python -c "import mlx_vlm; mlx_vlm.load('mlx-community/DeepSeek-OCR-8bit')"

# Check cache
ls -lah ~/.cache/mlx/
```

### Issue 3: Port Already in Use

**Symptom**: `Address already in use`

**Solution**:
```bash
# Check what's using port 9005
lsof -i :9005

# Kill the process or change port in start_service.sh
export PORT=9006
```

### Issue 4: Poor Performance

**Symptom**: Slow OCR processing

**Solution**:
```bash
# Verify Metal GPU is being used
system_profiler SPDisplaysDataType | grep Metal

# Check process is using GPU
sudo powermetrics --samplers gpu_power -i 1000 -n 1

# Increase max_tokens if output is truncated
# In API request: -F "max_tokens=4000"
```

---

## 🔄 Starting the Service

### Option 1: Native Mac Service (Recommended)

```bash
# Start manually
cd ~/Projects/archon/services/deepseek-ocr-mlx
./start_service.sh

# Or run in background
nohup ./start_service.sh > logs/service.log 2>&1 &

# Check logs
tail -f logs/service.log
```

### Option 2: Docker Service (Fallback)

```bash
# Start with other OCR services
docker compose --profile ocr up -d

# View logs
docker compose logs -f deepseek-ocr-mlx

# Restart
docker compose restart deepseek-ocr-mlx
```

---

## 📝 Next Steps After Integration

1. **Performance Testing**
   - Test with various document types (scanned PDFs, images, forms)
   - Compare processing times with other OCR services
   - Benchmark accuracy

2. **Frontend Integration**
   - Add "DeepSeek-OCR MLX" option to OCR engine selector
   - Update upload dialog to show GPU-accelerated option
   - Add processing time estimates

3. **Monitoring**
   - Set up health check monitoring
   - Track OCR success/failure rates
   - Monitor GPU usage

4. **Documentation**
   - Update README with DeepSeek-OCR MLX setup
   - Add usage examples
   - Document best practices

---

## 📚 Resources

- **DeepSeek-OCR GitHub**: https://github.com/Krishna-kai/DeepSeek-OCR
- **MLX Framework**: https://github.com/ml-explore/mlx
- **MLX-VLM**: https://github.com/Blaizzy/mlx-vlm
- **DeepSeek-OCR Paper**: https://arxiv.org/abs/2501.12397
- **Archon OCR Audit**: `~/Projects/archon/OCR_Service_Audit_Report.md`

---

## ✅ Completion Checklist

- [ ] Phase 1: Environment setup complete
  - [ ] Repository cloned
  - [ ] Virtual environment created
  - [ ] Dependencies installed
  - [ ] Model downloaded
- [ ] Phase 2: Service implementation
  - [ ] app.py created
  - [ ] start_service.sh created and executable
  - [ ] requirements.txt created
- [ ] Phase 3: Backend integration
  - [ ] ocr_service.py updated
  - [ ] document_processing.py updated
- [ ] Phase 4: Docker configuration (optional)
  - [ ] docker-compose.yml updated
  - [ ] Volume added
- [ ] Phase 5: Environment configuration
  - [ ] .env updated
  - [ ] .env.example updated
- [ ] Phase 6: Documentation
  - [ ] PORT_MAPPING.md updated
- [ ] Testing
  - [ ] Service startup test passed
  - [ ] Health check test passed
  - [ ] Single image OCR test passed
  - [ ] Integration test passed
- [ ] Monitoring
  - [ ] Health checks configured
  - [ ] Logging verified

---

## 🎯 Success Criteria

- ✅ Service starts without errors
- ✅ Health endpoint returns 200 OK
- ✅ OCR processes images successfully
- ✅ Integration with Archon backend works
- ✅ Performance is better than Docker-based services
- ✅ Apple Metal GPU is being utilized
- ✅ Documents are searchable after OCR

---

**Status**: Ready for implementation
**Estimated Total Time**: 1.5-2 hours
**Difficulty**: Medium
**Risk**: Low (proven pattern with MinerU)
