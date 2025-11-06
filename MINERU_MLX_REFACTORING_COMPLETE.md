# ✅ MinerU MLX Refactoring - IMPLEMENTATION COMPLETE

**Date**: 2025-11-06
**Platform**: Mac M4 Studio with Apple Metal GPU
**Port**: 9006 (Changed from 8055)
**Status**: Ready for Testing

---

## 🎉 Executive Summary

The MinerU MLX service has been **successfully refactored** following the DeepSeek-OCR MLX pattern! This implementation provides consistent service organization, improved monitoring, and better integration with Archon's OCR pipeline.

### Key Achievements

✅ **Service Reorganization** - Moved from `python/src/mineru_service/` to `services/mineru-mlx/`
✅ **Port Standardization** - Changed from 8055 to 9006 (OCR services range: 9000-9099)
✅ **Enhanced Service Implementation** - Improved logging, health checks, and error handling
✅ **Pattern Consistency** - Matches DeepSeek-OCR MLX architecture for maintainability
✅ **Environment Configuration** - Updated .env and .env.example with clear documentation
✅ **Documentation Updated** - PORT_MAPPING.md reflects new port and service organization

---

## 📦 What Was Refactored

### Phase 1: Service Reorganization ✅

**New Location**: `~/Projects/archon/services/mineru-mlx/`

**Files Created**:

1. **app.py** (Enhanced FastAPI application)
   - Port changed from 8055 to 9006
   - Enhanced logging with timestamps and emoji indicators
   - Comprehensive health check endpoint with detailed metadata
   - Improved error handling with processing time tracking
   - CORS middleware for cross-origin requests
   - Startup/shutdown event handlers
   - Processing time metrics included in responses

2. **requirements.txt** (Comprehensive dependencies)
   - FastAPI and Uvicorn for web service
   - magic-pdf[full] for MinerU functionality
   - Pillow for image processing
   - python-json-logger for enhanced logging

3. **start_service.sh** (Enhanced startup script)
   - Virtual environment management
   - Dependency checking and installation
   - Port conflict detection and resolution
   - Health check validation
   - Interactive prompts for dependency reinstallation
   - Comprehensive logging during startup
   - Made executable (755 permissions)

4. **logs/** directory
   - Created for service logging

### Phase 2: Backend Integration ✅

**No Changes Required** - The existing backend integration already uses environment-based service discovery:

- `python/src/server/services/mineru_service.py` - Uses `MINERU_SERVICE_URL` env var
- `python/src/server/services/mineru_http_client.py` - HTTP client works with any URL
- Service discovery in `get_mineru_service()` function automatically switches based on environment

### Phase 3: Environment Configuration ✅

**Files Modified**:

1. **.env**
   - Updated `MINERU_SERVICE_URL` from port 8055 to 9006
   - Enhanced documentation with service startup instructions
   - Clear comment indicating Docker container access pattern

2. **.env.example**
   - Added comprehensive MinerU MLX configuration section
   - Documented recommended usage for Mac M4
   - Included startup instructions and Docker access pattern
   - Positioned after DeepSeek-OCR section for logical grouping

### Phase 4: Documentation Updates ✅

**File Modified**: `PORT_MAPPING.md`

**Changes**:
- Updated MinerU service name from "MinerU" to "MinerU MLX"
- Changed port from 8055 to 9006
- Updated service description to highlight formula/table processing
- Moved from "8000-8099" range to "9000-9099" (OCR services)
- Updated port allocation strategy section
- Updated environment variables section
- Added health check URL: http://localhost:9006/health
- Removed 8055 from port documentation

---

## 🚀 Quick Start Guide

### Start the Service

```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

**Expected Output**:

```
════════════════════════════════════════════════════════════
🚀 MinerU MLX Service Startup
════════════════════════════════════════════════════════════

✅ Using Python 3.12.x
ℹ️  Virtual environment already exists
ℹ️  Activating virtual environment...
✅ Virtual environment activated
ℹ️  Checking dependencies...
ℹ️  Dependencies appear to be installed
📦 Reinstall dependencies? (y/N): n
ℹ️  Skipping dependency installation
✅ Log directory created: .../logs

════════════════════════════════════════════════════════════
🌐 Starting MinerU MLX Service
════════════════════════════════════════════════════════════
📍 Port: 9006
🖥️  Host: 0.0.0.0
📝 Log Level: info
🔥 Backend: MinerU with Apple Metal GPU
📁 Working Dir: .../services/mineru-mlx
📂 Logs: .../logs
════════════════════════════════════════════════════════════

INFO: Started server process [12345]
INFO: Waiting for application startup.
[2025-11-06 10:00:00] ℹ️ [INFO] ════════════════════════════════════════════════════════════
[2025-11-06 10:00:00] ℹ️ [INFO] 🚀 Starting mineru-mlx v2.0.0
[2025-11-06 10:00:00] ℹ️ [INFO] 📍 Port: 9006
[2025-11-06 10:00:00] ℹ️ [INFO] 🖥️  Platform: macOS 15.x on arm64
[2025-11-06 10:00:00] ℹ️ [INFO] 🔥 Backend: MinerU with Apple Metal GPU
[2025-11-06 10:00:00] ℹ️ [INFO] 📝 Log Level: INFO
[2025-11-06 10:00:00] ℹ️ [INFO] ════════════════════════════════════════════════════════════
[2025-11-06 10:00:00] ✅ [SUCCESS] Service ready to accept requests
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:9006
```

### Health Check

```bash
curl http://localhost:9006/health
```

**Expected Response**:

```json
{
  "status": "healthy",
  "service": "mineru-mlx",
  "version": "2.0.0",
  "port": 9006,
  "backend": "MinerU with Apple Metal GPU",
  "platform": "macOS 15.x on arm64",
  "timestamp": "2025-11-06T10:00:00.000000"
}
```

---

## 🧪 Testing the Refactoring

### Test 1: Service Health Check

```bash
curl http://localhost:9006/health
```

Verify response shows:
- `"status": "healthy"`
- `"port": 9006`
- `"service": "mineru-mlx"`

### Test 2: Direct PDF Processing

```bash
curl -X POST "http://localhost:9006/process" \
  -F "file=@/path/to/test.pdf" \
  -F "device=mps" \
  -F "lang=en"
```

Verify response includes:
- `"success": true`
- `"text": "...extracted text..."`
- `"metadata"` with page count, formulas, tables
- `"processing_time"` in seconds

### Test 3: Integration with Archon Backend

1. Start MinerU MLX service: `cd ~/Projects/archon/services/mineru-mlx && ./start_service.sh`
2. Start Archon services: `docker compose up -d`
3. Upload a PDF via Archon UI with MinerU processing enabled
4. Check Archon server logs: `docker compose logs archon-server | grep -i mineru`
5. Verify MinerU service is called and returns results

### Test 4: Side-by-Side with DeepSeek-OCR MLX

**Terminal 1** - Start MinerU MLX:
```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

**Terminal 2** - Start DeepSeek-OCR MLX:
```bash
cd ~/Projects/archon/services/deepseek-ocr-mlx
./start_service.sh
```

**Terminal 3** - Test both services:
```bash
# Test MinerU MLX (port 9006)
curl http://localhost:9006/health

# Test DeepSeek-OCR MLX (port 9005)
curl http://localhost:9005/health
```

Both should respond with healthy status on their respective ports.

---

## 📊 Architecture

### Service Flow

```
User Upload (Archon UI)
    ↓
Archon Backend API (/api/documents/upload)
    ↓
document_processing.py (extract_text_from_document)
    ↓
Use MinerU? → Yes → mineru_service.py
    ↓                           ↓
MINERU_SERVICE_URL set?    get_mineru_service()
    ↓                           ↓
    Yes                     MinerUHttpClient
    ↓                           ↓
HTTP Request                MinerU MLX Service (port 9006)
    ↓                           ↓
FastAPI app.py              MinerU doc_analyze()
    ↓                           ↓
Apple Metal GPU             Extracted Text + Images
    ↓                           ↓
Response                    Stored in Supabase
```

### Integration Points

1. **Environment Configuration** (`.env`)
   - `MINERU_SERVICE_URL` - Service URL (http://host.docker.internal:9006)

2. **Service Discovery** (`python/src/server/services/mineru_service.py`)
   - `get_mineru_service()` - Returns HTTP client when URL is set
   - Automatic fallback to local CLI if URL not configured

3. **HTTP Client** (`python/src/server/services/mineru_http_client.py`)
   - `MinerUHttpClient` - Calls native service via HTTP
   - Handles timeouts, errors, and response transformation

---

## 🔧 Configuration Options

### Service URL

**For Docker Containers** (recommended):
```bash
MINERU_SERVICE_URL=http://host.docker.internal:9006
```

**For Local Development** (backend running on host):
```bash
MINERU_SERVICE_URL=http://localhost:9006
```

### Processing Options

Available in API calls:
- **device**: "mps" (Apple GPU) or "cpu"
- **lang**: Language code (e.g., "en", "zh")
- **extract_charts**: Boolean - Extract chart data from images
- **chart_provider**: "auto", "local", "claude", etc.

---

## 🎯 Improvements Over Previous Implementation

### What Changed

| Aspect | Old (Port 8055) | New (Port 9006) |
|--------|----------------|-----------------|
| **Location** | `python/src/mineru_service/` | `services/mineru-mlx/` |
| **Port** | 8055 (inconsistent) | 9006 (OCR range) |
| **Logging** | Basic print statements | Enhanced with timestamps & emojis |
| **Health Checks** | Simple JSON | Comprehensive metadata |
| **Error Handling** | Basic try/catch | Detailed with processing time |
| **Startup Script** | Minimal | Full venv management & checks |
| **Documentation** | Limited comments | Extensive inline docs |
| **Pattern** | Standalone | Matches DeepSeek-OCR MLX |

### Benefits of Refactoring

1. **Port Consistency** - Now in OCR services range (9000-9099)
2. **Pattern Consistency** - Matches DeepSeek-OCR MLX architecture
3. **Better Monitoring** - Enhanced logging and health checks
4. **Easier Testing** - Side-by-side testing with DeepSeek-OCR MLX
5. **Improved Maintainability** - Clear structure and documentation
6. **Better Developer Experience** - Interactive startup script with helpful prompts

---

## 📁 File Structure

```
~/Projects/archon/
├── services/
│   ├── deepseek-ocr-mlx/          # Port 9005
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── start_service.sh
│   │   └── logs/
│   └── mineru-mlx/                 # Port 9006 (NEW)
│       ├── app.py                  # Enhanced FastAPI app
│       ├── requirements.txt        # Comprehensive dependencies
│       ├── start_service.sh        # Enhanced startup script
│       └── logs/                   # Log directory
├── python/
│   └── src/
│       └── server/
│           └── services/
│               ├── mineru_service.py         # Service discovery
│               └── mineru_http_client.py     # HTTP client
├── .env                            # Updated with port 9006
├── .env.example                    # Updated with MinerU MLX section
├── PORT_MAPPING.md                 # Updated port documentation
├── MINERU_MLX_REFACTORING_PLAN.md  # Refactoring plan
└── MINERU_MLX_REFACTORING_COMPLETE.md  # This file
```

### Old Files (Preserved for Fallback)

```
~/Projects/archon/python/src/mineru_service/
├── main.py                         # Original service on port 8055
└── __init__.py
```

**Note**: The old MinerU service code is preserved for backward compatibility and fallback scenarios.

---

## 🐛 Troubleshooting

### Issue 1: Port Already in Use

**Symptom**: `Address already in use: 9006`

**Solution**:
```bash
# Check what's using the port
lsof -i :9006

# Kill the process
kill -9 $(lsof -t -i :9006)

# Or let the startup script handle it (it will prompt)
./start_service.sh
```

### Issue 2: Dependencies Not Installed

**Symptom**: `ModuleNotFoundError: No module named 'magic_pdf'`

**Solution**:
```bash
cd ~/Projects/archon/services/mineru-mlx
source venv/bin/activate
pip install -r requirements.txt
```

### Issue 3: Backend Can't Connect

**Symptom**: `MinerU service unavailable at http://host.docker.internal:9006`

**Check**:
1. Is the service running? `curl http://localhost:9006/health`
2. Is the URL correct in `.env`? Check `MINERU_SERVICE_URL`
3. Using correct host for Docker? Use `host.docker.internal` not `localhost`

### Issue 4: Old Service Still Running

**Symptom**: Service responds on port 8055 but not 9006

**Solution**:
```bash
# Stop old service
lsof -i :8055
kill -9 $(lsof -t -i :8055)

# Start new service
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

---

## 📝 Next Steps

### Immediate Actions

1. **Test the Service**
   ```bash
   cd ~/Projects/archon/services/mineru-mlx
   ./start_service.sh
   ```

2. **Verify Health Check**
   ```bash
   curl http://localhost:9006/health
   ```

3. **Test PDF Processing**
   - Upload a PDF via Archon UI
   - Check logs to verify new service is being used
   - Compare results with previous implementation

### Optional Enhancements

1. **Add to System Startup** (launchd on macOS)
   - Create launch agent for automatic start
   - Configure to start on boot

2. **Add Monitoring**
   - Health check monitoring
   - Processing time metrics tracking
   - Alert on service failure

3. **Performance Benchmarking**
   - Compare processing times with old service
   - Test with various PDF sizes and complexities
   - Measure Metal GPU utilization

---

## ✅ Completion Checklist

- [x] Phase 1: Service reorganization
  - [x] Create services/mineru-mlx directory
  - [x] Create enhanced app.py with port 9006
  - [x] Create comprehensive requirements.txt
  - [x] Create enhanced start_service.sh script
  - [x] Make startup script executable

- [x] Phase 2: Backend integration
  - [x] Verify service discovery works with new URL
  - [x] Confirm HTTP client supports new port

- [x] Phase 3: Environment configuration
  - [x] Update .env with port 9006
  - [x] Update .env.example with MinerU MLX section
  - [x] Add clear documentation and startup instructions

- [x] Phase 4: Documentation
  - [x] Update PORT_MAPPING.md service entry
  - [x] Update port allocation strategy
  - [x] Update environment variables section
  - [x] Add health check URL

- [ ] Phase 5: Testing (Ready to start)
  - [ ] Service startup test
  - [ ] Health check verification
  - [ ] Single PDF processing test
  - [ ] Integration test with Archon backend
  - [ ] Side-by-side test with DeepSeek-OCR MLX

---

## 🏁 Summary

**Status**: ✅ **REFACTORING COMPLETE - READY FOR TESTING**

The MinerU MLX service refactoring is complete! All implementation phases are done:

- ✅ Service reorganized from `python/src/mineru_service/` to `services/mineru-mlx/`
- ✅ Port changed from 8055 to 9006 for consistency
- ✅ Enhanced startup script with venv management
- ✅ Improved logging and monitoring
- ✅ Environment configuration updated
- ✅ Documentation updated

**Next Action**: Start the service and run tests!

```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

Then test the health endpoint:
```bash
curl http://localhost:9006/health
```

**Estimated Time to Validation**: 5-10 minutes of testing
**Pattern Consistency**: ✅ Matches DeepSeek-OCR MLX architecture
**GPU Acceleration**: ✅ Full Apple Metal support via MinerU

---

## 🤝 Comparison with DeepSeek-OCR MLX

Both services now follow the same pattern:

| Aspect | DeepSeek-OCR MLX | MinerU MLX |
|--------|------------------|------------|
| **Port** | 9005 | 9006 |
| **Location** | `services/deepseek-ocr-mlx/` | `services/mineru-mlx/` |
| **GPU Backend** | MLX-VLM | MinerU (Magic-PDF) |
| **Startup Script** | Enhanced with venv | Enhanced with venv |
| **Health Checks** | Comprehensive | Comprehensive |
| **Logging** | Timestamps + emojis | Timestamps + emojis |
| **Use Case** | Vision-language OCR | PDF formulas & tables |

---

**Refactoring Date**: 2025-11-06
**Platform**: Mac M4 Studio with Apple Silicon
**Old Port**: 8055
**New Port**: 9006
**Service Type**: Native Mac Service (FastAPI + MinerU)
**Status**: ✅ Complete and Ready for Testing
