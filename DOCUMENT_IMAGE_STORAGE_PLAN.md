# Document Image Storage Implementation Plan

## Executive Summary

This plan outlines the complete architecture for adding image extraction, storage, OCR, and retrieval capabilities to Archon's document processing pipeline. The goal is to handle both **structured data** (text, formulas, tables) and **unstructured data** (images, charts, diagrams) from PDF documents, particularly research papers with complex layouts.

## Problem Statement

### Current Limitations
1. **Missing Images**: MinerU extracts images from PDFs but current implementation deletes them before storage
2. **Text-Only RAG**: Only text chunks are stored and searchable via MCP
3. **Lost Context**: Charts, diagrams, architecture diagrams, and visual data are not available to AI agents
4. **No Image Search**: Cannot search or retrieve images based on content or context
5. **Complex Documents**: Research papers with formulas, two-column layouts, and figures lose critical visual information

### User Requirements
- Extract and preserve ALL images from research papers and documents
- Store images in Supabase Storage with proper metadata
- OCR images to make them searchable
- Link images to their surrounding text context
- Make images retrievable via MCP tools for AI agents
- Handle formulas, charts, diagrams, and complex layouts

## Current State Assessment

### What Exists
**Database Tables:**
- `archon_crawled_pages` - Text chunks with vector embeddings (3,142 rows)
- `archon_page_metadata` - Full page content (1,666 rows)
- `archon_code_examples` - Code snippets (860 rows)
- `archon_sources` - Knowledge sources (27 rows)

**Services:**
- `MinerU Native Service` (`/Users/krishna/Projects/archon/python/src/mineru_service/main.py`) - Runs on host Mac with GPU
- `MinerU HTTP Client` (`/Users/krishna/Projects/archon/python/src/server/services/mineru_http_client.py`) - Client for Docker containers
- `DocumentStorageService` - Handles text chunk storage and embedding generation
- `Supabase Client` - Available via `get_supabase_client()` with Storage API support

**Critical Issue in Native Service (Lines 134-140):**
```python
finally:
    if work_dir and work_dir.exists():
        try:
            shutil.rmtree(work_dir)  # ❌ DELETES ALL IMAGES!
        except Exception as e:
            print(f"Warning: Failed to cleanup {work_dir}: {e}")
```

### What's Missing
- ❌ No Supabase Storage bucket for images
- ❌ No `archon_document_images` table for image metadata
- ❌ No image storage service
- ❌ No image OCR processing
- ❌ No image retrieval via MCP
- ❌ No link between images and text chunks

## Proposed Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. PDF Upload via API                                           │
│    POST /api/knowledge/upload                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. MinerU Processing (Native Mac Service - Port 8055)          │
│    - Extract markdown text (formulas, tables, structure)        │
│    - Extract images (charts, diagrams, figures)                 │
│    - Convert images to base64 encoding                          │
│    - Return: {                                                  │
│        "markdown": "...",                                       │
│        "images": [                                              │
│          {"name": "image_0.jpg", "base64": "...", "page": 1},  │
│          {"name": "image_1.png", "base64": "...", "page": 2}   │
│        ],                                                       │
│        "metadata": {...}                                        │
│      }                                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. archon-server Processing (Document Storage Service)         │
│    A. Process Images:                                           │
│       - Decode base64 → binary data                             │
│       - Upload to Supabase Storage bucket                       │
│       - Run OCR on images → extract text                        │
│       - Generate image descriptions/captions                    │
│       - Store metadata in archon_document_images table          │
│                                                                 │
│    B. Process Text:                                             │
│       - Chunk markdown text                                     │
│       - Generate embeddings for text chunks                     │
│       - Store in archon_crawled_pages table                     │
│       - Link chunks to images via page_id + image_ids          │
│                                                                 │
│    C. Generate Image Embeddings:                                │
│       - Create embeddings from OCR text + descriptions          │
│       - Store in archon_document_images.embedding column        │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Supabase Storage & Database                                  │
│                                                                 │
│    Storage Bucket: "document-images"                            │
│    ├── {source_id}/                                            │
│    │   ├── page_1_image_0.jpg     ← page_number_image_index   │
│    │   ├── page_1_image_1.png                                  │
│    │   ├── page_2_image_0.jpg                                  │
│    │   └── page_3_image_0.png                                  │
│                                                                 │
│    Tables:                                                      │
│    ├── archon_sources (existing - both files + web)            │
│    ├── archon_page_metadata (existing - web crawls ONLY)       │
│    ├── archon_crawled_pages (existing - text chunks)           │
│    └── archon_document_images (NEW - image metadata)           │
│                                                                 │
│    CRITICAL: File uploads do NOT create page_metadata entries! │
│    Images link via source_id + page_number (not page_id)       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. RAG Retrieval & MCP Tools                                    │
│                                                                 │
│    Text Search:                                                 │
│    - Query archon_crawled_pages (existing)                     │
│    - Return text chunks + linked image references              │
│                                                                 │
│    Image Search (NEW):                                          │
│    - Query archon_document_images by embedding similarity      │
│    - Return image URLs + OCR text + descriptions               │
│                                                                 │
│    MCP Tools:                                                   │
│    - rag_search_knowledge_base → includes image references     │
│    - rag_search_images (NEW) → dedicated image search          │
│    - rag_read_full_page → includes inline images               │
│    - rag_get_image_details (NEW) → get image URL + metadata    │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema Design

### New Table: `archon_document_images`

**CRITICAL**: Based on database investigation (see `DATABASE_ARCHITECTURE_FINDINGS.md`),
file uploads do NOT create `archon_page_metadata` entries. Therefore:
- `page_id` must be NULLABLE (NULL for file uploads, UUID for web crawls)
- Primary linking is via `source_id` (works for both architectures)
- `page_number` tracks position in PDFs (where page_id is NULL)

```sql
CREATE TABLE IF NOT EXISTS archon_document_images (
    -- Primary Key
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Relationships
    -- CRITICAL: source_id is the primary link (works for files + web)
    source_id TEXT NOT NULL REFERENCES archon_sources(source_id) ON DELETE CASCADE,

    -- NULLABLE: page_id is NULL for file uploads, UUID for web crawls
    page_id UUID REFERENCES archon_page_metadata(id) ON DELETE SET NULL,

    -- Position Tracking
    -- For PDFs: page_number tracks position (1-indexed)
    -- For web: page_id provides the link (page_number can be NULL)
    page_number INTEGER,  -- PDF page number (1-indexed)
    image_index INTEGER NOT NULL,  -- Order within page (0-indexed)
    chunk_number INTEGER,  -- Associated chunk (optional, for proximity search)

    -- Image Identification
    image_name TEXT NOT NULL,  -- Original filename from MinerU (e.g., "image_0.jpg")

    -- Storage Information
    storage_path TEXT NOT NULL UNIQUE,  -- Path in Supabase Storage: {source_id}/{page_number}_{image_index}.{ext}
    file_size_bytes INTEGER,
    mime_type TEXT DEFAULT 'image/jpeg',
    width_px INTEGER,
    height_px INTEGER,

    -- Content & Context
    ocr_text TEXT,  -- Extracted text from OCR (for searchability)
    image_type TEXT,  -- 'chart', 'diagram', 'formula', 'photo', 'table'
    surrounding_text TEXT,  -- Text before/after image in document (optional)

    -- Searchability
    embedding vector(768),  -- Vector embedding of OCR text (using current dimension: 768)
    embedding_model TEXT DEFAULT 'text-embedding-3-small',
    embedding_dimension INTEGER DEFAULT 768,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,  -- Flexible metadata (bounding box, etc.)

    -- Processing Status
    ocr_processed BOOLEAN DEFAULT FALSE,
    embedding_generated BOOLEAN DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    -- Unique image per source + page_number + index (handles NULL page_id)
    CONSTRAINT unique_image_per_position UNIQUE(source_id, page_number, image_index)
);

-- Indexes for performance
CREATE INDEX idx_document_images_source_id ON archon_document_images(source_id);
CREATE INDEX idx_document_images_page_id ON archon_document_images(page_id) WHERE page_id IS NOT NULL;
CREATE INDEX idx_document_images_storage_path ON archon_document_images(storage_path);
CREATE INDEX idx_document_images_page_number ON archon_document_images(source_id, page_number);
CREATE INDEX idx_document_images_type ON archon_document_images(image_type);

-- Full-text search on OCR text
CREATE INDEX idx_document_images_ocr_text ON archon_document_images
  USING gin(to_tsvector('english', ocr_text));

-- Vector similarity search
CREATE INDEX idx_document_images_embedding ON archon_document_images
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger for updated_at
CREATE TRIGGER update_document_images_updated_at
    BEFORE UPDATE ON archon_document_images
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE archon_document_images ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow service role full access" ON archon_document_images
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow authenticated users to read" ON archon_document_images
    FOR SELECT TO authenticated
    USING (true);
```

### Supabase Storage Bucket Configuration

```sql
-- Create storage bucket for document images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'document-images',
    'document-images',
    false,  -- Private bucket (use signed URLs)
    52428800,  -- 50MB file size limit
    ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
);

-- Storage policies
CREATE POLICY "Service role can upload images"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'document-images');

CREATE POLICY "Service role can update images"
ON storage.objects FOR UPDATE
TO service_role
USING (bucket_id = 'document-images');

CREATE POLICY "Service role can delete images"
ON storage.objects FOR DELETE
TO service_role
USING (bucket_id = 'document-images');

CREATE POLICY "Authenticated users can view images"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'document-images');
```

### Link to Existing Tables

**Modify `archon_crawled_pages` to reference images:**
```sql
ALTER TABLE archon_crawled_pages
ADD COLUMN IF NOT EXISTS related_images UUID[] DEFAULT '{}';

COMMENT ON COLUMN archon_crawled_pages.related_images IS
'Array of image IDs from archon_document_images table that appear near this text chunk';
```

## Service Layer Design

### New Service: `ImageStorageService`

**Location**: `/Users/krishna/Projects/archon/python/src/server/services/image_storage_service.py`

**Responsibilities:**
- Upload images to Supabase Storage
- Generate storage paths and URLs
- Store image metadata in database
- Run OCR on images
- Generate image captions/descriptions
- Generate embeddings for images
- Retrieve images by ID or search criteria
- Delete images and clean up storage

**Key Methods:**
```python
class ImageStorageService:
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.bucket_name = "document-images"

    async def upload_image(
        self,
        image_data: bytes,
        source_id: str,
        page_id: str,
        image_name: str,
        image_number: int,
        page_number: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Upload image to storage and store metadata"""

    async def run_ocr_on_image(
        self,
        image_id: str
    ) -> str:
        """Extract text from image using OCR"""

    async def generate_image_caption(
        self,
        image_id: str,
        surrounding_context: Optional[str] = None
    ) -> str:
        """Generate AI caption for image"""

    async def generate_image_embedding(
        self,
        image_id: str
    ) -> List[float]:
        """Generate vector embedding from OCR text + caption"""

    async def get_image_by_id(
        self,
        image_id: str,
        generate_signed_url: bool = True,
        url_expires_in: int = 3600
    ) -> Dict[str, Any]:
        """Retrieve image metadata and URL"""

    async def search_images_by_text(
        self,
        query: str,
        source_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search images using vector similarity"""

    async def delete_image(
        self,
        image_id: str
    ) -> bool:
        """Delete image from storage and database"""
```

### Modify Existing: `MinerU Native Service`

**File**: `/Users/krishna/Projects/archon/python/src/mineru_service/main.py`

**Changes:**
1. **Keep images in temp directory** until after HTTP response
2. **Encode images as base64** and include in response
3. **Return image list** with metadata

```python
# Current (lines 67-140) - BEFORE
finally:
    if work_dir and work_dir.exists():
        try:
            shutil.rmtree(work_dir)  # ❌ Deletes images!
        except Exception as e:
            print(f"Warning: Failed to cleanup {work_dir}: {e}")

# Proposed - AFTER
# Extract images before cleanup
images = []
if work_dir and work_dir.exists():
    image_dir = work_dir / "images"
    if image_dir.exists():
        for img_file in sorted(image_dir.glob("*")):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                with open(img_file, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                images.append({
                    "name": img_file.name,
                    "base64": image_data,
                    "page": extract_page_from_filename(img_file.name),
                    "size_bytes": img_file.stat().st_size,
                    "mime_type": f"image/{img_file.suffix.lstrip('.')}"
                })

# Return images in response
return {
    "markdown": markdown_content,
    "images": images,
    "metadata": {
        "page_count": page_count,
        "image_count": len(images),
        # ... existing metadata
    }
}

# Now cleanup
finally:
    if work_dir and work_dir.exists():
        try:
            shutil.rmtree(work_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup {work_dir}: {e}")
```

### Modify Existing: `MinerU HTTP Client`

**File**: `/Users/krishna/Projects/archon/python/src/server/services/mineru_http_client.py`

**Changes:**
1. Parse `images` array from response
2. Decode base64 to binary data
3. Return images to caller

### Modify Existing: `DocumentStorageService`

**File**: `/Users/krishna/Projects/archon/python/src/server/services/document_storage_service.py`

**Changes:**
1. Accept images from document processing
2. Call `ImageStorageService` to handle image storage
3. Link images to text chunks via `related_images` column
4. Include image references in chunk metadata

## API Changes

### Modify Existing: Document Upload Endpoint

**File**: `/Users/krishna/Projects/archon/python/src/server/api_routes/knowledge_api.py`

**Endpoint**: `POST /api/knowledge/upload`

**Changes:**
1. Extract images from MinerU result
2. Pass images to `DocumentStorageService`
3. Update progress tracking to include image processing
4. Return image count in response

### New Endpoints (Optional - for direct image access)

**Endpoint**: `GET /api/knowledge/images/{image_id}`
- Retrieve image metadata and signed URL
- Supports query param `?download=true` for direct download

**Endpoint**: `GET /api/knowledge/sources/{source_id}/images`
- List all images for a source
- Pagination support

## MCP Tool Changes

### Modify Existing: `rag_search_knowledge_base`

**File**: `/Users/krishna/Projects/archon/python/src/mcp_server/features/knowledge/knowledge_tools.py`

**Changes:**
- Include `related_images` array in text chunk results
- Each image includes: `image_id`, `url`, `caption`, `page_number`

### New Tool: `rag_search_images`

```python
@server.tool()
async def rag_search_images(
    query: str,
    source_id: Optional[str] = None,
    match_count: int = 5
) -> str:
    """
    Search for images in the knowledge base using semantic search.

    Args:
        query: Search query describing the image content
        source_id: Optional filter by specific source
        match_count: Number of images to return (default 5)

    Returns:
        JSON with matching images, their URLs, OCR text, and captions
    """
```

### New Tool: `rag_get_image_details`

```python
@server.tool()
async def rag_get_image_details(
    image_id: str,
    include_url: bool = True
) -> str:
    """
    Get detailed information about a specific image.

    Args:
        image_id: UUID of the image
        include_url: Whether to generate a signed URL

    Returns:
        JSON with image metadata, OCR text, caption, and URL
    """
```

### Modify Existing: `rag_read_full_page`

**Changes:**
- Include inline image references with URLs
- Show images in context with surrounding text

## Image Processing Pipeline

### OCR Strategy

**Primary OCR Engine**: Tesseract (already available in Docker)

**Process:**
1. Image uploaded to storage
2. Download image from storage
3. Run Tesseract OCR to extract text
4. Store OCR text in `archon_document_images.ocr_text`
5. Update `ocr_processed = TRUE`

**Future Enhancement**: Support additional OCR engines (e.g., EasyOCR, PaddleOCR)

### Caption Generation Strategy

**Approach**: Use existing LLM (from settings) to generate captions

**Process:**
1. Get OCR text + surrounding document text
2. Prompt LLM: "Generate a concise caption describing this image. Context: {surrounding_text}. OCR text: {ocr_text}"
3. Store caption in `archon_document_images.caption`
4. Update `caption_generated = TRUE`

**Future Enhancement**: Use vision models (GPT-4V, Claude 3, LLaVA) for direct image analysis

### Embedding Generation Strategy

**Input Sources:**
1. OCR text (if available)
2. Generated caption
3. Surrounding text context
4. Image metadata (filename, page number)

**Combined Text:**
```
Caption: {caption}
OCR Text: {ocr_text}
Context: {surrounding_text}
Page: {page_number}
Filename: {image_name}
```

**Embedding Model**: Use same model as text chunks (configured in settings)

## Implementation Phases

### Phase 1: Database & Storage Setup
**Tasks:**
1. Create Supabase Storage bucket `document-images`
2. Create `archon_document_images` table with indexes
3. Add `related_images` column to `archon_crawled_pages`
4. Apply RLS policies
5. Test storage bucket access

**Files Modified:**
- `/Users/krishna/Projects/archon/migration/0.1.0/012_add_document_images.sql` (NEW)

**Validation:**
- Bucket exists and accessible
- Table created with proper constraints
- Indexes created successfully

### Phase 2: MinerU Service Modifications
**Tasks:**
1. Modify native service to encode images as base64
2. Update response format to include images array
3. Add image metadata extraction
4. Test with sample PDF

**Files Modified:**
- `/Users/krishna/Projects/archon/python/src/mineru_service/main.py` (lines 67-140)

**Validation:**
- Images returned in HTTP response
- Base64 encoding correct
- Temp cleanup still works

### Phase 3: Image Storage Service
**Tasks:**
1. Create `ImageStorageService` class
2. Implement upload_image method
3. Implement OCR processing
4. Implement caption generation
5. Implement embedding generation
6. Add comprehensive error handling

**Files Created:**
- `/Users/krishna/Projects/archon/python/src/server/services/image_storage_service.py` (NEW)

**Validation:**
- Images upload successfully
- Metadata stored correctly
- OCR extracts text
- Captions generated
- Embeddings created

### Phase 4: Integration with Document Processing
**Tasks:**
1. Update `MinerUHttpClient` to handle images
2. Update `DocumentStorageService` to process images
3. Link images to text chunks
4. Update progress tracking
5. Add comprehensive logging

**Files Modified:**
- `/Users/krishna/Projects/archon/python/src/server/services/mineru_http_client.py`
- `/Users/krishna/Projects/archon/python/src/server/services/document_storage_service.py`
- `/Users/krishna/Projects/archon/python/src/server/utils/document_processing.py`

**Validation:**
- End-to-end upload works
- Images stored and linked
- Progress tracking accurate

### Phase 5: MCP Tool Enhancements
**Tasks:**
1. Modify `rag_search_knowledge_base` to include images
2. Create `rag_search_images` tool
3. Create `rag_get_image_details` tool
4. Update `rag_read_full_page` to show images
5. Update MCP tool documentation

**Files Modified:**
- `/Users/krishna/Projects/archon/python/src/mcp_server/features/knowledge/knowledge_tools.py`

**Validation:**
- Image search returns relevant results
- Image URLs work in AI IDE
- Full page includes images

### Phase 6: Testing & Validation
**Tasks:**
1. Test with research paper PDFs
2. Test with various image types
3. Test OCR accuracy
4. Test search relevance
5. Load testing
6. Error handling validation

**Test Cases:**
- Upload PDF with multiple images
- Search for images by description
- Retrieve images via MCP
- Delete source with images (cascade)
- Handle malformed images
- Handle large images (>50MB)

## Testing Strategy

### Unit Tests

**New Test Files:**
- `tests/server/services/test_image_storage_service.py`
- `tests/server/services/test_mineru_http_client_images.py`
- `tests/mcp_server/features/knowledge/test_image_tools.py`

**Test Coverage:**
- Image upload to storage
- Base64 encoding/decoding
- OCR text extraction
- Caption generation
- Embedding generation
- Image search
- Image deletion with cleanup

### Integration Tests

**Test Scenarios:**
1. **Full Upload Flow**:
   - Upload PDF with 5 images
   - Verify all images stored
   - Verify OCR completed
   - Verify embeddings generated

2. **Search & Retrieval**:
   - Search for "neural network diagram"
   - Verify relevant images returned
   - Verify URLs are accessible

3. **MCP Tool Flow**:
   - Call `rag_search_knowledge_base`
   - Verify images included in results
   - Call `rag_get_image_details`
   - Verify metadata complete

### Manual Testing

**Test Documents:**
- Research paper with formulas (Histopathology papers)
- Technical documentation with architecture diagrams
- Two-column layout papers
- Papers with charts and graphs
- Papers with tables as images

**Validation:**
- All images extracted correctly
- OCR text readable and accurate
- Captions describe images appropriately
- Search finds relevant images
- URLs load images correctly

## Risk Analysis & Mitigation

### Risk 1: Storage Costs
**Impact**: Medium
**Probability**: High
**Mitigation**:
- Set file size limits (50MB per image)
- Implement image compression before upload
- Monitor storage usage
- Add cleanup for old sources

### Risk 2: OCR Performance
**Impact**: Medium
**Probability**: Medium
**Mitigation**:
- Run OCR asynchronously
- Add retry logic for failures
- Allow manual OCR retry
- Support multiple OCR engines

### Risk 3: Large Base64 Payloads
**Impact**: Low
**Probability**: Low
**Mitigation**:
- Compress images before base64 encoding
- Stream large responses
- Set reasonable timeouts
- Monitor response sizes

### Risk 4: Embedding Quality for Images
**Impact**: Medium
**Probability**: Medium
**Mitigation**:
- Use rich captions with context
- Include OCR text in embeddings
- Fine-tune search relevance
- Allow feedback mechanism

### Risk 5: Race Conditions in Processing
**Impact**: High
**Probability**: Low
**Mitigation**:
- Use database transactions
- Implement idempotent operations
- Add processing status flags
- Lock resources during updates

## Success Criteria

### Functional Requirements
- ✅ All images extracted from uploaded PDFs
- ✅ Images stored in Supabase Storage
- ✅ OCR text extracted from images
- ✅ AI-generated captions created
- ✅ Vector embeddings generated for search
- ✅ Images linked to text chunks
- ✅ Images searchable via MCP tools
- ✅ Images retrievable with signed URLs

### Performance Requirements
- Image upload: < 500ms per image
- OCR processing: < 2 seconds per image
- Caption generation: < 3 seconds per image
- Embedding generation: < 1 second per image
- Image search: < 200ms per query
- Total upload time: Base + (1 second × image count)

### Quality Requirements
- OCR accuracy: > 90% for printed text
- Caption relevance: Subjective but contextually accurate
- Search relevance: Top 5 results include target image > 80% of time
- No data loss: 100% of images preserved
- Uptime: 99.9% availability

## Future Enhancements

### Phase 7: Vision Model Integration
- Direct image analysis using GPT-4V / Claude 3
- Extract structured data from charts/graphs
- Generate detailed image descriptions

### Phase 8: Advanced Search
- Search by visual similarity (image embeddings)
- Multi-modal search (text + image)
- Filter by image type (chart, diagram, photo)

### Phase 9: Image Processing
- Automatic image enhancement
- De-duplication of similar images
- Image format conversion
- Thumbnail generation

### Phase 10: Analytics
- Track image view counts
- Most accessed images
- Image search analytics
- Storage usage dashboards

## Conclusion

This implementation plan provides a comprehensive roadmap for adding complete image support to Archon's document processing pipeline. The architecture follows Archon's existing patterns, uses proven technologies, and scales gracefully with document volume.

The phased approach allows for incremental delivery and validation at each step, reducing risk and ensuring quality. The plan addresses the user's need to handle both structured (text/formulas) and unstructured (images/charts) data from research papers and complex documents.

**Next Steps:**
1. Review this plan with stakeholders
2. Get approval on database schema design
3. Begin Phase 1 implementation
4. Iterate based on feedback and testing results
