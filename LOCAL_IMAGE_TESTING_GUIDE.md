# Local Image Processing - Testing Guide

**Date:** 2025-11-06
**Status:** Ready for Testing
**Cost:** $0 (100% Local)

---

## What We've Built

✅ **Phase 1 Complete:** Image storage pipeline (images extracted and stored)
✅ **Local Services Verified:** Ollama + OCR services running
✅ **Test Script Created:** End-to-end local processing validation

---

## Quick Start - Test Now!

### Step 1: Test Script with Sample Image

```bash
cd /Users/krishna/Projects/archon/python

# Test with any image (chart, diagram, table from a paper)
uv run python scripts/test_local_image_processing.py /path/to/your/image.png
```

**What it does:**
1. Checks Ollama is running and models are available
2. Loads your image
3. Extracts OCR text using Ollama vision
4. Classifies image type (chart, diagram, table, etc.)
5. Extracts structured data (for charts/tables)
6. Generates vector embedding
7. Prints detailed results

**Expected Output:**
```
======================================================================
🖼️  PROCESSING IMAGE: /path/to/image.png
======================================================================

✅ Ollama is running
   Vision model (llama3.2-vision:11b): ✅
   Embed model (nomic-embed-text): ✅

📁 Loading image: /path/to/image.png
✅ Image loaded (145.3 KB)

📊 Extracting OCR and classifying image...
   Model: llama3.2-vision:11b
   Prompt length: 523 chars
✅ OCR and classification complete

📋 CLASSIFICATION RESULTS:
   Type: chart (bar_chart)
   Confidence: 95.00%
   Domain: machine_learning
   Key Elements: accuracy, epochs, training, validation

📝 OCR TEXT:
   Length: 287 characters
   Preview: Training and Validation Accuracy
            Epochs: 0-100
            Accuracy (%): 0-100
            Legend: Training (blue), Validation (orange)...

🔍 Extracting structured data from chart...
✅ Structured data extraction complete

📊 STRUCTURED DATA:
{
  "chart_type": "line",
  "axes": {
    "x": {"label": "Epochs", "unit": "", "range": [0, 100]},
    "y": {"label": "Accuracy", "unit": "%", "range": [0, 100]}
  },
  "series": [
    {"name": "Training", "data_points": [[0, 45], [25, 67], ...]}
  ],
  ...
}

🧮 Generating embedding for text (450 chars)...
✅ Generated embedding (dimension: 768)

======================================================================
✅ PROCESSING COMPLETE
======================================================================
   OCR Text: 287 chars
   Image Type: chart
   Structured Data: Yes
   Embedding: Generated
======================================================================
```

---

## Testing Different Image Types

### Test 1: Bar Chart
```bash
# Find a bar chart image from an IEEE paper
uv run python scripts/test_local_image_processing.py ~/Downloads/bar_chart.png
```

**Expected:** OCR text + chart data extraction + classification

### Test 2: Table
```bash
# Find a table image
uv run python scripts/test_local_image_processing.py ~/Downloads/table.png
```

**Expected:** OCR text + table data (headers + rows) + classification

### Test 3: Diagram
```bash
# Find a system diagram or flowchart
uv run python scripts/test_local_image_processing.py ~/Downloads/diagram.png
```

**Expected:** OCR text + component identification + classification

### Test 4: Mathematical Formula
```bash
# Find an equation/formula image
uv run python scripts/test_local_image_processing.py ~/Downloads/formula.png
```

**Expected:** OCR text + LaTeX-like representation + classification

---

## Evaluating Results

### Good Results ✅
- OCR text is accurate and readable
- Image type classification is correct
- Confidence > 80%
- Structured data (for charts) captures key information
- Embedding generated successfully

### Issues to Watch For ⚠️
- OCR misses small text
- Classification incorrect
- Structured data incomplete
- Processing time > 10 seconds

### Known Limitations
- Ollama is slower than cloud APIs (2-5 sec vs 1 sec)
- Accuracy lower than Claude Vision (~85% vs 95%)
- Complex charts may have incomplete data extraction
- Small text may be missed

---

## Performance Benchmarks

### Expected Timing (Apple M4)
- Image load: < 0.1 sec
- OCR + Classification: 2-3 sec
- Structured extraction: 3-5 sec
- Embedding: 0.5 sec
- **Total: 5-8 seconds per image**

### Resource Usage
- CPU: 50-80% (during processing)
- RAM: ~2GB (Ollama model)
- GPU: Utilized (M4 Metal acceleration)

---

## Next Steps After Testing

### If Results are Good ✅

**Option A: Implement Full Service (2-3 hours)**

Create production-ready service:
- `ImageContentProcessor` service class
- API endpoints for processing
- Background job queue
- Database integration

**Implementation:**
```python
# Services to create
1. python/src/server/services/image_content_processor.py
2. python/src/server/api_routes/image_processing_api.py

# API endpoints
POST /api/documents/images/{image_id}/process
POST /api/documents/{source_id}/process-images
GET  /api/documents/images/{image_id}/content
POST /api/documents/images/search
```

**Option B: Quick Integration (1 hour)**

Add processing to existing upload flow:
```python
# Modify: python/src/server/api_routes/knowledge_api.py
# After storing images (line ~1097), add:

if extracted_images:
    # Queue processing jobs
    for img in extracted_images:
        await queue_image_processing(
            image_id=img['id'],
            image_data=img['base64']
        )
```

### If Results Need Improvement ⚠️

**Option C: Hybrid Approach**

Use Ollama for basic cases, Claude for complex:
```python
# Try local first
result = await process_with_ollama(image)

if result['confidence'] < 0.8:
    # Fallback to Claude for accuracy
    result = await process_with_claude(image)
```

**Option D: Optimize Prompts**

Improve Ollama accuracy with better prompts:
- More specific instructions
- Examples in prompt
- Structured output format
- Multiple attempts if needed

---

## Integration Plan

### Phase 2A: Basic Content Extraction (Now)
```
Stored Image → Process with Ollama → Update DB
             ↓
             - OCR text
             - Image type
             - Embedding
```

### Phase 2B: Search Integration (Later)
```
User Query → Search embeddings → Return images with content
          ↓
          - Semantic search
          - Full-text search
          - Metadata filters
```

### Phase 2C: RAG Enhancement (Future)
```
RAG Query → Search text AND images → Combined results
         ↓
         - Multi-modal retrieval
         - Image-aware answers
         - Visual context
```

---

## Troubleshooting

### Issue: "Ollama is not available"

**Solutions:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve

# Check if vision model is installed
ollama list | grep llama3.2-vision

# Pull vision model if missing
ollama pull llama3.2-vision:11b
```

### Issue: "Model not found"

**Solutions:**
```bash
# Pull required models
ollama pull llama3.2-vision:11b
ollama pull nomic-embed-text
```

### Issue: "Timeout during processing"

**Solutions:**
- Increase timeout in test script
- Check GPU availability
- Reduce image size
- Close other applications

### Issue: "Invalid JSON response"

**Solutions:**
- Ollama sometimes adds markdown
- Script has fallback JSON parser
- Try re-running (Ollama can be inconsistent)

---

## Cost-Benefit Analysis

### Local Processing (Current)
**Pros:**
- ✅ $0 cost
- ✅ Complete privacy
- ✅ No rate limits
- ✅ Offline capable
- ✅ Fast iteration

**Cons:**
- ⚠️ Slower (5-8 sec vs 1-2 sec)
- ⚠️ Lower accuracy (85% vs 95%)
- ⚠️ Requires local resources
- ⚠️ Not available when Mac is off

### Cloud Processing (Alternative)
**Pros:**
- ✅ Faster (1-2 sec)
- ✅ Higher accuracy (95%+)
- ✅ Always available
- ✅ No local resources

**Cons:**
- ❌ Cost (~$0.01 per image)
- ❌ Privacy concerns
- ❌ Rate limits
- ❌ Requires internet

### Hybrid (Best of Both)
**Pros:**
- ✅ Low cost (most images local)
- ✅ High accuracy (fallback to cloud)
- ✅ Flexible
- ✅ Best user experience

**Cons:**
- ⚠️ More complex
- ⚠️ Requires both systems

---

## Decision Matrix

### Use Local-Only If:
- ✅ You process 100+ images regularly (saves $$)
- ✅ Privacy is important
- ✅ You have good hardware (M4 Mac)
- ✅ 85% accuracy is acceptable
- ✅ 5-8 seconds per image is OK

### Add Cloud Fallback If:
- ⚠️ You need 95%+ accuracy
- ⚠️ Complex charts/diagrams are common
- ⚠️ Processing < 100 images/month
- ⚠️ Speed is critical (< 2 sec)

### Go Cloud-Only If:
- ❌ Limited local resources
- ❌ Need 99% accuracy
- ❌ Processing from multiple machines
- ❌ Budget allows ($1 per 100 images)

---

## Testing Checklist

### Pre-Test ✅
- [ ] Ollama is running
- [ ] Vision model installed
- [ ] Embed model installed
- [ ] Test script is executable
- [ ] Sample images ready

### During Test 📝
- [ ] Test bar chart
- [ ] Test line plot
- [ ] Test table
- [ ] Test diagram
- [ ] Test formula
- [ ] Measure processing time
- [ ] Check OCR accuracy
- [ ] Verify classification
- [ ] Validate structured data

### Post-Test 📊
- [ ] Document accuracy rate
- [ ] Note processing times
- [ ] Identify failure cases
- [ ] Decide: local-only vs hybrid
- [ ] Plan integration approach

---

## Ready to Test!

**Run this command now:**
```bash
cd /Users/krishna/Projects/archon/python

# Test with your IEEE paper image
uv run python scripts/test_local_image_processing.py /path/to/your/chart.png
```

**Then:**
1. Review the results
2. Test with 3-5 different image types
3. Evaluate accuracy and speed
4. Decide on integration approach
5. Let me know what you want to implement next!

---

## Summary

**What's Working:**
- ✅ Images are extracted and stored (Phase 1)
- ✅ Local services are running (Ollama + OCR)
- ✅ Test script is ready
- ✅ End-to-end pipeline designed

**What's Next:**
- 🔬 Test with your actual images
- 📊 Evaluate results
- ⚙️ Implement full service (if approved)
- 🔍 Add search capabilities

**Total Investment So Far:** ~4 hours of planning + implementation
**Total Cost:** $0
**Next Steps:** 30 minutes of testing → decision on full implementation
