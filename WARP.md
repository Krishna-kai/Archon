# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Overview

Archon is a knowledge management system with MCP (Model Context Protocol) integration for AI coding assistants. It's built as a microservices architecture with a React frontend, FastAPI backend services, and Supabase database.

## Development Commands

### Quick Start Commands

```bash
# Clone and setup
git clone -b stable https://github.com/coleam00/archon.git
cd archon
cp .env.example .env
# Edit .env with your Supabase credentials

# Full Docker mode (recommended for normal usage)
docker compose up --build -d

# Hybrid development mode (backend in Docker, frontend local with hot reload)
make dev

# Stop all services
make stop
```

### Make Commands (Recommended)

```bash
make dev          # Hybrid dev: backend in Docker, frontend local
make dev-docker   # Full Docker mode
make stop         # Stop all services
make test         # Run all tests
make test-fe      # Frontend tests only
make test-be      # Backend tests only
make lint         # Run all linters
make lint-fe      # Frontend linter
make lint-be      # Backend linter (Ruff + MyPy)
make install      # Install dependencies
make check        # Check environment setup
make clean        # Remove containers and volumes
```

### Frontend Commands (archon-ui-main/)

```bash
npm run dev              # Start dev server (port 3737)
npm run build            # Build for production
npm run test             # Run tests in watch mode
npm run test:ui          # Run with Vitest UI
npm run test:coverage:stream  # Run tests with coverage

# Linting (dual system)
npm run lint             # ESLint for legacy code
npm run biome            # Biome for /src/features
npm run biome:fix        # Auto-fix with Biome
npm run biome:format     # Format code

# TypeScript checking
npx tsc --noEmit         # Check all TypeScript
npx tsc --noEmit 2>&1 | grep "src/features"  # Check features only
```

### Backend Commands (python/)

```bash
# Using uv (preferred package manager)
uv sync --group all      # Install all dependencies
uv run python -m src.server.main  # Run server locally (port 8181)
uv run pytest           # Run all tests
uv run pytest tests/test_api_essentials.py -v  # Specific test
uv run ruff check        # Lint
uv run ruff check --fix  # Auto-fix linting
uv run mypy src/         # Type checking

# Docker operations
docker compose logs -f archon-server   # View server logs
docker compose logs -f archon-mcp      # View MCP server logs
docker compose restart archon-server   # Restart after changes
```

### Database Setup

Run this in your Supabase SQL Editor:
```sql
-- Copy and execute the contents of migration/complete_setup.sql
```

**Important**: Use the legacy service role key format (longer key) for cloud Supabase.

## Architecture Overview

### Microservices Structure

- **Frontend (port 3737)**: React + TypeScript + Vite + TailwindCSS
- **Main Server (port 8181)**: FastAPI with HTTP polling (no WebSockets)
- **MCP Server (port 8051)**: Lightweight HTTP-based MCP protocol server
- **Agents Service (port 8052)**: PydanticAI agents (optional, requires `--profile agents`)

All services communicate via HTTP APIs. No shared code dependencies between services.

### Frontend Architecture (Dual UI Strategy)

- **`/src/features`**: Modern vertical slice architecture with Radix UI + TanStack Query + Biome
- **`/src/components`**: Legacy components being migrated (ESLint)

#### Key Frontend Patterns

- **TanStack Query**: All data fetching, no prop drilling
- **Smart Polling**: HTTP polling with ETag caching, pauses when tab inactive
- **Vertical Slices**: Features own their sub-features (projects/tasks/documents)
- **Query Keys Factory**: Consistent cache invalidation patterns

### Backend Service Layer Pattern

```
API Route → Service → Database
```

- Routes in `src/server/api_routes/`
- Business logic in `src/server/services/`
- Database operations use Supabase client

### Database Schema (Supabase + pgvector)

Key tables:
- `archon_settings`: Configuration and encrypted API keys
- `archon_sources`: Crawled websites/documents metadata
- `archon_crawled_pages`: Document chunks with multi-dimensional embeddings
- `archon_code_examples`: Extracted code snippets with summaries
- `archon_projects/tasks`: Optional project management (toggle in settings)

## MCP Integration

### Available MCP Tools

When connected to Claude/Cursor/Windsurf:

- **Knowledge**: `rag_search_knowledge_base`, `rag_search_code_examples`, `rag_get_available_sources`
- **Projects**: `find_projects`, `manage_project` (create/update/delete)
- **Tasks**: `find_tasks`, `manage_task` (create/update/delete)
- **Documents**: `find_documents`, `manage_document` (create/update/delete)
- **Versions**: `find_versions`, `manage_version` (create/restore)

### MCP Connection

```bash
# Check MCP health
curl http://localhost:8051/health

# View MCP logs
docker compose logs -f archon-mcp
```

## Development Workflows

### Adding New Features

1. **Backend**: Add route in `api_routes/`, service in `services/`, update `main.py`
2. **Frontend**: Create in `src/features/[feature]/` with components, hooks, services, types
3. **MCP**: Add tools in `src/mcp_server/features/[feature]/[feature]_tools.py`

### Error Handling Philosophy (Beta)

- **Fail fast**: Service startup, auth, data corruption
- **Continue with logging**: Batch processing, background tasks, optional features
- **Never accept corrupted data**: Skip failed items, don't store zeros/nulls

### Testing Single Components

```bash
# Frontend
vitest run src/features/projects  # Test specific directory

# Backend
uv run pytest tests/test_api_essentials.py::TestSpecificFunction -v
```

## Environment Variables

Required in `.env`:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-legacy-service-key  # Use longer legacy format
```

Optional but recommended:
```bash
OPENAI_API_KEY=your-openai-key
ARCHON_SERVER_PORT=8181
ARCHON_MCP_PORT=8051
ARCHON_UI_PORT=3737
HOST=localhost
```

## Common Issues

- **Port conflicts**: Change ports in `.env`, both `ARCHON_SERVER_PORT` and `VITE_ARCHON_SERVER_PORT`
- **Hot reload not working**: Use `make dev` for best experience
- **MCP connection issues**: Check health endpoints, verify Supabase credentials
- **TypeScript errors**: Use `npm run biome:fix` for features, `npm run lint:files` for legacy

## Code Quality Standards

- **Frontend**: TypeScript strict mode, Biome (features) + ESLint (legacy), 120 char lines
- **Backend**: Python 3.12, Ruff linting, MyPy type checking, 120 char lines
- **Testing**: Vitest (frontend), Pytest (backend) with async support

---

## Embedding Generation & RAG System (Nov 2025 Update)

### Current System Configuration

**Hardware**: Mac Studio M4 Max with 128GB RAM
**Strategy**: 100% Local (Ollama-based)

#### Embedding Configuration
```sql
EMBEDDING_PROVIDER = ollama
EMBEDDING_MODEL = nomic-embed-text
EMBEDDING_DIMENSIONS = 768
```

#### LLM Configuration
```sql
LLM_PROVIDER = ollama
MODEL_CHOICE = qwen2.5-coder:7b
LLM_BASE_URL = http://host.docker.internal:11434/v1
```

#### RAG Features (All Enabled)
```sql
USE_CONTEXTUAL_EMBEDDINGS = true    -- LLM adds context to each chunk (slower but better quality)
USE_HYBRID_SEARCH = true            -- Vector + keyword search (no performance impact)
USE_AGENTIC_RAG = true              -- Code extraction with summaries (moderate LLM usage)
USE_RERANKING = true                -- Intelligent result ranking (no performance impact)
```

### Database Schema (Multi-Dimensional Embeddings)

The database supports multiple embedding dimensions for different models:

**Tables**: `archon_crawled_pages` and `archon_code_examples`

**Embedding Columns**:
- `embedding_384` - Small models (384-dim)
- `embedding_768` - Ollama/Google models (768-dim) ← Currently used
- `embedding_1024` - Ollama large models (1024-dim)
- `embedding_1536` - OpenAI standard models (1536-dim)
- `embedding_3072` - OpenAI large models (3072-dim)

**Tracking Columns**:
- `embedding_model` - Model name used (e.g., "nomic-embed-text")
- `embedding_dimension` - Dimension of embedding stored (e.g., 768)
- `llm_chat_model` - LLM used for processing (e.g., "qwen2.5-coder:7b")

**Indexes**:
- IVFFLAT vector indexes on 384/768/1024/1536 dimensions
- Regular B-tree indexes on tracking columns
- GIN indexes for hybrid search (tsvector + trigrams)

### Chunking Strategy

**Implementation**: Custom context-aware rule-based chunking
**Location**: `/python/src/server/services/storage/base_storage_service.py:39-120`

**Parameters**:
- Chunk size: 5000 characters (fixed)
- Chunk overlap: None
- Minimum chunk size: 200 characters (small chunks get combined)

**Boundary Detection** (priority order):
1. **Code blocks** (```) - Preserves complete code snippets
2. **Paragraphs** (`\n\n`) - Maintains context
3. **Sentences** (`. `) - Natural breaks
4. **Hard break** - Last resort at exactly 5000 chars

**Why this strategy**:
- ✅ Preserves code blocks (critical for technical docs)
- ✅ Context-aware (respects natural boundaries)
- ✅ Fast (no AI calls required)
- ✅ Deterministic (same input = same output)
- ⚠️ No overlap (could miss cross-chunk relationships)

### LLM Usage Breakdown

The LLM (qwen2.5-coder:7b) is used for 4 purposes:

#### 1. Source Summaries (Always)
- Generates 3-5 sentence summaries of documentation sources
- Runs once per source when crawled
- **Token usage**: ~200-500 tokens per source
- **Example**: "Pydantic is a data validation library for Python..."

#### 2. Source Titles (Always)
- Generates user-friendly titles from URLs
- Runs once per source
- **Token usage**: ~100-200 tokens per source
- **Example**: "docs.n8n.io" → "N8N Workflow Automation Documentation"

#### 3. Contextual Embeddings (Optional - Currently ENABLED)
- Adds context to each chunk before embedding
- **Setting**: `USE_CONTEXTUAL_EMBEDDINGS = true`
- **Token usage**: ~100-200 tokens PER CHUNK
- **Impact**: Makes search more accurate but significantly slower
- **Example**:
  ```
  Chunk: "Use the apply() method"
  + Context: "This describes DataFrame transformation in Pandas"
  → Better search retrieval
  ```

#### 4. Code Summaries (Optional - Currently ENABLED)
- Generates natural language summaries of code examples
- **Setting**: `USE_AGENTIC_RAG = true`
- **Token usage**: ~100-300 tokens per code block
- **Example**: Summarizes what a code snippet does

### Performance Comparison

| Configuration | Speed (138 pages) | Quality | LLM Calls |
|---------------|-------------------|---------|-----------|
| **Contextual ON** | ~2 hours | Excellent | ~170K tokens |
| **Contextual OFF** | ~10-20 min | Very Good | ~5K tokens |

Both are 100% local and free - the question is speed vs. quality trade-off.

### Current Knowledge Base Status

**Total Embedded**: 1,709 chunks across 4 sources
**Embedding Model**: nomic-embed-text (768-dim)
**All embeddings**: 100% complete

**Sources**:
1. **Pydantic Documentation** - 812 chunks
2. **N8N Documentation** - 475 chunks
3. **Mediversityglobal** - 21 chunks
4. **Astro Documentation** - 1 chunk
5. **Astro Documentation Guide** - 0 chunks (config issue)

### Recommended Ollama Models

**Current Setup** (Optimal):
- `nomic-embed-text` - Embeddings (274 MB) ✅
- `qwen2.5-coder:7b` - LLM (4.7 GB) ✅
- `deepseek-r1:7b` - Reasoning backup (4.7 GB)
- `qwen3:8b` - General purpose backup (5.2 GB)

**Upgrade Options** (if you want better quality):
- `qwen2.5-coder:14b` - Better code understanding (7.7 GB)
- `mxbai-embed-large` - Better embeddings (1024-dim, 669 MB)
- `llama3.3:70b-q4_K_M` - Flagship model (40 GB quantized)

**Models Removed** (redundant):
- ❌ `gemma2:9b` - Removed to free space
- ❌ `gemma3:1b` - Too small, removed
- ❌ `llama3:8b` - Outdated, removed

### Embedding Generation Process

```bash
# Trigger embedding generation for a source (via API)
curl -X POST "http://localhost:9181/api/knowledge-items/{source_id}/refresh" \
  -H "Content-Type: application/json"

# Monitor progress (database check)
docker exec archon-server python3 -c "
from src.server.config.database import get_supabase_client
supabase = get_supabase_client()
result = supabase.table('archon_crawled_pages').select('*', count='exact').execute()
total = result.count
result_emb = supabase.table('archon_crawled_pages').select('*', count='exact').not_.is_('embedding_768', 'null').execute()
embedded = result_emb.count
print(f'Total: {total}, Embedded: {embedded}, Progress: {round(embedded/total*100 if total > 0 else 0, 1)}%')
"

# Check server logs for errors
docker compose logs archon-server --tail 50 | grep -i "embedding\|error"
```

### Common Schema Fixes Applied (Nov 2025)

If you encounter missing column errors during embedding generation:

```sql
-- Add multi-dimensional embedding columns
ALTER TABLE archon_crawled_pages
ADD COLUMN IF NOT EXISTS embedding_384 VECTOR(384),
ADD COLUMN IF NOT EXISTS embedding_768 VECTOR(768),
ADD COLUMN IF NOT EXISTS embedding_1024 VECTOR(1024),
ADD COLUMN IF NOT EXISTS embedding_1536 VECTOR(1536),
ADD COLUMN IF NOT EXISTS embedding_3072 VECTOR(3072);

-- Add model tracking columns
ALTER TABLE archon_crawled_pages
ADD COLUMN IF NOT EXISTS llm_chat_model TEXT,
ADD COLUMN IF NOT EXISTS embedding_model TEXT,
ADD COLUMN IF NOT EXISTS embedding_dimension INTEGER;

-- Repeat for archon_code_examples
ALTER TABLE archon_code_examples
ADD COLUMN IF NOT EXISTS embedding_384 VECTOR(384),
ADD COLUMN IF NOT EXISTS embedding_768 VECTOR(768),
ADD COLUMN IF NOT EXISTS embedding_1024 VECTOR(1024),
ADD COLUMN IF NOT EXISTS embedding_1536 VECTOR(1536),
ADD COLUMN IF NOT EXISTS embedding_3072 VECTOR(3072),
ADD COLUMN IF NOT EXISTS llm_chat_model TEXT,
ADD COLUMN IF NOT EXISTS embedding_model TEXT,
ADD COLUMN IF NOT EXISTS embedding_dimension INTEGER;
```

### Testing RAG Search

Once embeddings are complete:

```bash
# Via UI
# Navigate to: http://localhost:9737 → Knowledge Base → Search
# Try queries like:
# - "How to use PydanticAI with async?"
# - "N8N workflow examples"
# - "Astro component syntax"

# Via MCP Tools (if connected to Claude Code)
# Use: archon:rag_search_knowledge_base
# Use: archon:rag_search_code_examples
```

### Troubleshooting Embedding Generation

**Error: "Could not find the 'embedding_768' column"**
- Solution: Run the schema fix above to add missing columns
- Restart services: `docker compose restart`

**Error: "Could not find the 'embedding_dimension' column"**
- Solution: Run the schema fix to add tracking columns
- Restart services: `docker compose restart`

**Slow embedding generation**
- Check if `USE_CONTEXTUAL_EMBEDDINGS = true` (adds 10x processing time)
- Consider disabling: `UPDATE archon_settings SET value = 'false' WHERE key = 'USE_CONTEXTUAL_EMBEDDINGS';`
- Restart services to apply changes

**No embeddings being generated**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Verify nomic-embed-text is installed: `ollama list | grep nomic`
- Check server logs: `docker compose logs archon-server | grep -i error`
- Verify EMBEDDING_PROVIDER setting: `SELECT * FROM archon_settings WHERE key = 'EMBEDDING_PROVIDER';`

### Optimizing for Your Hardware

With Mac Studio M4 Max (128GB RAM), you can:
- ✅ Run 70B models comfortably
- ✅ Process embeddings very fast (CPU-optimized)
- ✅ Run multiple models simultaneously
- ✅ Use larger embedding models (1024-dim)

**Recommendation**: Keep current setup (qwen2.5-coder:7b + nomic-embed-text) - it's optimal for speed and quality balance.