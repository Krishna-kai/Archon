# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Core Commands

### Environment Setup
```bash
# Clone and initial setup
git clone https://github.com/coleam00/archon.git
cd archon
cp .env.example .env
# Edit .env with Supabase credentials

# Database setup (run in Supabase SQL Editor)
# Copy and execute: migration/complete_setup.sql
```

### Development Workflow
```bash
# Start all services (production-like)
docker-compose up --build -d

# Development with hot reload
# Backend services
docker-compose up archon-server archon-mcp archon-agents --build
# Frontend (separate terminal)
cd archon-ui-main && npm run dev

# View logs
docker-compose logs -f
docker-compose logs archon-server
```

### Frontend Development (archon-ui-main/)
```bash
npm run dev              # Development server on port 3737
npm run build            # Production build
npm run lint             # ESLint
npm run test             # Vitest tests
npm run test:ui          # Vitest UI
npm run test:coverage    # Coverage report with summary
```

### Backend Development (python/)
```bash
# Using uv package manager (Python 3.12+ required)
uv sync                  # Install/sync dependencies
uv run pytest           # Run all tests
uv run pytest tests/test_api_essentials.py -v  # Single test file
uv run ruff check        # Lint Python code
uv run mypy src/         # Type checking

# Direct service execution (for debugging)
cd python && uv run python -m src.server.main
cd python && uv run python -m src.mcp.server
cd python && uv run python -m src.agents.server
```

### Service Management
```bash
# Restart specific services
docker-compose restart archon-server
docker-compose restart archon-mcp

# Check service health
curl http://localhost:8181/health  # Server
curl http://localhost:8051/health  # MCP Server  
curl http://localhost:8052/health  # Agents Service
curl http://localhost:3737         # Frontend

# Database reset (DESTRUCTIVE)
# Run migration/RESET_DB.sql then migration/complete_setup.sql in Supabase
docker-compose down && docker-compose up -d
```

## Architecture Overview

### Microservices Structure
Archon V2 is a true microservices architecture with 4 independent services:

1. **Frontend (archon-ui, port 3737)**: React + TypeScript + Vite + TailwindCSS
2. **Server (archon-server, port 8181)**: FastAPI + Socket.IO for APIs and real-time updates  
3. **MCP Server (archon-mcp, port 8051)**: Lightweight HTTP wrapper for Model Context Protocol
4. **Agents Service (archon-agents, port 8052)**: PydanticAI agents for ML/AI operations

### Service Communication
- **HTTP-based**: All inter-service communication via HTTP APIs
- **Socket.IO**: Real-time updates from Server to Frontend
- **MCP Protocol**: AI clients connect to MCP Server via SSE/stdio
- **No Direct Imports**: Services are truly independent containers

### Database
- **Supabase**: PostgreSQL + pgvector for embeddings
- **Key Tables**: sources, documents, projects, tasks, code_examples
- **Vector Search**: Semantic search with contextual embeddings

### Key Ports (configurable via .env)
- Frontend UI: 3737
- Server API: 8181  
- MCP Server: 8051
- Agents Service: 8052

## Development Architecture

### Frontend Structure (archon-ui-main/src/)
- `components/` - Reusable UI components
- `pages/` - Main application pages  
- `services/` - API communication layer
- `hooks/` - Custom React hooks
- `contexts/` - React context providers
- `types/` - TypeScript type definitions

### Backend Structure (python/src/)
- `server/` - Main FastAPI application
  - `api_routes/` - HTTP route handlers
  - `services/` - Business logic layer
  - `middleware/` - Request/response middleware
- `mcp/` - Model Context Protocol server implementation
- `agents/` - PydanticAI agent implementations

### Code Quality Standards
- **Python 3.12** with 120 character line length
- **Ruff** for linting with comprehensive rule set
- **Mypy** for type checking (allow missing imports from 3rd party)
- **Auto-formatting** maintained via Ruff format
- **Testing** with pytest (backend) and Vitest (frontend)

## Error Handling Philosophy

### Fail Fast and Loud
These should crash immediately with clear errors:
- Service startup failures
- Missing configuration/environment variables
- Database connection failures
- Authentication/authorization failures  
- Data corruption or validation errors
- Invalid data that would corrupt state

### Complete but Log Failures
These should continue processing but report detailed failures:
- Batch operations (crawling, document processing)
- Background tasks (embedding generation)
- WebSocket events
- Optional features
- External API calls (with retry logic)

### Never Accept Corrupted Data
When continuing despite failures, skip failed items entirely rather than storing corrupted/partial data.

## MCP Integration

### Available Tools
When connected via MCP (Cursor, Claude Code, etc.):
- `archon:perform_rag_query` - Search knowledge base
- `archon:search_code_examples` - Find code snippets  
- `archon:manage_project` - Project operations
- `archon:manage_task` - Task management
- `archon:get_available_sources` - List knowledge sources

### MCP Server Debugging
```bash
# Check MCP health
curl http://localhost:8051/health

# View MCP logs
docker-compose logs archon-mcp

# Test via UI
# Navigate to http://localhost:3737 → MCP Dashboard
```

## Key Features

### Knowledge Management
- Smart web crawling with sitemap detection
- Document processing (PDF, DOCX, MD) with chunking
- Code example extraction and indexing
- Vector search with multiple RAG strategies
- Real-time crawling progress via WebSocket

### AI Integration  
- Multi-LLM support (OpenAI, Gemini, Ollama)
- RAG strategies: hybrid search, contextual embeddings, reranking
- PydanticAI agents for streaming responses
- MCP protocol for AI coding assistant integration

### Project Management (Optional)
- Hierarchical projects with tasks
- AI-assisted project/task creation
- Real-time progress tracking
- Feature-based task organization

## Development Workflow

### Adding New API Endpoints
1. Create route handler in `python/src/server/api_routes/`
2. Add business logic in `python/src/server/services/`
3. Include router in `python/src/server/main.py`
4. Update frontend service in `archon-ui-main/src/services/`

### Adding New UI Components
1. Create component in `archon-ui-main/src/components/`
2. Add to appropriate page in `archon-ui-main/src/pages/`
3. Include API calls in services layer
4. Add tests in `archon-ui-main/test/`

### Socket.IO Events
Real-time events broadcast from server:
- `crawl_progress` - Website crawling status
- `project_creation_progress` - Project setup
- `task_update` - Task status changes
- `knowledge_update` - Knowledge base updates

## Environment Configuration

### Required Variables (.env)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here
```

### Optional Configuration
```bash
# API Keys (can be set via Settings UI)
OPENAI_API_KEY=your-openai-key
LOGFIRE_TOKEN=your-logfire-token

# Service Ports
HOST=localhost
ARCHON_SERVER_PORT=8181
ARCHON_MCP_PORT=8051
ARCHON_AGENTS_PORT=8052
ARCHON_UI_PORT=3737

# Debugging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Important Notes

- **Alpha Development**: No backwards compatibility - remove deprecated code immediately
- **Local Deployment**: Each user runs their own instance
- **Projects Optional**: Feature can be toggled in Settings UI  
- **Hot Reload**: Backend services have auto-reload enabled in development
- **Package Management**: Backend uses `uv` for Python dependencies
- **Container Independence**: Each service has minimal dependencies for lightweight containers

## Specialized Rules Integration

### Claude Rules (CLAUDE.md)
This project includes comprehensive Claude-specific guidance covering:
- Alpha development principles with detailed error handling
- Microservices architecture patterns
- Development commands and workflows
- API endpoint structure and Socket.IO events

### Archon Workflow (CLAUDE-ARCHON.md)  
Contains Archon-specific development patterns:
- Task-driven development with MCP integration
- Research-driven coding using Archon's knowledge base
- Code operations with Serena MCP integration
- Project lifecycle management

These specialized files provide detailed context for AI coding assistants working with this codebase.
