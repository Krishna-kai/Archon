# Database Architecture Findings - File Uploads vs Web Crawls

## Executive Summary

The database investigation revealed **two distinct storage architectures** in Archon:
1. **Web Crawls**: Three-tier structure with full pages and linked chunks
2. **File Uploads (PDFs)**: Two-tier structure with direct source-to-chunk linking

This architectural difference is **CRITICAL** for implementing image storage, as images from PDFs need a different linking strategy than web page images.

---

## Current Database Statistics

```
Total Sources:              27
├─ File Uploads:            20 sources
└─ Web Crawls:              6-7 sources

Total Chunks:               3,142
├─ With page_id (web):      3,113 chunks
└─ Without page_id (files): 29 chunks

Total Pages (metadata):     1,666 (web crawls only)
Total Code Examples:        860
```

---

## Architecture Pattern 1: Web Crawls

### Structure
```
archon_sources
    ↓ (source_id)
archon_page_metadata (full pages)
    ↓ (page_id foreign key)
archon_crawled_pages (chunks)
```

### Characteristics
- **Three-tier hierarchy**: source → full page → chunks
- **page_id linking**: Chunks reference their parent page via `page_id` foreign key
- **Full content storage**: `archon_page_metadata.full_content` contains complete page text
- **Metadata tracking**: `section_title`, `word_count`, `chunk_count` per page
- **URL format**: Standard web URLs (e.g., `https://ai.pydantic.dev/api/durable_exec/index.md`)

### Example Data
```json
{
  "source_id": "473e7956a86382e6",
  "page_id": "01087689-aa19-44de-8ee4-6795b56e3e5a",
  "url": "https://ai.pydantic.dev/api/durable_exec/index.md",
  "chunk_number": 29,
  "metadata": {
    "url": "https://ai.pydantic.dev/api/durable_exec/index.md",
    "tags": ["pydantic", "ai"],
    "title": "pydantic_ai.durable_exec",
    "page_id": "01087689-aa19-44de-8ee4-6795b56e3e5a",
    "source_id": "473e7956a86382e6",
    "crawl_type": "llms_txt_with_linked_pages"
  }
}
```

---

## Architecture Pattern 2: File Uploads (PDFs)

### Structure
```
archon_sources
    ↓ (source_id only)
archon_crawled_pages (chunks)
```

### Characteristics
- **Two-tier hierarchy**: source → chunks directly
- **NO page_id linking**: All chunks have `page_id = NULL`
- **NO page_metadata entries**: File uploads do not create entries in `archon_page_metadata`
- **Direct source linking**: Chunks link to source via `source_id` only
- **URL format**: File protocol (e.g., `file://Copy of Dual U-Net.pdf`)
- **No crawl_type**: `metadata->>'crawl_type'` is NULL for file uploads

### Example Data
```json
{
  "source_id": "file_Copy_of_Dual_U-Net_for_the_Segmentation_of_Overlapping_Glioma_Nuclei_pdf_0710eb11",
  "url": "file://Copy of Dual U-Net for the Segmentation of Overlapping Glioma Nuclei.pdf",
  "chunk_number": 0,
  "page_id": null,
  "metadata": {
    "char_count": "4617",
    "word_count": "655",
    "chunk_size": 4617,
    "chunk_index": 0
  }
}
```

### Source Metadata
```json
{
  "tags": ["research", "test", "chart-extraction"],
  "source_type": "file",
  "auto_generated": false,
  "knowledge_type": "technical",
  "update_frequency": 7
}
```

---

## Database Schema Details

### Key Tables

#### `archon_sources`
- Stores both web crawls and file uploads
- `metadata->>'source_type'` distinguishes: `"file"` vs others
- `total_word_count` aggregated from all chunks
- Foreign key source for cascading deletes

#### `archon_page_metadata`
- **ONLY used for web crawls**
- Stores full page content and metadata
- Referenced by chunks via `page_id` foreign key
- **Zero entries for file uploads**

#### `archon_crawled_pages`
- Stores all text chunks (both web and file)
- `page_id` is NULL for file uploads, UUID for web crawls
- Multiple embedding columns: `embedding_384`, `embedding_768`, `embedding_1024`, `embedding_1536`, `embedding_3072`
- `embedding_dimension` tracks which embedding is active (currently 768)

### Foreign Key Relationships

```sql
archon_crawled_pages.source_id → archon_sources.source_id (CASCADE DELETE)
archon_crawled_pages.page_id → archon_page_metadata.id (SET NULL)
archon_page_metadata.source_id → archon_sources.source_id (CASCADE DELETE)
```

### Indexes

#### Vector Indexes (ivfflat)
- One index per embedding dimension (384, 768, 1024, 1536, 3072)
- Uses `vector_cosine_ops` for cosine similarity
- Lists parameter: 100

#### JSONB Indexes (GIN)
- `archon_crawled_pages.metadata` (GIN index)
- `archon_page_metadata.metadata` (GIN index)

#### Unique Constraints
- `(url, chunk_number)` unique on `archon_crawled_pages`
- `(url, chunk_number)` unique on `archon_code_examples`

---

## Implications for Image Storage

### Critical Design Decisions Required

1. **Linking Strategy**
   - Web crawl images: Can link to `page_id` (if needed)
   - PDF images: **MUST link to `source_id`** (no page_id available)
   - **Recommendation**: Use `source_id` as primary link for all images

2. **Position Tracking**
   - PDF images need `page_number` or `chunk_number` to track position
   - Charts/figures often span multiple chunks
   - May need separate `image_index` for ordering

3. **Metadata Storage**
   - OCR text for searchability
   - Image type (chart, diagram, formula, photo)
   - Position in document (page number, bounding box)
   - Relationship to nearby chunks

4. **Retrieval Patterns**
   - By source: "Get all images from this PDF"
   - By page: "Get images from page 5"
   - By search: "Find charts containing specific content"
   - By chunk proximity: "Get images near this text chunk"

### Recommended Schema Addition

```sql
CREATE TABLE archon_document_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id TEXT NOT NULL REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  -- Position tracking
  page_number INTEGER,           -- PDF page number
  chunk_number INTEGER,          -- Associated chunk (if applicable)
  image_index INTEGER,           -- Order within page

  -- Storage
  storage_path TEXT NOT NULL,    -- Supabase Storage path

  -- Metadata
  image_type TEXT,               -- 'chart', 'diagram', 'formula', 'photo', 'table'
  ocr_text TEXT,                 -- Searchable text from OCR
  width INTEGER,
  height INTEGER,
  file_size_bytes INTEGER,

  -- Full-text search
  ocr_vector vector(768),        -- Embedding of OCR text for semantic search

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- Indexes
  UNIQUE(source_id, page_number, image_index)
);

-- Indexes
CREATE INDEX idx_document_images_source ON archon_document_images(source_id);
CREATE INDEX idx_document_images_page ON archon_document_images(source_id, page_number);
CREATE INDEX idx_document_images_type ON archon_document_images(image_type);
CREATE INDEX idx_document_images_ocr_vector ON archon_document_images
  USING ivfflat (ocr_vector vector_cosine_ops) WITH (lists = 100);
```

---

## Implementation Impact

### Phase 1: Database Schema (NOW UPDATED)
- Use `source_id` as primary link (works for both architectures)
- Add `page_number` for PDF positional tracking
- Do NOT rely on `page_id` foreign key (NULL for files)

### Phase 2-3: MinerU Integration (NO CHANGES)
- MinerU processes files, not web crawls
- Implementation remains as planned in `DOCUMENT_IMAGE_STORAGE_PLAN.md`

### Phase 4: Storage Service (MINOR UPDATE)
- Storage path format: `document-images/{source_id}/{page_number}_{image_index}.{ext}`
- Support both file and web sources (future-proof)

### Phase 5: Document Processing (CRITICAL UPDATE)
- File upload processing does NOT create page_metadata
- Images linked directly to source_id
- Chunk association is optional (for proximity search)

### Phase 6: MCP Tools (UPDATED)
- Query by `source_id` (primary)
- Query by `page_number` (secondary)
- Query by OCR text search (tertiary)
- Do NOT expose `page_id` in MCP API

---

## Testing Implications

### Test Scenarios Must Include

1. **File Upload with Images**
   - Upload PDF with charts
   - Verify images link to source_id
   - Verify page_number tracking
   - Confirm page_id is NULL

2. **Web Crawl (Future)**
   - If web pages ever have images
   - Verify source_id linking still works
   - Confirm page_id is optional

3. **Retrieval Patterns**
   - By source_id: Get all images from source
   - By page_number: Get images from specific page
   - By OCR search: Find images with text
   - By proximity: Get images near chunk

---

## Conclusions

1. **Use source_id as the primary link** for all document images (both files and web)
2. **Do NOT rely on page_id** - it's NULL for file uploads
3. **Add page_number tracking** for positional information in PDFs
4. **Update DOCUMENT_IMAGE_STORAGE_PLAN.md** with these architectural insights
5. **File uploads are simpler** - two-tier structure (source → chunks)

---

## Next Steps

1. ✅ Complete database investigation
2. 🔄 Document architectural differences (this file)
3. ⏭️ Update implementation plan based on findings
4. ⏭️ Proceed with Phase 1: Create `archon_document_images` table
