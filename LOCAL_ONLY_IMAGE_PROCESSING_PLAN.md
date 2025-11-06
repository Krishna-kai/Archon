# Local-Only Image Processing Plan

**Date:** 2025-11-06
**Goal:** End-to-end image content extraction using ONLY local services
**Cost:** $0 (completely free, runs on your hardware)

---

## Available Local Services ✅

### 1. Ollama (Primary - All-in-One Vision)
**Port:** 11434
**Model:** llama3.2-vision:11b (Meta's vision model)
**Status:** ✅ Running and healthy

**Capabilities:**
- Image classification (chart, diagram, table, formula, photo)
- OCR text extraction from images
- Structured chart data extraction
- Multi-modal understanding (text + image)

**Performance:**
- Speed: 2-5 seconds per image (Apple M4 GPU)
- Accuracy: Good for technical content
- Cost: FREE

### 2. Docling OCR (Backup OCR)
**Port:** 9000
**Backend:** pypdfium2
**Status:** ✅ Running and healthy

**Capabilities:**
- Fast document layout analysis
- Text extraction from PDFs
- Table detection

### 3. OCRmyPDF (Backup OCR)
**Port:** 9002
**Backend:** Tesseract
**Status:** ✅ Running and healthy

**Capabilities:**
- High-accuracy OCR
- Multi-language support
- PDF optimization

### 4. LaTeX OCR (Formula Extraction)
**Port:** 9001
**Status:** ✅ Running and healthy

**Capabilities:**
- Mathematical formula recognition
- LaTeX output
- Specialized for equations

---

## Local-Only Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     PHASE 1: UPLOAD (DONE ✅)                    │
│  PDF → MinerU → Extract Images → Store in Supabase Storage      │
│                                  ↓                               │
│                          Create DB Records                       │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 2: CONTENT EXTRACTION (NEW)                │
│                                                                   │
│  For each stored image:                                          │
│                                                                   │
│  1. Retrieve image from Supabase Storage                         │
│     ↓                                                             │
│  2. Send to Ollama Vision Model                                  │
│     ↓                                                             │
│  3. Parallel Processing:                                         │
│     ├── Extract OCR text                                         │
│     ├── Classify image type                                      │
│     └── Extract structured data (if chart/table)                 │
│     ↓                                                             │
│  4. Get surrounding text from document                           │
│     ↓                                                             │
│  5. Generate embedding (Ollama nomic-embed-text)                 │
│     ↓                                                             │
│  6. Update database record                                       │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 3: SEARCH & RETRIEVAL                     │
│                                                                   │
│  Query → Semantic Search (embeddings) → Results                  │
│       → Full-text Search (OCR) → Results                         │
│       → Metadata Filter (type) → Results                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Strategy

### Option 1: Synchronous Processing (Testing)
**Best for:** Initial testing and validation

```python
async def process_image_local_sync(image_id: UUID):
    """Process single image synchronously"""
    # 1. Get image from DB
    image_record = await get_image_record(image_id)

    # 2. Download from Supabase Storage
    image_bytes = await download_image(image_record['storage_path'])

    # 3. Process with Ollama
    result = await process_with_ollama(image_bytes)

    # 4. Update database
    await update_image_content(
        image_id=image_id,
        ocr_text=result['ocr_text'],
        image_type=result['type'],
        metadata=result['structured_data'],
        embedding=result['embedding']
    )
```

**Timeline:** Process one image, verify, repeat
**Speed:** ~5 seconds per image (sequential)

### Option 2: Background Job Queue (Production)
**Best for:** Real deployment

```python
async def queue_image_processing(source_id: str):
    """Queue all images for a document"""
    images = await get_images_by_source(source_id)

    for image in images:
        await job_queue.enqueue(
            process_image_local_sync,
            image_id=image['id']
        )
```

**Timeline:** All images processed in background
**Speed:** ~5 seconds per image (parallel across images)

---

## Ollama Vision Integration

### Prompt Engineering for Image Analysis

#### Task 1: OCR + Classification
```python
PROMPT_OCR_CLASSIFY = """
Analyze this image from a technical/scientific document.

Tasks:
1. Extract all visible text (OCR)
2. Classify the image type
3. Identify key elements

Return JSON format:
{
  "ocr_text": "all extracted text...",
  "image_type": "chart|diagram|table|formula|photo|flowchart|circuit",
  "subtype": "bar_chart|line_plot|system_diagram|etc",
  "confidence": 0.95,
  "key_elements": ["element1", "element2"],
  "technical_domain": "machine_learning|circuits|biology|etc"
}
"""
```

#### Task 2: Chart Data Extraction
```python
PROMPT_CHART_EXTRACTION = """
This is a {chart_type} from a technical paper.

Extract structured data:
{
  "chart_type": "line|bar|scatter|pie",
  "axes": {
    "x": {"label": "...", "unit": "...", "range": [min, max]},
    "y": {"label": "...", "unit": "...", "range": [min, max]}
  },
  "series": [
    {
      "name": "...",
      "data_points": [[x1, y1], [x2, y2], ...]
    }
  ],
  "legend": [...],
  "caption": "...",
  "key_findings": "..."
}
"""
```

---

## Service Implementation

### New Service: `ImageContentProcessor`

**File:** `python/src/server/services/image_content_processor.py`

```python
"""
Local-only image content processing service.
Uses Ollama for all vision tasks (OCR, classification, chart extraction).
"""

import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from ..services.storage import get_image_storage_service
from ..services.embedding_service import get_embedding_service
from ..config.database import get_supabase_client

logger = logging.getLogger(__name__)


class ImageContentProcessor:
    """Process image content using local-only services"""

    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        self.vision_model = "llama3.2-vision:11b"
        self.embed_model = "nomic-embed-text"
        self.timeout = 120.0

        self.image_storage = get_image_storage_service()
        self.embedding_service = get_embedding_service()
        self.supabase = get_supabase_client()

    async def process_image_content(
        self,
        image_id: UUID,
        force_refresh: bool = False
    ) -> Dict:
        """
        Complete local processing pipeline for a single image.

        Args:
            image_id: UUID of image to process
            force_refresh: Re-process even if already processed

        Returns:
            Processing results with all extracted content
        """

        # 1. Check if already processed
        if not force_refresh:
            record = await self._get_image_record(image_id)
            if record.get('ocr_processed') and record.get('embedding_generated'):
                logger.info(f"Image {image_id} already processed, skipping")
                return {"status": "already_processed", "record": record}

        # 2. Get image data
        image_data = await self._fetch_image_data(image_id)

        # 3. Extract content with Ollama
        ocr_classification = await self._extract_ocr_and_classify(
            image_data['base64']
        )

        # 4. Extract structured data if applicable
        structured_data = None
        if ocr_classification['image_type'] in ['chart', 'table', 'diagram']:
            structured_data = await self._extract_structured_data(
                image_data['base64'],
                ocr_classification
            )

        # 5. Get surrounding text (context from document)
        surrounding_text = await self._get_surrounding_text(
            image_data['source_id'],
            image_data['page_number']
        )

        # 6. Generate embedding
        content_for_embedding = self._prepare_content_for_embedding(
            ocr_classification['ocr_text'],
            surrounding_text,
            structured_data
        )

        embedding = await self._generate_embedding_local(content_for_embedding)

        # 7. Update database
        await self._update_image_record(
            image_id=image_id,
            ocr_text=ocr_classification['ocr_text'],
            image_type=ocr_classification['image_type'],
            surrounding_text=surrounding_text,
            metadata={
                'classification': ocr_classification,
                'structured_data': structured_data
            },
            embedding=embedding
        )

        logger.info(f"Successfully processed image {image_id}")

        return {
            "status": "success",
            "image_id": str(image_id),
            "ocr_length": len(ocr_classification['ocr_text']),
            "image_type": ocr_classification['image_type'],
            "has_structured_data": structured_data is not None,
            "embedding_generated": True
        }

    async def _extract_ocr_and_classify(
        self,
        image_base64: str
    ) -> Dict:
        """
        Use Ollama vision model to extract text and classify image.

        Returns:
            {
                "ocr_text": str,
                "image_type": str,
                "subtype": str,
                "confidence": float,
                "key_elements": List[str],
                "technical_domain": str
            }
        """

        prompt = """
Analyze this image from a technical/scientific document.

Tasks:
1. Extract ALL visible text using OCR (be thorough)
2. Classify the image type
3. Identify key elements and domain

Return ONLY valid JSON (no markdown, no explanation):
{
  "ocr_text": "complete extracted text",
  "image_type": "chart|diagram|table|formula|photo|flowchart|circuit|screenshot",
  "subtype": "specific type like bar_chart, system_diagram, etc",
  "confidence": 0.95,
  "key_elements": ["list", "of", "key", "elements"],
  "technical_domain": "machine_learning|circuits|biology|mathematics|etc"
}
"""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "format": "json"
                }
            )

            result = response.json()
            content = json.loads(result['response'])

            return content

    async def _extract_structured_data(
        self,
        image_base64: str,
        classification: Dict
    ) -> Optional[Dict]:
        """
        Extract structured data from charts/tables using Ollama.
        """

        image_type = classification['image_type']

        if image_type == 'chart':
            prompt = f"""
This is a {classification.get('subtype', 'chart')} from a technical paper.

Extract the chart data in structured format.

Return ONLY valid JSON:
{{
  "chart_type": "line|bar|scatter|pie|heatmap",
  "axes": {{
    "x": {{"label": "...", "unit": "...", "range": [min, max]}},
    "y": {{"label": "...", "unit": "...", "range": [min, max]}}
  }},
  "series": [
    {{
      "name": "series name",
      "data_points": [[x1, y1], [x2, y2]]
    }}
  ],
  "legend": ["item1", "item2"],
  "caption": "extracted caption text",
  "key_finding": "main takeaway from the chart"
}}
"""

        elif image_type == 'table':
            prompt = """
Extract the table data in structured format.

Return ONLY valid JSON:
{
  "headers": ["col1", "col2", "col3"],
  "rows": [
    ["val1", "val2", "val3"],
    ["val4", "val5", "val6"]
  ],
  "caption": "table caption",
  "notes": "any footnotes or notes"
}
"""

        else:
            return None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "format": "json"
                }
            )

            result = response.json()
            content = json.loads(result['response'])

            return content

    async def _generate_embedding_local(self, text: str) -> List[float]:
        """
        Generate embedding using local Ollama model.
        """

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.embed_model,
                    "prompt": text
                }
            )

            result = response.json()
            return result['embedding']

    # ... helper methods for DB operations
```

---

## API Endpoints

### 1. Process Single Image
```http
POST /api/documents/images/{image_id}/process
{
  "force_refresh": false
}
```

**Response:**
```json
{
  "status": "success",
  "image_id": "uuid",
  "ocr_text": "extracted text...",
  "image_type": "chart",
  "processing_time": 4.2
}
```

### 2. Process All Images for Document
```http
POST /api/documents/{source_id}/process-images
{
  "force_refresh": false
}
```

**Response:**
```json
{
  "status": "processing",
  "source_id": "source_123",
  "total_images": 15,
  "processed": 0,
  "progress_id": "uuid"
}
```

### 3. Get Image Content
```http
GET /api/documents/images/{image_id}/content
```

**Response:**
```json
{
  "image_id": "uuid",
  "image_url": "signed_url",
  "content": {
    "ocr_text": "...",
    "image_type": "chart",
    "structured_data": {...},
    "surrounding_text": "..."
  },
  "processing_status": {
    "ocr_processed": true,
    "embedding_generated": true,
    "processed_at": "2025-11-06T13:30:00Z"
  }
}
```

---

## Testing Strategy

### Phase 1: Single Image Test (30 minutes)
1. Create test script
2. Upload sample image to Supabase
3. Run processing pipeline
4. Verify results in database
5. Validate OCR accuracy

### Phase 2: Multi-Image Test (1 hour)
1. Upload PDF with 5-10 images
2. Process all images
3. Verify consistency
4. Test search functionality

### Phase 3: Performance Test (1 hour)
1. Upload PDF with 50+ images
2. Measure processing time
3. Check resource usage
4. Optimize if needed

### Phase 4: Accuracy Test (2 hours)
1. Test with various image types:
   - Bar charts
   - Line plots
   - Tables
   - Diagrams
   - Formulas
2. Validate OCR accuracy
3. Validate classification accuracy
4. Validate structured data extraction

---

## Performance Expectations

### Apple M4 GPU (Your Hardware)

**Single Image:**
- OCR + Classification: 2-3 seconds
- Structured data extraction: 3-5 seconds
- Embedding generation: 0.5 seconds
- **Total: 5-8 seconds per image**

**Document Processing:**
- 10 images: ~1 minute (sequential) or ~10 seconds (parallel)
- 50 images: ~5 minutes (sequential) or ~30 seconds (parallel)
- 100 images: ~10 minutes (sequential) or ~60 seconds (parallel)

---

## Next Steps

### Step 1: Create Test Script (Now)
- Write Python script to test Ollama vision
- Test OCR extraction
- Test classification
- Test structured data extraction

### Step 2: Implement Service (1-2 hours)
- Create `ImageContentProcessor` service
- Add API endpoints
- Connect to existing services

### Step 3: End-to-End Test (30 minutes)
- Upload sample PDF
- Process images
- Query content
- Verify results

### Step 4: Production Integration (1 hour)
- Add background job queue
- Add progress tracking
- Add error handling
- Add retry logic

---

## Cost Analysis

**Local-Only Pipeline:**
- Hardware: Your Mac M4 (already owned)
- Electricity: ~$0.01 per hour of processing
- Software: All open source (FREE)
- API calls: ZERO

**Total Cost: Effectively $0**

**vs Cloud Pipeline:**
- Claude Vision: $0.01 per image
- OpenAI Vision: $0.01 per image
- 100 images = $1.00

**Savings: 100% cost reduction** 🎉

---

## Limitations & Considerations

### Local-Only Constraints:
1. **Accuracy:** Lower than Claude/GPT-4 Vision (but still good)
2. **Speed:** Slower than cloud APIs (but acceptable)
3. **Hardware:** Requires good GPU (you have M4 ✅)
4. **Offline:** Cannot process when Mac is off/sleeping

### Mitigation Strategies:
1. **Quality:** Test and validate on your specific document types
2. **Speed:** Use parallel processing
3. **Availability:** Add cloud fallback for critical cases
4. **Reliability:** Implement retry logic and error handling

---

## Decision Point

**Do you want to:**

**Option A:** Implement the full service now (2-3 hours)
- Complete ImageContentProcessor
- Add API endpoints
- End-to-end integration

**Option B:** Start with test script first (30 minutes)
- Validate Ollama accuracy on sample images
- Test different image types
- Confirm acceptable quality
- Then decide on full implementation

**Option C:** Create minimal working prototype (1 hour)
- Simple script to process one image
- Manual testing
- Prove the concept works
- Iterate from there

**My Recommendation:** Start with **Option B** - validate quality first, then commit to full implementation.

Shall I create a test script to validate Ollama's performance on your technical documents?
