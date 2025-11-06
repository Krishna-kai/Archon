-- Migration: Add archon_document_images table for image storage
-- Description: Supports image extraction from PDFs and web pages with OCR and vector search
-- Author: AI Assistant
-- Date: 2025-01-06
-- Reference: DATABASE_ARCHITECTURE_FINDINGS.md

-- ============================================================
-- CRITICAL ARCHITECTURE NOTES
-- ============================================================
-- 1. File uploads (PDFs) do NOT create archon_page_metadata entries
-- 2. page_id is NULL for file uploads, UUID for web crawls
-- 3. Primary linking is via source_id (works for both)
-- 4. page_number tracks position in PDFs (1-indexed)
-- 5. Current embedding dimension: 768 (text-embedding-3-small)
-- ============================================================

-- Create the archon_document_images table
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

-- ============================================================
-- INDEXES
-- ============================================================

-- Basic lookups
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

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Update updated_at timestamp on row modification
CREATE OR REPLACE FUNCTION update_document_images_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_document_images_updated_at
    BEFORE UPDATE ON archon_document_images
    FOR EACH ROW
    EXECUTE FUNCTION update_document_images_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- Enable RLS
ALTER TABLE archon_document_images ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Allow service role full access" ON archon_document_images
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE archon_document_images IS 'Stores metadata and OCR text for images extracted from PDFs and web pages';
COMMENT ON COLUMN archon_document_images.source_id IS 'Primary link to archon_sources (works for both file uploads and web crawls)';
COMMENT ON COLUMN archon_document_images.page_id IS 'NULL for file uploads, UUID for web crawls linking to archon_page_metadata';
COMMENT ON COLUMN archon_document_images.page_number IS 'PDF page number (1-indexed) for positional tracking';
COMMENT ON COLUMN archon_document_images.image_index IS 'Order of image within page (0-indexed)';
COMMENT ON COLUMN archon_document_images.storage_path IS 'Path in Supabase Storage bucket: {source_id}/{page_number}_{image_index}.{ext}';
COMMENT ON COLUMN archon_document_images.ocr_text IS 'Text extracted from image via OCR for searchability';
COMMENT ON COLUMN archon_document_images.image_type IS 'Classification: chart, diagram, formula, photo, table';
COMMENT ON COLUMN archon_document_images.embedding IS 'Vector embedding of OCR text for semantic search (768 dimensions)';

-- ============================================================
-- STORAGE BUCKET SETUP
-- ============================================================

-- Note: This SQL creates the database table only.
-- The Supabase Storage bucket 'document-images' must be created via:
--   1. Supabase Dashboard: Storage → New Bucket
--   2. Or via archon-server ImageStorageService initialization
--   3. Bucket settings:
--      - Name: document-images
--      - Public: false (signed URLs only)
--      - File size limit: 10MB per image
--      - Allowed MIME types: image/jpeg, image/png, image/gif

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- After running this migration, verify with:
-- SELECT COUNT(*) FROM archon_document_images;
-- SELECT * FROM pg_indexes WHERE tablename = 'archon_document_images';
-- SELECT * FROM pg_policies WHERE tablename = 'archon_document_images';
