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