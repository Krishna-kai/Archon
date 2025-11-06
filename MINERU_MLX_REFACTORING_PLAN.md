# MinerU MLX Refactoring Plan
**Date**: 2025-11-06
**Target Port**: 9006 (changed from 8055)
**Platform**: Mac M4 Studio with Apple Metal GPU
**Purpose**: Complete refactoring to match DeepSeek-OCR MLX pattern and enable dual MLX service testing

---

## Executive Summary

This refactoring plan standardizes the MinerU service to match the DeepSeek-OCR MLX implementation pattern, moving from port 8055 to 9006 for consistency with Archon's OCR services architecture (9000-9099 range).

### Key Objectives

✅ **Port Standardization**: Move from 8055 → 9006 (OCR services range)
✅ **Service Reorganization**: Move from `python/src/mineru_service/` → `services/mineru-mlx/`
✅ **Pattern Consistency**: Match DeepSeek-OCR MLX structure
✅ **Dual MLX Testing**: Enable side-by-side testing of both MLX services
✅ **Documentation**: Complete refactoring documentation

---

## Current State Analysis

### Existing Implementation

**Location**: `~/Projects/archon/python/src/mineru_service/`
**Current Port**: 8055
**Current Status**: Working native service with Apple Silicon GPU acceleration

**Files**:
1. `python/src/mineru_service/main.py` (7,311 bytes)
   - FastAPI application with MinerU integration
   - Uses `doc_analyze` from MinerU backend
   - Hardcoded port 8055 (line 219)

2. `python/start_mineru_service.sh` (234 bytes)
   - Simple startup script using `uv run`
   - No virtual environment management

3. `python/src/server/services/mineru_http_client.py` (4,803 bytes)
   - HTTP client for Docker containers
   - Calls native MinerU service
   - References port 8055 in documentation

4. `python/src/server/services/mineru_service.py` (CLI-based service)
   - Alternative CLI-based implementation
   - Not used when HTTP service is available

**Environment Configuration**:
- `.env`: `MINERU_SERVICE_URL=http://host.docker.internal:8055`
- `.env.example`: No MinerU configuration

### Integration Points

1. **document_processing.py**: `extract_text_from_mineru()` function
2. **Backend API**: PDF upload with `use_mineru=True` parameter
3. **Docker Compose**: Reference in comments (native service preferred)

---

## Problems with Current Implementation

### 1. **Port Inconsistency**
- ❌ Port 8055 is outside OCR services range (9000-9099)
- ❌ Doesn't follow Archon port allocation strategy
- ❌ Confusing for users expecting consistent port numbering

### 2. **Location Inconsistency**
- ❌ Service in `python/src/mineru_service/` (inside Python package)
- ❌ DeepSeek-OCR MLX in `services/deepseek-ocr-mlx/` (separate service)
- ❌ Mixed architecture patterns

### 3. **Startup Script Inconsistency**
- ❌ Script in `python/` directory (not with service)
- ❌ No virtual environment management
- ❌ No dependency checking
- ❌ Minimal error handling

### 4. **Documentation Gaps**
- ❌ No .env.example entry
- ❌ PORT_MAPPING.md lists as "External" (8055)
- ❌ No startup/usage instructions
- ❌ Missing from main README

---

## Refactoring Goals

### Goal 1: Port Standardization ✅

**Change port from 8055 → 9006**

**Rationale**:
- Fits in OCR services range (9000-9099)
- Sequential after Parser Service (9004) and DeepSeek-OCR MLX (9005)
- Clear grouping with other OCR services

**Impact**:
- Update service main.py
- Update .env configuration
- Update HTTP client references
- Update documentation

### Goal 2: Service Reorganization ✅

**Move from `python/src/mineru_service/` → `services/mineru-mlx/`**

**Rationale**:
- Matches DeepSeek-OCR MLX pattern
- Separates service from Python backend
- Clear organization for native Mac services
- Easier to maintain and understand

**New Structure**:
```
services/
├── deepseek-ocr-mlx/    # Vision-language OCR (port 9005)
│   ├── app.py
│   ├── requirements.txt
│   ├── start_service.sh
│   └── logs/
└── mineru-mlx/          # Document processing OCR (port 9006)
    ├── app.py
    ├── requirements.txt
    ├── start_service.sh
    └── logs/
```

### Goal 3: Pattern Consistency ✅

**Match DeepSeek-OCR MLX implementation pattern**

**Requirements**:
1. Comprehensive `app.py` with proper logging
2. Detailed `requirements.txt`
3. Robust `start_service.sh` with venv management
4. Health check endpoint matching pattern
5. Consistent error handling
6. Similar API structure

### Goal 4: Environment Configuration ✅

**Add proper environment variable support**

**Changes Needed**:
1. Add `MINERU_MLX_URL` environment variable
2. Update `.env` with new port
3. Add configuration to `.env.example`
4. Support both local and Docker URLs

### Goal 5: Documentation ✅

**Complete documentation updates**

**Updates Needed**:
1. PORT_MAPPING.md - Update port to 9006
2. README additions - MinerU MLX service setup
3. Service README - Individual service documentation
4. Refactoring completion document

---

## Implementation Plan

### Phase 1: Service Reorganization (20-30 min)

#### Step 1.1: Create New Service Directory
```bash
mkdir -p ~/Projects/archon/services/mineru-mlx/logs
```

#### Step 1.2: Create Enhanced app.py

**File**: `services/mineru-mlx/app.py`

**Key Improvements**:
- Update port to 9006
- Add comprehensive logging
- Add environment variable support for port
- Add root endpoint with service info
- Enhance error messages
- Add metadata endpoints
- Match DeepSeek-OCR MLX structure

#### Step 1.3: Create requirements.txt

**File**: `services/mineru-mlx/requirements.txt`

```txt
# MinerU Core - Document processing with MLX support
mineru[full]>=2.6.4

# FastAPI and server
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9

# Image processing
Pillow>=10.2.0

# Data validation
pydantic>=2.6.0

# HTTP client
httpx>=0.26.0

# PDF processing
pypdfium2>=4.26.0

# OCR and ML
PaddleOCR>=2.8.0
torch>=2.0.0
transformers>=4.36.0
```

#### Step 1.4: Create Enhanced start_service.sh

**File**: `services/mineru-mlx/start_service.sh`

**Features**:
- Virtual environment creation/activation
- Dependency installation
- Health checks
- Error handling
- Environment variable support
- Logging setup

### Phase 2: Backend Integration Updates (15-20 min)

#### Step 2.1: Update HTTP Client

**File**: `python/src/server/services/mineru_http_client.py`

**Changes**:
- Update default service URL documentation
- Add support for `MINERU_MLX_URL` environment variable
- Update comments/docstrings referencing port 8055

#### Step 2.2: Update Service Discovery

**File**: `python/src/server/services/ocr_service.py` or similar

**Changes**:
- Update MinerU service URL configuration
- Support both 8055 (legacy) and 9006 (new) for transition period
- Add deprecation warning for 8055

### Phase 3: Environment Configuration (10 min)

#### Step 3.1: Update .env

**File**: `.env`

```bash
# MinerU MLX Native Service URL (Mac M4 with Apple Metal GPU)
# Run the service: ~/Projects/archon/services/mineru-mlx/start_service.sh
# For Docker containers to access host service:
MINERU_MLX_URL=http://localhost:9006

# Legacy MinerU URL (deprecated - use MINERU_MLX_URL)
# MINERU_SERVICE_URL=http://host.docker.internal:8055
```

#### Step 3.2: Update .env.example

**File**: `.env.example`

```bash
# MinerU MLX Service Configuration (Optional but Recommended)
# MinerU provides advanced PDF processing with formula and table extraction
# Port 9006 for consistency with OCR services (9000-9099)

# MinerU MLX Native Service (Recommended for Mac M4 - Apple Metal GPU)
# Run the native service: ~/Projects/archon/services/mineru-mlx/start_service.sh
MINERU_MLX_URL=http://localhost:9006

# For Docker containers to access host service:
# MINERU_SERVICE_URL=http://host.docker.internal:9006
```

### Phase 4: Documentation Updates (15 min)

#### Step 4.1: Update PORT_MAPPING.md

**Changes**:
- Update MinerU entry from 8055 → 9006
- Change from "🔵 External" to "🔵 Native Service"
- Add to OCR services table properly
- Update port allocation section
- Add health check URL

#### Step 4.2: Update docker-compose.yml Comments

**Changes**:
- Update MinerU comment with new port
- Update MINERU_SERVICE_URL reference

#### Step 4.3: Create Service README

**File**: `services/mineru-mlx/README.md`

**Content**:
- Service description
- Installation instructions
- Usage examples
- API endpoints
- Performance notes

### Phase 5: Migration & Cleanup (10-15 min)

#### Step 5.1: Test New Service

```bash
# Start new service
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh

# Test health endpoint
curl http://localhost:9006/health

# Test processing endpoint
curl -X POST "http://localhost:9006/process" \
  -F "file=@test.pdf" \
  -F "device=mps"
```

#### Step 5.2: Update Backend Configuration

```bash
# Update .env
MINERU_MLX_URL=http://localhost:9006
```

#### Step 5.3: Test Integration

```bash
# Start Archon backend
docker compose up -d

# Upload PDF with MinerU enabled
# Verify logs show connection to port 9006
```

#### Step 5.4: Archive Old Implementation

```bash
# Keep for reference but mark as deprecated
mv ~/Projects/archon/python/src/mineru_service \
   ~/Projects/archon/python/src/mineru_service.old

# Keep startup script for backwards compatibility
# Add deprecation notice
```

---

## Detailed File Changes

### 1. services/mineru-mlx/app.py

**Key Changes from Current Implementation**:

```python
# OLD (line 219):
port=8055,

# NEW:
port=int(os.getenv("PORT", 9006)),

# Add environment variable support
PORT = int(os.getenv("PORT", 9006))
HOST = os.getenv("HOST", "0.0.0.0")
MODEL_CACHE = os.getenv("MINERU_MODEL_CACHE", "~/.cache/mineru")

# Enhanced logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add models endpoint
@app.get("/models")
async def list_models():
    """List available MinerU models"""
    return {
        "models": [
            {
                "id": "mineru-2.6",
                "name": "MinerU 2.6",
                "description": "Document processing with formula and table extraction",
                "capabilities": ["pdf", "formulas", "tables", "images"],
                "loaded": True
            }
        ]
    }

# Enhanced health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mineru-mlx",
        "version": "2.6.4",
        "backend": "MLX (Apple Metal)",
        "platform": "Mac M4 native",
        "port": PORT
    }
```

### 2. services/mineru-mlx/start_service.sh

**Complete Rewrite** to match DeepSeek-OCR MLX pattern:

```bash
#!/bin/bash

# MinerU MLX Service Startup Script
# For Mac M4 with Apple Metal GPU acceleration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting MinerU MLX Service..."
echo "📍 Working directory: $SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv || python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Check if MinerU is installed
if ! python -c "import mineru" 2>/dev/null; then
    echo "❌ MinerU not installed!"
    echo "Installing MinerU framework..."
    pip install "mineru[full]"
fi

# Set environment variables
export PORT=${PORT:-9006}
export PYTHONUNBUFFERED=1
export MINERU_MODEL_CACHE=${MINERU_MODEL_CACHE:-"~/.cache/mineru"}

echo ""
echo "🌐 Starting server on port $PORT..."
echo "📦 Service: MinerU MLX"
echo "🔥 GPU: Apple Metal (M4)"
echo "📝 Logs: Will appear below..."
echo ""
echo "Press Ctrl+C to stop the service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start uvicorn server
uvicorn app:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info

# The server will keep running until stopped with Ctrl+C
```

### 3. python/src/server/services/mineru_http_client.py

**Line 32**: Update comment
```python
# OLD:
# Args:
#     service_url: Base URL of MinerU service (e.g., "http://host.docker.internal:8055")

# NEW:
# Args:
#     service_url: Base URL of MinerU service (e.g., "http://host.docker.internal:9006")
```

### 4. Environment Variables

**.env**:
```bash
# OLD:
MINERU_SERVICE_URL=http://host.docker.internal:8055

# NEW:
MINERU_MLX_URL=http://localhost:9006
# For Docker: http://host.docker.internal:9006
```

**.env.example**:
```bash
# Add complete MinerU MLX configuration section
# (See Phase 3.2 above)
```

### 5. PORT_MAPPING.md

**Update MinerU entry**:
```markdown
# OLD:
| **MinerU** | (Native Mac) | N/A | **8055** | 8055 | Apple GPU-accelerated OCR | 🔵 External |

# NEW:
| **MinerU MLX** | (Native Mac) | N/A | **9006** | 9006 | PDF processing with formulas/tables (Apple Metal GPU) | 🔵 Native Service |
```

**Update port allocation**:
```markdown
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
```

**Add health check**:
```markdown
| MinerU MLX | http://localhost:9006/health |
```

---

## Testing Plan

### Test 1: Service Startup

```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

**Expected Output**:
```
🚀 Starting MinerU MLX Service...
📍 Working directory: /Users/krishna/Projects/archon/services/mineru-mlx
✅ Activating virtual environment...
📥 Installing dependencies...
🌐 Starting server on port 9006...
📦 Service: MinerU MLX
🔥 GPU: Apple Metal (M4)
📝 Logs: Will appear below...

INFO: Started server process [12345]
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:9006
```

### Test 2: Health Check

```bash
curl http://localhost:9006/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "mineru-mlx",
  "version": "2.6.4",
  "backend": "MLX (Apple Metal)",
  "platform": "Mac M4 native",
  "port": 9006
}
```

### Test 3: PDF Processing

```bash
curl -X POST "http://localhost:9006/process" \
  -F "file=@test.pdf" \
  -F "device=mps" \
  -F "extract_charts=true"
```

**Expected Response**:
```json
{
  "success": true,
  "text": "## Page 1\n\n[Extracted text...]",
  "images": [
    {
      "name": "image_0.png",
      "base64": "iVBORw0KGgo...",
      "page_number": null,
      "image_index": 0,
      "mime_type": "image/png"
    }
  ],
  "metadata": {
    "filename": "test.pdf",
    "pages": 5,
    "chars_extracted": 12345,
    "formulas_count": 10,
    "tables_count": 3,
    "images_extracted": 5
  }
}
```

### Test 4: Dual MLX Services

**Terminal 1** - DeepSeek-OCR MLX:
```bash
cd ~/Projects/archon/services/deepseek-ocr-mlx
./start_service.sh
# Should start on port 9005
```

**Terminal 2** - MinerU MLX:
```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
# Should start on port 9006
```

**Terminal 3** - Test both:
```bash
# Test DeepSeek-OCR MLX
curl http://localhost:9005/health

# Test MinerU MLX
curl http://localhost:9006/health

# Both should respond healthy
```

### Test 5: Integration with Archon

```bash
# Start both MLX services
# (Terminal 1 and 2 from Test 4)

# Start Archon backend
docker compose up -d

# Upload PDF via Archon UI
# - Enable OCR with DeepSeek-OCR MLX
# - Upload another PDF with MinerU enabled
# - Verify both services process correctly

# Check logs
docker compose logs archon-server | grep -i "mlx\|mineru"
```

---

## Migration Checklist

### Pre-Migration

- [ ] Backup current implementation
  ```bash
  cp -r ~/Projects/archon/python/src/mineru_service \
        ~/Projects/archon/python/src/mineru_service.backup
  ```

- [ ] Document current port configuration
- [ ] Test current implementation works on 8055

### Migration Steps

- [ ] **Phase 1**: Service reorganization
  - [ ] Create `services/mineru-mlx/` directory
  - [ ] Create enhanced `app.py`
  - [ ] Create `requirements.txt`
  - [ ] Create enhanced `start_service.sh`
  - [ ] Make startup script executable

- [ ] **Phase 2**: Backend updates
  - [ ] Update `mineru_http_client.py`
  - [ ] Update service URL references
  - [ ] Add environment variable support

- [ ] **Phase 3**: Environment configuration
  - [ ] Update `.env` with port 9006
  - [ ] Update `.env.example`
  - [ ] Test environment variables

- [ ] **Phase 4**: Documentation
  - [ ] Update `PORT_MAPPING.md`
  - [ ] Update docker-compose.yml comments
  - [ ] Create service README
  - [ ] Create refactoring completion document

- [ ] **Phase 5**: Testing
  - [ ] Test service startup on 9006
  - [ ] Test health endpoint
  - [ ] Test PDF processing
  - [ ] Test dual MLX services
  - [ ] Test Archon integration
  - [ ] Performance benchmark

### Post-Migration

- [ ] Archive old implementation
- [ ] Update main README
- [ ] Create migration notes
- [ ] Document breaking changes

---

## Breaking Changes

### Port Change: 8055 → 9006

**Impact**: Existing installations need to update

**Migration Path**:
1. Update `.env`: `MINERU_MLX_URL=http://localhost:9006`
2. Restart MinerU service on new port
3. Restart Archon backend to pick up new port

**Backwards Compatibility**: None (clean break for standardization)

### Location Change: `python/src/mineru_service/` → `services/mineru-mlx/`

**Impact**: Startup script path changes

**Migration Path**:
1. Use new startup script: `services/mineru-mlx/start_service.sh`
2. Update any custom scripts or documentation

**Backwards Compatibility**: Old location kept for reference (deprecated)

---

## Benefits of Refactoring

### 1. Consistency ✅
- All OCR services in 9000-9099 port range
- Uniform service structure across MLX services
- Standardized startup and configuration

### 2. Maintainability ✅
- Clear separation of services
- Easy to understand service organization
- Consistent patterns for future services

### 3. User Experience ✅
- Predictable port numbering
- Similar setup process for all MLX services
- Clear documentation

### 4. Testing ✅
- Easy to run multiple MLX services
- Clear isolation between services
- Better debugging capabilities

### 5. Scalability ✅
- Room for more OCR services (9007-9099)
- Clear pattern to follow
- Modular architecture

---

## Timeline

**Total Estimated Time**: 70-90 minutes

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Service reorganization | 20-30 min |
| 2 | Backend integration | 15-20 min |
| 3 | Environment config | 10 min |
| 4 | Documentation | 15 min |
| 5 | Testing & validation | 15-20 min |

---

## Success Criteria

✅ MinerU service runs on port 9006
✅ Service located in `services/mineru-mlx/`
✅ Matches DeepSeek-OCR MLX pattern
✅ Both MLX services run simultaneously
✅ All health checks pass
✅ PDF processing works correctly
✅ Integration with Archon backend verified
✅ Documentation complete and accurate
✅ All tests passing

---

## Next Steps After Refactoring

### 1. Performance Comparison
- Benchmark both MLX services
- Compare processing times
- Compare accuracy
- Document strengths of each service

### 2. Usage Guidelines
- When to use DeepSeek-OCR MLX (9005)
- When to use MinerU MLX (9006)
- Combined workflow recommendations

### 3. Future Enhancements
- Add model caching optimization
- Add batch processing for MinerU
- Add progress tracking for large PDFs
- Add GPU usage monitoring

---

## References

### Current Implementation
- **MinerU Service**: `python/src/mineru_service/main.py`
- **HTTP Client**: `python/src/server/services/mineru_http_client.py`
- **Startup Script**: `python/start_mineru_service.sh`

### Reference Implementation
- **DeepSeek-OCR MLX**: `services/deepseek-ocr-mlx/`
- **Implementation Guide**: `DEEPSEEK_OCR_MLX_INTEGRATION_PLAN.md`
- **Completion Doc**: `DEEPSEEK_OCR_MLX_IMPLEMENTATION_COMPLETE.md`

### External Resources
- **MinerU GitHub**: https://github.com/opendatalab/MinerU
- **MinerU Documentation**: https://github.com/opendatalab/MinerU/tree/master/docs
- **MLX Framework**: https://github.com/ml-explore/mlx

---

**Status**: Ready for Implementation
**Created**: 2025-11-06
**Target Completion**: 2025-11-06 (same day)
**Priority**: Medium (improves consistency, not urgent)
