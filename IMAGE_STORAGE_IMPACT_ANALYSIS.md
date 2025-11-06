# Image Storage Feature - Complete Impact Analysis

**Date**: 2025-01-06
**Scope**: All Archon services, API routes, MCP tools, and UI components
**Status**: Database complete ✅ | Implementation needed ⏳

---

## Executive Summary

Adding image storage support impacts **15-20 backend files**, **2-3 MCP tools**, and **0-2 frontend files**. The changes span the entire document processing pipeline from MinerU extraction through storage to MCP retrieval.

### Impact Breakdown
- 🔴 **CRITICAL** changes: 8 files (system will break without them)
- 🟡 **HIGH PRIORITY** changes: 5 files (features incomplete without them)
- 🟢 **OPTIONAL** enhancements: 4 files (nice-to-have improvements)

---

## 🎯 Data Flow Overview

```
PDF Upload → MinerU Native → MinerU HTTP Client → Document Storage Service →
             (extracts images)  (receives images)   (processes & stores)

Supabase Storage (images) + archon_document_images (metadata) → RAG Search → MCP Tools → AI Agents
```

---

## 📁 Backend Services - Files to Modify/Create

### 🔴 CRITICAL Changes (Must Implement)

#### 1. **MinerU Native Service**
**File**: `python/src/mineru_service/main.py` (EXISTS - MODIFY)
**Lines to Change**: 134-140 (cleanup `finally` block)
**Current Behavior**: Deletes all images after extraction
**Required Changes**:
```python
# BEFORE (lines 134-140):
finally:
    if work_dir and work_dir.exists():
        shutil.rmtree(work_dir)  # ❌ DELETES IMAGES

# AFTER:
finally:
    # 1. Read all image files from work_dir/images/
    # 2. Encode images as base64
    # 3. Add to response: {"images": [{"name": "...", "base64": "...", "page": 1}]}
    # 4. THEN cleanup work_dir
```
**Priority**: 🔴 CRITICAL
**Estimated Effort**: 2-3 hours

---

#### 2. **MinerU HTTP Client**
**File**: `python/src/server/services/mineru_http_client.py` (EXISTS - MODIFY)
**Current Behavior**: Receives markdown text only
**Required Changes**:
- Update response parsing to handle `images` field
- Decode base64 image data
- Pass images to document storage service
- Add type hints for image data structures

**Priority**: 🔴 CRITICAL
**Estimated Effort**: 1-2 hours

---

#### 3. **Image Storage Service** (NEW FILE)
**File**: `python/src/server/services/storage/image_storage_service.py` (CREATE NEW)
**Purpose**: Handle all image storage operations
**Required Methods**:
```python
class ImageStorageService:
    async def create_storage_bucket(self) -> bool:
        """Create 'document-images' bucket if not exists"""

    async def upload_image(
        self,
        image_data: bytes,
        source_id: str,
        page_number: int,
        image_index: int,
        metadata: dict
    ) -> dict:
        """Upload image to Supabase Storage, store metadata in DB"""

    async def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Generate signed URL for image access"""

    async def get_images_by_source(self, source_id: str) -> list[dict]:
        """Retrieve all images for a source"""

    async def get_images_by_page(self, source_id: str, page_number: int) -> list[dict]:
        """Retrieve images for a specific page"""

    async def delete_images_by_source(self, source_id: str) -> int:
        """Delete all images when source is deleted (CASCADE handled by DB)"""
```
**Dependencies**:
- Supabase Storage API
- `archon_document_images` table (✅ already created)
- Embedding service (for OCR embeddings)

**Priority**: 🔴 CRITICAL
**Estimated Effort**: 4-6 hours

---

#### 4. **Document Storage Service**
**File**: `python/src/server/services/storage/document_storage_service.py` (EXISTS - MODIFY)
**Current Behavior**: Stores text chunks only
**Required Changes**:
- Accept `images` parameter in main processing function
- Call `ImageStorageService.upload_image()` for each image
- Link images to source_id + page_number
- Run OCR on images (optional, based on settings)
- Generate embeddings for OCR text

**Priority**: 🔴 CRITICAL
**Estimated Effort**: 2-3 hours

---

### 🟡 HIGH PRIORITY Changes

#### 5. **Knowledge API Routes**
**File**: `python/src/server/api_routes/knowledge_api.py` (EXISTS - MODIFY)
**Required Changes**:
- Update upload endpoint response to include image count
- Add new endpoint: `GET /api/knowledge/sources/{source_id}/images`
- Add new endpoint: `GET /api/knowledge/images/{image_id}` (returns signed URL)

**Priority**: 🟡 HIGH
**Estimated Effort**: 1-2 hours

---

#### 6. **MCP RAG Tools**
**File**: `python/src/mcp_server/features/rag/rag_tools.py` (EXISTS - MODIFY)
**Required Changes**:
- **Update `rag_search_knowledge_base`**: Include image references in results
- **Update `rag_read_full_page`**: Return images associated with page
- **Add NEW `rag_search_images`**: Search images by OCR text or source
- **Add NEW `rag_get_image_details`**: Get image metadata + signed URL

**Example New Tool**:
```python
@mcp.tool()
async def rag_search_images(
    query: str,
    source_id: str | None = None,
    match_count: int = 5
) -> str:
    """
    Search for images by OCR text or metadata.
    Returns image URLs, OCR text, and context.
    """
```

**Priority**: 🟡 HIGH
**Estimated Effort**: 3-4 hours

---

#### 7. **Pydantic Models**
**File**: `python/src/server/models/` (CREATE NEW FILE)
**New File**: `python/src/server/models/image_models.py`
**Required Models**:
```python
class DocumentImage(BaseModel):
    id: UUID
    source_id: str
    page_id: UUID | None
    page_number: int | None
    image_index: int
    storage_path: str
    ocr_text: str | None
    image_type: str | None
    signed_url: str | None  # Generated on demand
    metadata: dict

class ImageSearchResult(BaseModel):
    image: DocumentImage
    similarity_score: float | None
    surrounding_context: str | None
```

**Priority**: 🟡 HIGH
**Estimated Effort**: 1 hour

---

#### 8. **OCR Service Integration**
**File**: `python/src/server/services/ocr_service.py` (EXISTS - ENHANCE)
**Current Behavior**: OCR for document pages
**Required Changes**:
- Add method: `extract_text_from_image(image_data: bytes) -> str`
- Support multiple OCR backends (Tesseract, easyOCR, etc.)
- Handle formulas, charts, diagrams

**Priority**: 🟡 HIGH
**Estimated Effort**: 2-3 hours

---

### 🟢 OPTIONAL Enhancements

#### 9. **Chart Extraction Service**
**File**: `python/src/server/services/chart_extraction_service.py` (EXISTS - ENHANCE)
**Potential Enhancement**: Classify images as charts/diagrams and extract structured data
**Priority**: 🟢 OPTIONAL
**Estimated Effort**: 4-6 hours

---

#### 10. **Frontend Knowledge Inspector**
**File**: `archon-ui-main/src/features/knowledge/inspector/components/ContentViewer.tsx` (EXISTS - MODIFY)
**Purpose**: Display images inline with text chunks
**Required Changes**:
- Fetch images for displayed source
- Render images with captions
- Add image viewer/lightbox component

**Priority**: 🟢 OPTIONAL (MCP tools work without UI)
**Estimated Effort**: 2-3 hours

---

#### 11. **Frontend Knowledge Types**
**File**: `archon-ui-main/src/features/knowledge/types/knowledge.ts` (EXISTS - MODIFY)
**Required Changes**:
```typescript
export interface KnowledgeSource {
    // ... existing fields
    image_count?: number;  // ADD
    has_images?: boolean;  // ADD
}

export interface DocumentImage {  // ADD NEW
    id: string;
    source_id: string;
    page_number: number | null;
    image_index: number;
    signed_url: string;
    ocr_text: string | null;
    image_type: string | null;
    created_at: string;
}
```

**Priority**: 🟢 OPTIONAL
**Estimated Effort**: 30 minutes

---

#### 12. **Frontend Knowledge Service**
**File**: `archon-ui-main/src/features/knowledge/services/knowledgeService.ts` (EXISTS - MODIFY)
**Required Changes**:
```typescript
export const knowledgeService = {
    // ... existing methods

    // ADD NEW:
    async getSourceImages(sourceId: string): Promise<DocumentImage[]> {
        const response = await apiClient.get(`/knowledge/sources/${sourceId}/images`);
        return response.data;
    },

    async getImageDetails(imageId: string): Promise<DocumentImage> {
        const response = await apiClient.get(`/knowledge/images/${imageId}`);
        return response.data;
    }
}
```

**Priority**: 🟢 OPTIONAL
**Estimated Effort**: 30 minutes

---

## 🗄️ Database Changes

### ✅ Already Complete

1. **`archon_document_images` table** - CREATED ✅
2. **10 indexes** - CREATED ✅
3. **Foreign keys** - CONFIGURED ✅
4. **RLS policies** - ENABLED ✅

### ⏭️ Next: Supabase Storage Bucket

**Bucket Name**: `document-images`
**Configuration**:
- Public: `false` (signed URLs only)
- File size limit: 10MB per image
- Allowed MIME types: `image/jpeg`, `image/png`, `image/gif`
- Path structure: `{source_id}/{page_number}_{image_index}.{ext}`

**How to Create**:
1. Via Supabase Dashboard: Storage → New Bucket
2. Via `ImageStorageService.create_storage_bucket()` on first upload

---

## 📊 Implementation Priority Matrix

| Priority | Component | File/Service | Estimated Time | Blocks Other Work? |
|----------|-----------|--------------|----------------|-------------------|
| 🔴 P0 | MinerU Native | `mineru_service/main.py` | 2-3h | YES - everything depends on this |
| 🔴 P0 | MinerU HTTP Client | `mineru_http_client.py` | 1-2h | YES |
| 🔴 P0 | Image Storage Service | `storage/image_storage_service.py` | 4-6h | YES |
| 🔴 P0 | Document Storage | `storage/document_storage_service.py` | 2-3h | YES |
| 🟡 P1 | Pydantic Models | `models/image_models.py` | 1h | NO |
| 🟡 P1 | Knowledge API | `knowledge_api.py` | 1-2h | NO |
| 🟡 P1 | MCP RAG Tools | `rag/rag_tools.py` | 3-4h | NO (but needed for AI access) |
| 🟡 P1 | OCR Service | `ocr_service.py` | 2-3h | NO (images stored without OCR) |
| 🟢 P2 | Frontend Types | `knowledge.ts` | 30min | NO |
| 🟢 P2 | Frontend Service | `knowledgeService.ts` | 30min | NO |
| 🟢 P2 | Frontend UI | `ContentViewer.tsx` | 2-3h | NO |
| 🟢 P3 | Chart Classification | `chart_extraction_service.py` | 4-6h | NO |

---

## 🔄 Implementation Phases (Recommended Order)

### Phase 1: Core Image Extraction & Storage (8-11 hours)
**Goal**: Images are extracted, stored, and linked to sources

1. Modify `mineru_service/main.py` (2-3h)
2. Modify `mineru_http_client.py` (1-2h)
3. Create `image_storage_service.py` (4-6h)
4. Modify `document_storage_service.py` (2-3h)

**Success Criteria**: Upload PDF → Images stored in Supabase → Metadata in DB

---

### Phase 2: API & Data Models (2-3 hours)
**Goal**: Images accessible via API

1. Create `image_models.py` (1h)
2. Update `knowledge_api.py` (1-2h)

**Success Criteria**: `GET /api/knowledge/sources/{id}/images` returns image list with signed URLs

---

### Phase 3: MCP Tools (3-4 hours)
**Goal**: AI agents can retrieve images

1. Update `rag_tools.py` (3-4h)
   - Add `rag_search_images`
   - Add `rag_get_image_details`
   - Update `rag_search_knowledge_base`
   - Update `rag_read_full_page`

**Success Criteria**: AI can ask "show me images from this paper" and get results

---

### Phase 4: OCR & Searchability (2-3 hours)
**Goal**: Images are searchable via text content

1. Enhance `ocr_service.py` (2-3h)
2. Integrate OCR into `image_storage_service.py`

**Success Criteria**: Search for "neural network diagram" finds relevant images

---

### Phase 5: Frontend (Optional, 3-4 hours)
**Goal**: Users can view images in UI

1. Update `knowledge.ts` types (30min)
2. Update `knowledgeService.ts` (30min)
3. Update `ContentViewer.tsx` (2-3h)

**Success Criteria**: Knowledge Inspector shows inline images

---

## 🧪 Testing Requirements

### Unit Tests

1. **`test_image_storage_service.py`** (NEW)
   - Test bucket creation
   - Test image upload
   - Test signed URL generation
   - Test image retrieval

2. **`test_mineru_service.py`** (MODIFY)
   - Test image extraction
   - Test base64 encoding
   - Verify cleanup doesn't delete before encoding

3. **`test_document_storage_service.py`** (MODIFY)
   - Test image processing integration
   - Test OCR integration
   - Test embedding generation for images

### Integration Tests

1. **End-to-End Upload Test**:
   ```
   Upload PDF with images → Verify images in Storage → Verify metadata in DB →
   Verify signed URLs work → Verify OCR text extracted
   ```

2. **MCP Tool Test**:
   ```
   Call rag_search_images → Verify results → Call rag_get_image_details →
   Verify signed URL → Download image
   ```

3. **Deletion Test**:
   ```
   Delete source → Verify CASCADE deletes images from DB →
   Verify Storage cleanup (if implemented)
   ```

---

## ⚠️ Potential Risks & Mitigation

### Risk 1: Storage Costs
**Issue**: Supabase Storage costs for large numbers of images
**Mitigation**:
- Set file size limits (10MB per image)
- Implement image compression
- Monitor storage usage

### Risk 2: Signed URL Expiration
**Issue**: URLs expire after 1 hour (default)
**Mitigation**:
- Generate signed URLs on-demand
- Cache URLs with TTL < expiration
- Handle 404 errors gracefully in frontend

### Risk 3: OCR Performance
**Issue**: OCR on complex diagrams/formulas may be slow or inaccurate
**Mitigation**:
- Make OCR optional (controlled by settings)
- Use async processing for OCR
- Consider specialized OCR for formulas (LaTeX-OCR)

### Risk 4: Image Extraction Quality
**Issue**: MinerU may not extract all images correctly
**Mitigation**:
- Test with various PDF types
- Provide manual upload fallback
- Log extraction failures for debugging

---

## 📈 Success Metrics

### Technical Metrics
- ✅ Image extraction rate: >95% of images extracted
- ✅ Storage latency: <2 seconds per image
- ✅ OCR accuracy: >90% for clean text in images
- ✅ API response time: <500ms for image list endpoint

### User-Facing Metrics
- ✅ AI agents can retrieve images via MCP
- ✅ Search finds relevant images by OCR text
- ✅ Images display correctly in UI (optional)
- ✅ No data loss (images persist with sources)

---

## 🎯 Total Estimated Effort

| Phase | Priority | Time Estimate |
|-------|----------|---------------|
| Phase 1: Core (Backend) | 🔴 CRITICAL | 8-11 hours |
| Phase 2: API & Models | 🟡 HIGH | 2-3 hours |
| Phase 3: MCP Tools | 🟡 HIGH | 3-4 hours |
| Phase 4: OCR | 🟡 HIGH | 2-3 hours |
| Phase 5: Frontend | 🟢 OPTIONAL | 3-4 hours |
| **TOTAL (Required)** | - | **15-21 hours** |
| **TOTAL (With Frontend)** | - | **18-25 hours** |

---

## 🚀 Next Immediate Steps

1. **Create Supabase Storage bucket** `document-images`
2. **Start Phase 1, Step 1**: Modify `mineru_service/main.py`
3. **Review MinerU image output format** to understand structure
4. **Set up test PDFs** with various image types (charts, diagrams, photos)

---

## 📚 Reference Documents

1. **DATABASE_ARCHITECTURE_FINDINGS.md** - Database investigation results
2. **DOCUMENT_IMAGE_STORAGE_PLAN.md** - Original 6-phase implementation plan
3. **SESSION_SUMMARY_IMAGE_STORAGE.md** - Session summary with database setup
4. **migration/add_document_images_table.sql** - Database migration (applied ✅)

---

## ✅ Progress Tracker

- [x] Database schema designed and created
- [x] Impact analysis completed
- [ ] Supabase Storage bucket created
- [ ] MinerU native service modified
- [ ] MinerU HTTP client updated
- [ ] Image storage service created
- [ ] Document storage service updated
- [ ] API endpoints added
- [ ] MCP tools updated
- [ ] OCR integration complete
- [ ] Frontend updated (optional)
- [ ] End-to-end testing complete

---

**Status**: Database foundation complete ✅ | Ready for Phase 1 implementation ⏭️
