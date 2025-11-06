# Integration & Upstream Merge Plan

**Date**: 2025-01-06
**Status**: Phase 1 Complete - Integration Working

## Current Status

### ✅ Working Features
- MinerU HTTP service running on port 8055
- Successfully processing PDFs (13 pages tested)
- API endpoint: `/api/documents/upload`
- Docker services: archon-server (9181), archon-mcp (9051), archon-ui (9737)

### 📦 Implemented But Not Integrated
- ImageProcessingAgent (PydanticAI-based)
- Comprehensive test suite (9/9 passing)
- Usage examples in `/python/examples/`

### 🔄 Upstream Status
- 3 commits behind upstream (coleam00/archon)
- Security fixes (Docker socket CVE-2025-9074)
- Bug fix (zero uptime HTTP health check)
- Low risk of conflicts

---

## Phase 2: Commit Working Changes

### Step 1: Review Changes
```bash
git diff python/src/server/api_routes/knowledge_api.py
git diff python/src/server/services/mineru_http_client.py
git diff python/src/server/services/mineru_service.py
```

### Step 2: Stage Modified Files
```bash
# Core integration files
git add python/src/server/api_routes/knowledge_api.py
git add python/src/server/services/mineru_http_client.py
git add python/src/server/services/mineru_service.py
git add python/src/server/config/service_discovery.py
git add python/src/server/main.py

# Docker configuration
git add docker-compose.yml
git add python/Dockerfile.server
git add python/Dockerfile.mcp

# Dependencies
git add python/pyproject.toml
git add python/uv.lock

# Environment example
git add .env.example

# Frontend changes
git add archon-ui-main/src/features/knowledge/components/AddKnowledgeDialog.tsx
git add archon-ui-main/src/features/knowledge/types/knowledge.ts

# MinerU service startup script
git add python/start_mineru_service.sh
```

### Step 3: Stage New Files (Optional - for PydanticAI integration)
```bash
# New ImageProcessingAgent (when ready to integrate)
# git add python/src/agents/image_processing_agent.py
# git add python/tests/test_image_processing_agent.py
# git add python/examples/image_processing_example.py

# Documentation
# git add PRPs/ai_docs/IMAGE_PROCESSING_AGENT_IMPLEMENTATION.md
# git add PRPs/ai_docs/MINERU_PYDANTIC_REFACTORING.md
```

### Step 4: Commit
```bash
git commit -m "feat: Add MinerU HTTP service integration for PDF processing

- Integrate MinerU v2.6.4 HTTP service for document processing
- Add mineru_http_client for native service communication
- Update knowledge upload API to support MinerU processing
- Configure service discovery for MinerU endpoint
- Add Docker configuration for MinerU service
- Update frontend to pass mineru processing flags

Tested with 13-page research paper - successful extraction of:
- Text content and markdown conversion
- Tables (6 tables with OCR)
- Formulas (93 formulas with MFR)
- Images and charts

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 3: Merge Upstream Security Fixes

### Step 1: Fetch Latest Upstream
```bash
git fetch upstream
```

### Step 2: Review Upstream Changes
```bash
# See what will be merged
git log --oneline HEAD..upstream/main

# Detailed view
git log --stat HEAD..upstream/main
```

### Step 3: Merge Upstream
```bash
# Create backup branch first (safety)
git branch backup-before-upstream-merge

# Merge upstream
git merge upstream/main -m "merge: Pull security fixes from upstream

Merging 3 commits from coleam00/archon:
- Security: Remove Docker socket mounting (CVE-2025-9074)
- Fix: Zero uptime handling in HTTP health check
- Merge pull request #834

Local features preserved:
- MinerU HTTP service integration
- ImageProcessingAgent (PydanticAI)
- OCR enhancements

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 4: Handle Merge Conflicts (if any)

Expected conflict areas:
- `docker-compose.yml` - Port mappings and service definitions
- `python/src/server/main.py` - Service initialization
- `.env.example` - Environment variables

Resolution strategy:
1. Keep both changes where possible
2. Prefer upstream for security fixes
3. Keep your local feature additions
4. Test after resolution

---

## Phase 4: Test After Merge

### Step 1: Rebuild Docker Services
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Step 2: Verify Services
```bash
# Check all services running
docker ps

# Check server logs
docker logs archon-server --tail=50

# Test health endpoints
curl http://localhost:9181/health
curl http://localhost:9051/health
```

### Step 3: Test PDF Upload
```bash
# Navigate to PDF directory
cd "/Users/krishna/Downloads/Krishna-Mahendra Experiement/Histopathology Project/Research Papers"

# Test upload with MinerU
curl -X POST http://localhost:9181/api/documents/upload \
  -F "file=@Copy of Dual U-Net for the Segmentation of Overlapping Glioma Nuclei.pdf" \
  -F "use_mineru=true" \
  -F "extract_charts=true" \
  -F "chart_provider=auto" \
  -F "knowledge_type=technical"

# Should return: {"success":true,"progressId":"...","message":"Document upload started"}
```

### Step 4: Monitor Processing
```bash
# Check MinerU service logs
docker logs archon-server -f | grep -i mineru

# Or if running locally
tail -f python/mineru_service.log
```

---

## Phase 5: Integration of ImageProcessingAgent (Future)

### When Ready
1. Test ImageProcessingAgent with integration tests
2. Add feature flag: `USE_PYDANTIC_IMAGE_AGENT`
3. Update `knowledge_api.py` to use agent conditionally
4. Monitor side-by-side with legacy service
5. Full migration after validation

### Test Commands
```bash
cd python

# Run unit tests
uv run pytest tests/test_image_processing_agent.py -v

# Run example
uv run python examples/image_processing_example.py
```

---

## Rollback Plan

If something breaks after upstream merge:

### Option 1: Quick Rollback
```bash
git reset --hard backup-before-upstream-merge
docker compose down && docker compose up -d --build
```

### Option 2: Identify Issue
```bash
# Compare with backup
git diff backup-before-upstream-merge

# Check specific conflicts
git diff backup-before-upstream-merge docker-compose.yml
```

### Option 3: Selective Undo
```bash
# Undo specific file
git checkout backup-before-upstream-merge -- path/to/file

# Recommit
git commit -m "fix: Restore working version of conflicted file"
```

---

## Success Criteria

### Before Upstream Merge
- [x] MinerU service processing PDFs successfully
- [x] API endpoint responding correctly
- [x] Docker services running
- [ ] Changes committed with proper message
- [ ] Backup branch created

### After Upstream Merge
- [ ] All services start without errors
- [ ] PDF upload works with MinerU
- [ ] No regressions in existing features
- [ ] Security fixes applied
- [ ] No merge artifacts in code

---

## Notes

- Keep local changes (don't push to coleam00/archon)
- Push to origin (Krishna-kai/Archon) after testing
- Document any issues encountered
- Update this plan as needed

---

## Maintenance

### Regular Upstream Sync
```bash
# Check for new commits
git fetch upstream
git log --oneline HEAD..upstream/main

# If safe to merge
git merge upstream/main
```

### Before Each Merge
1. Commit local changes
2. Create backup branch
3. Review upstream changes
4. Test after merge
