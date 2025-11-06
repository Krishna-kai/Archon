# Image Content Retrieval & Analysis Plan

**Date:** 2025-11-06
**Context:** Improving downstream analysis of PDF scanned content (IEEE papers, technical documents)
**Goal:** Enable comprehensive retrieval and analysis of image content, not just image files

---

## Current State Analysis

### What We Have ✅

1. **Image Storage Infrastructure**
   - ✅ Images stored in Supabase Storage (`document-images` bucket)
   - ✅ Metadata in `archon_document_images` table
   - ✅ Base64 image data from MinerU extraction
   - ✅ Page-level tracking (page_number, image_index)

2. **Database Schema Features**
   ```sql
   -- Content fields
   ocr_text TEXT                    -- Extracted text (currently NULL)
   image_type TEXT                  -- Classification (currently NULL)
   surrounding_text TEXT            -- Context (currently NULL)
   metadata JSONB                   -- Flexible storage (currently empty)

   -- Search capabilities
   embedding vector(768)            -- For semantic search (currently NULL)
   embedding_model TEXT             -- Tracking model used
   embedding_generated BOOLEAN      -- Processing status
   ```

3. **MinerU Capabilities**
   - Extracts images from PDFs with page numbers
   - Supports `extract_charts` flag
   - Returns base64-encoded images
   - Currently does NOT extract OCR text from images
   - Currently does NOT extract structured chart data

### What's Missing ❌

1. **OCR Text Extraction** - Images stored but no text extracted
2. **Chart Data Extraction** - No structured data from charts/diagrams
3. **Vector Embeddings** - No semantic search on image content
4. **Image Classification** - No type detection (chart, diagram, formula, table)
5. **Context Linking** - No surrounding text capture
6. **Content Retrieval API** - No way to query image content

---

## Image Content Types

For IEEE papers and technical documents, we need to handle:

### 1. **Charts & Graphs** 📊
**Content to Extract:**
- Chart type (bar, line, scatter, pie, etc.)
- Axis labels and units
- Data points and values
- Legends and labels
- Trends and patterns

**Use Cases:**
- "Find all bar charts showing performance comparisons"
- "Extract data points from Figure 3"
- "Compare trends across multiple papers"

### 2. **Diagrams & Flowcharts** 🔄
**Content to Extract:**
- Node labels and connections
- Process steps and flow
- Relationships and hierarchies
- Annotations and descriptions

**Use Cases:**
- "Find system architecture diagrams"
- "Extract workflow steps from Figure 2"
- "Understand data flow in the proposed system"

### 3. **Mathematical Formulas** 🧮
**Content to Extract:**
- LaTeX/MathML representation
- Variables and symbols
- Equation structure
- Surrounding explanations

**Use Cases:**
- "Find all equations related to neural networks"
- "Extract loss function definitions"
- "Search for specific mathematical relationships"

### 4. **Tables & Data** 📋
**Content to Extract:**
- Column headers and row labels
- Cell values (numeric and text)
- Table structure
- Captions and footnotes

**Use Cases:**
- "Extract benchmark results tables"
- "Compare performance metrics across papers"
- "Find datasets with specific characteristics"

### 5. **Circuit Diagrams & Technical Drawings** ⚡
**Content to Extract:**
- Component labels
- Connection patterns
- Technical specifications
- Annotations

**Use Cases:**
- "Find circuit implementations of amplifiers"
- "Extract component values from schematics"
- "Understand signal flow"

---

## Proposed Architecture for Image Content Retrieval

### Layer 1: Image Storage (DONE ✅)
```
PDF Upload → MinerU → Extract Images → Store in Supabase Storage
                                     ↓
                              Create DB Records
```

### Layer 2: Content Extraction (NEW 🆕)
```
Stored Image → OCR Service → Extract Text
            ↓
            → Vision AI → Classify Type
            ↓
            → Chart Parser → Extract Structured Data
            ↓
            → Context Extractor → Surrounding Text
            ↓
            → Update DB with Content
```

### Layer 3: Embedding Generation (NEW 🆕)
```
Extracted Content → Embedding Service → Generate Vectors
                                      ↓
                                Update DB with Embeddings
```

### Layer 4: Content Retrieval (NEW 🆕)
```
Query → Semantic Search (Embeddings) → Retrieve Images
     ↓
     → Structured Query (Metadata) → Filter Results
     ↓
     → Full-Text Search (OCR) → Match Text
     ↓
     → Return Image + Content + Context
```

---

## Implementation Options

### Option A: Sequential Processing (Recommended for MVP)

**Pros:**
- Simple implementation
- Clear error handling
- Easy to debug
- Incremental cost

**Cons:**
- Slower processing
- Blocks on errors

**Flow:**
1. Upload PDF → Extract images (MinerU)
2. Store images in Supabase
3. For each image:
   - Run OCR extraction
   - Classify image type
   - Extract structured data (if chart/table)
   - Generate embeddings
   - Update database

**Estimated Time:** 2-3 seconds per image

### Option B: Parallel Processing (Production)

**Pros:**
- Fast processing
- Efficient resource use
- Better user experience

**Cons:**
- Complex error handling
- Harder to debug
- Resource intensive

**Flow:**
1. Upload PDF → Extract images (MinerU)
2. Store images in Supabase
3. Queue background jobs for each image
4. Process in parallel:
   - OCR extraction
   - Type classification
   - Data extraction
   - Embedding generation
5. Update database as jobs complete

**Estimated Time:** 0.5-1 second per image (parallel)

### Option C: Lazy Loading (User-Triggered)

**Pros:**
- Zero upload cost
- Process only what's needed
- Pay-per-use model

**Cons:**
- Delayed content availability
- Complex caching
- User waits on first access

**Flow:**
1. Upload PDF → Extract and store images only
2. User requests image content → Trigger processing
3. Cache results for future requests

---

## Service Integration Requirements

### 1. OCR Services

**Current Options in Archon:**
- ✅ **DeepSeek OCR** - Already integrated (`src/server/services/ocr_deepseek.py`)
- ✅ **Tesseract** - Available via OCRmyPDF
- ✅ **Parser Service** - Document parsing (port 9004)

**Recommended:** DeepSeek OCR for high accuracy on technical content

**API Call:**
```python
from src.server.services.ocr_deepseek import extract_text_with_deepseek_ocr

ocr_text = await extract_text_with_deepseek_ocr(
    image_data_base64=image_base64,
    image_type="image/jpeg"
)
```

### 2. Vision AI for Classification

**Options:**
- **Claude Vision** (via API) - Best for technical content
- **GPT-4 Vision** - Good alternative
- **Open Source Models** - Lower cost, needs setup

**Recommended:** Claude Vision for accuracy on scientific images

**Sample Prompt:**
```
Analyze this image from a technical paper and classify it:
- Type: (chart, diagram, formula, table, photo, circuit, flowchart)
- Subtype: (bar chart, line plot, system diagram, etc.)
- Key elements: (describe main components)
- Technical domain: (ML, circuits, biology, etc.)
```

### 3. Chart Data Extraction

**Options:**
- **Claude Vision** with structured output
- **Specialized Chart Parsers** (PlotDigitizer, WebPlotDigitizer)
- **Custom Vision Models** (ChartQA, PlotQA)

**Recommended:** Claude Vision with JSON schema for structured data

**Sample Structured Output:**
```json
{
  "chart_type": "line_plot",
  "axes": {
    "x": {"label": "Epochs", "range": [0, 100]},
    "y": {"label": "Accuracy (%)", "range": [0, 100]}
  },
  "series": [
    {
      "name": "Training",
      "points": [[0, 45], [25, 67], [50, 82], [100, 95]]
    },
    {
      "name": "Validation",
      "points": [[0, 43], [25, 65], [50, 78], [100, 89]]
    }
  ],
  "legend": ["Training", "Validation"]
}
```

### 4. Embedding Generation

**Current:** Already integrated via `embedding_service.py`

**API Call:**
```python
from src.server.services.embedding_service import get_embedding_service

embedding_service = get_embedding_service()
embedding = await embedding_service.generate_embedding(ocr_text)
```

---

## Database Schema Enhancements

### Current Schema (Already Good!)
```sql
CREATE TABLE archon_document_images (
    id UUID PRIMARY KEY,
    source_id TEXT NOT NULL,
    page_number INTEGER,
    image_index INTEGER NOT NULL,

    -- Content (TO BE POPULATED)
    ocr_text TEXT,                -- OCR extracted text
    image_type TEXT,              -- Classification
    surrounding_text TEXT,        -- Context
    metadata JSONB,               -- Structured data

    -- Search (TO BE POPULATED)
    embedding vector(768),
    embedding_generated BOOLEAN DEFAULT FALSE,
    ocr_processed BOOLEAN DEFAULT FALSE
);
```

### Proposed Metadata Structure
```json
{
  "classification": {
    "primary_type": "chart",
    "subtype": "line_plot",
    "confidence": 0.95,
    "technical_domain": "machine_learning"
  },
  "chart_data": {
    "axes": {...},
    "series": [...],
    "legend": [...]
  },
  "formulas": [
    {"latex": "E = mc^2", "description": "..."}
  ],
  "bounding_box": {
    "x": 100, "y": 200, "width": 400, "height": 300
  },
  "caption": "Figure 3: Performance comparison...",
  "extracted_entities": ["accuracy", "epochs", "training", "validation"]
}
```

---

## API Design for Content Retrieval

### Endpoint 1: Get Image with Content
```http
GET /api/documents/{source_id}/images/{image_id}
```

**Response:**
```json
{
  "id": "uuid",
  "image_url": "signed_url",
  "page_number": 5,
  "image_type": "chart",

  "content": {
    "ocr_text": "Training Accuracy vs Epochs...",
    "structured_data": {
      "chart_type": "line_plot",
      "axes": {...},
      "data_points": [...]
    },
    "surrounding_text": "Figure 3 shows the training progress..."
  },

  "context": {
    "source_title": "Deep Learning Performance",
    "page_number": 5,
    "section": "Results and Analysis"
  }
}
```

### Endpoint 2: Search Images by Content
```http
POST /api/documents/images/search
{
  "query": "bar charts showing accuracy comparison",
  "image_types": ["chart"],
  "source_ids": ["source_123"],
  "min_similarity": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "image_id": "uuid",
      "similarity": 0.89,
      "image_url": "signed_url",
      "ocr_text": "...",
      "highlight": "accuracy comparison between models",
      "metadata": {...}
    }
  ],
  "total": 15,
  "page": 1
}
```

### Endpoint 3: Extract Chart Data
```http
POST /api/documents/images/{image_id}/extract-data
{
  "extraction_type": "chart_data",
  "force_refresh": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "chart_type": "bar_chart",
    "categories": ["Model A", "Model B", "Model C"],
    "series": [
      {"name": "Accuracy", "values": [0.85, 0.91, 0.88]},
      {"name": "F1-Score", "values": [0.82, 0.89, 0.86]}
    ]
  },
  "raw_ocr": "...",
  "confidence": 0.92
}
```

---

## Processing Pipeline Design

### Background Job: Process Image Content

```python
async def process_image_content(
    image_id: UUID,
    image_base64: str,
    source_id: str,
    page_number: int
):
    """
    Complete content extraction pipeline for a single image.

    Steps:
    1. OCR text extraction
    2. Image classification
    3. Structured data extraction (if applicable)
    4. Context gathering (surrounding text)
    5. Embedding generation
    6. Database update
    """

    # Step 1: OCR Extraction
    ocr_text = await extract_ocr_text(image_base64)

    # Step 2: Classification
    classification = await classify_image(image_base64, ocr_text)

    # Step 3: Structured Data (conditional)
    structured_data = None
    if classification["primary_type"] in ["chart", "table", "diagram"]:
        structured_data = await extract_structured_data(
            image_base64,
            classification["primary_type"]
        )

    # Step 4: Context Gathering
    surrounding_text = await get_surrounding_text(source_id, page_number)

    # Step 5: Embedding Generation
    content_for_embedding = f"{ocr_text}\n{surrounding_text}"
    embedding = await generate_embedding(content_for_embedding)

    # Step 6: Update Database
    await update_image_content(
        image_id=image_id,
        ocr_text=ocr_text,
        image_type=classification["primary_type"],
        surrounding_text=surrounding_text,
        metadata={
            "classification": classification,
            "structured_data": structured_data
        },
        embedding=embedding,
        ocr_processed=True,
        embedding_generated=True
    )
```

---

## Cost & Performance Analysis

### Per-Image Processing Cost

**OCR (DeepSeek):**
- Cost: ~$0.0001 per image
- Time: 0.5-1 second

**Vision AI (Claude Vision):**
- Cost: ~$0.01 per image
- Time: 1-2 seconds

**Embedding (OpenAI):**
- Cost: ~$0.00001 per image
- Time: 0.2 seconds

**Total per Image:**
- Cost: ~$0.01
- Time: 2-4 seconds

**For 100-image document:**
- Cost: ~$1.00
- Time: 3-7 minutes (sequential) or 30-60 seconds (parallel)

### Storage Cost

**Supabase Storage:**
- Images: ~1MB per page = $0.02/GB/month
- Embeddings: ~3KB per image = negligible

---

## Implementation Phases

### Phase 2A: OCR & Basic Search (2-3 days)
**Priority:** HIGH

**Deliverables:**
1. OCR text extraction for all images
2. Vector embedding generation
3. Basic content search API
4. Update image storage to populate `ocr_text` and `embedding`

**Value:** Enable text-based image search immediately

### Phase 2B: Classification & Metadata (2-3 days)
**Priority:** MEDIUM

**Deliverables:**
1. Vision AI classification
2. Populate `image_type` field
3. Basic metadata extraction
4. Filter images by type

**Value:** Enable targeted search (find all charts, diagrams, etc.)

### Phase 2C: Structured Data Extraction (4-5 days)
**Priority:** MEDIUM-LOW

**Deliverables:**
1. Chart data extraction
2. Table data extraction
3. Formula parsing (LaTeX)
4. Structured metadata API

**Value:** Enable data analysis and comparison across documents

### Phase 2D: Context & RAG Integration (3-4 days)
**Priority:** HIGH

**Deliverables:**
1. Surrounding text extraction
2. Image-text linking
3. RAG queries including image content
4. Multi-modal search (text + images)

**Value:** Complete context for image understanding

---

## Recommended Next Steps

### Immediate Action (Next Session)

**Option 1: MVP - OCR + Search (Fastest Value)**
1. Implement OCR extraction for stored images
2. Generate embeddings
3. Add basic search endpoint
4. Time: 2-3 hours

**Option 2: Full Pipeline - Sequential (Complete Solution)**
1. Implement full processing pipeline
2. Background job processing
3. All content extraction
4. Time: 1-2 days

**Option 3: Plan Only (User Decision)**
- Review this plan
- Decide on priorities
- Confirm technical approach
- Schedule implementation

---

## Questions for Discussion

1. **Processing Timing:** When should images be processed?
   - During upload (slower but complete)
   - Background job (faster upload, delayed content)
   - On-demand (lazy loading)

2. **Cost Tolerance:** What's acceptable for processing?
   - $0.01 per image (Claude Vision)
   - $0.0001 per image (DeepSeek OCR only)
   - Pay-per-query (lazy loading)

3. **Content Priorities:** What's most important?
   - OCR text for search
   - Chart data extraction
   - Formula parsing
   - All of the above

4. **Use Cases:** What analysis workflows need support?
   - Search papers by chart content
   - Compare benchmark tables
   - Extract mathematical formulas
   - Understand system diagrams

5. **Performance Requirements:**
   - Acceptable upload delay?
   - Acceptable query response time?
   - Need for real-time processing?

---

## Technical Risks & Mitigation

### Risk 1: OCR Accuracy on Complex Images
**Mitigation:** Use DeepSeek for high accuracy, fallback to Tesseract

### Risk 2: Chart Data Extraction Failures
**Mitigation:** Graceful degradation - store OCR text even if structured extraction fails

### Risk 3: Embedding Storage Growth
**Mitigation:** Vectors are small (3KB each), manageable cost

### Risk 4: Processing Time for Large Documents
**Mitigation:** Background job queue, progress tracking, batch processing

### Risk 5: Vision API Rate Limits
**Mitigation:** Implement retry logic, queue management, alternative providers

---

## Conclusion

The image content retrieval system will enable:

✅ **Text-based search** of visual content
✅ **Structured data extraction** from charts and tables
✅ **Semantic understanding** of diagrams and formulas
✅ **Context-aware analysis** with surrounding text
✅ **Multi-modal RAG** combining text and images

This transforms images from "files" into "analyzable content" for downstream IEEE paper analysis and research workflows.
