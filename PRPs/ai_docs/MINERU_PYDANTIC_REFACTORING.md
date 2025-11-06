# MinerU Service Refactoring with PydanticAI

## Executive Summary

This document proposes refactoring the MinerU PDF processing service to follow PydanticAI best practices already established in the Archon codebase. The refactoring will improve error handling, add progress reporting, implement proper dependency injection, and create a consistent agent-based interface.

## Current Implementation Issues

### 1. No Agent Pattern
**Current**: `MinerUService` and `MinerUHttpClient` are plain classes
```python
# python/src/server/services/mineru_service.py
class MinerUService:
    def __init__(self, mineru_path: Optional[str] = None):
        # Direct initialization, no dependency injection
        self.mineru_path = mineru_path
        self.timeout = 300.0
```

**Issue**:
- No rate limiting for AI calls (chart extraction)
- No retry logic for transient failures
- No progress callbacks for long-running operations
- No structured error handling

### 2. Inconsistent Return Types
**Current**: Returns `Tuple[bool, Dict]`
```python
async def process_pdf(...) -> Tuple[bool, Dict]:
    # Returns unstructured dict with optional fields
    return True, {
        "success": True,
        "markdown": "...",
        "metadata": {...},
        "charts": [...]  # Inconsistent structure
    }
```

**Issue**:
- No type safety for response fields
- Unclear what fields are required vs optional
- Different code paths return different dict structures
- Hard to validate in downstream code

### 3. No Dependency Injection
**Current**: Hardcoded configuration
```python
def __init__(self, mineru_path: Optional[str] = None):
    if mineru_path is None:
        # Auto-detect mineru in venv or system PATH
        venv_mineru = Path(__file__).parent.parent.parent.parent / ".venv" / "bin" / "mineru"
```

**Issue**:
- Hard to test (can't mock filesystem paths)
- Hard to configure for different environments
- Tight coupling to specific directory structure

### 4. Mixed HTTP and CLI Logic
**Current**: Two separate classes with duplicate code
- `MinerUService` - CLI-based (lines 20-448)
- `MinerUHttpClient` - HTTP-based (lines 1-148)

**Issue**:
- Code duplication between CLI and HTTP implementations
- No shared error handling
- Inconsistent logging patterns

### 5. No Progress Reporting
**Current**: Only log messages
```python
logger.info(f"Processing PDF with MinerU: {filename}")
# ... long-running process ...
logger.info(f"MinerU processing complete: {filename}")
```

**Issue**:
- Users can't see progress in UI
- No way to track multi-step operations
- Upload requests appear to hang

## Existing PydanticAI Patterns in Archon

### Pattern 1: BaseAgent with Rate Limiting
**Reference**: `python/src/agents/base_agent.py`

```python
class BaseAgent(ABC, Generic[DepsT, OutputT]):
    def __init__(self, model: str = "openai:gpt-4o", retries: int = 3, enable_rate_limiting: bool = True):
        # Automatic rate limiting with exponential backoff
        self.rate_limiter = RateLimitHandler(max_retries=retries)
        self._agent = self._create_agent(**agent_kwargs)

    async def run(self, user_prompt: str, deps: DepsT) -> OutputT:
        if self.rate_limiter:
            return await self.rate_limiter.execute_with_rate_limit(
                self._run_agent, user_prompt, deps, progress_callback=getattr(deps, "progress_callback", None)
            )
```

**Benefits**:
- Automatic retry on rate limits (429 errors)
- Exponential backoff with configurable max retries
- Progress callback support built-in
- Timeout handling (120s default)

### Pattern 2: Structured Dependencies
**Reference**: `python/src/agents/document_agent.py`

```python
@dataclass
class DocumentDependencies(ArchonDependencies):
    project_id: str = ""
    current_document_id: str | None = None
    progress_callback: Any | None = None  # Callback for progress updates
```

**Benefits**:
- Type-safe dependencies
- Default values for optional fields
- Easy to extend without breaking existing code
- Clear contract for what dependencies are needed

### Pattern 3: Pydantic Output Models
**Reference**: `python/src/agents/document_agent.py`

```python
class DocumentOperation(BaseModel):
    operation_type: str = Field(description="Type of operation")
    document_id: str | None = Field(description="ID of the document affected")
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable message")
    content_preview: str | None = Field(description="Preview of content")
```

**Benefits**:
- Type validation at runtime
- Clear documentation of fields
- JSON serialization built-in
- IDE autocomplete support

### Pattern 4: Agent Tools with Context
**Reference**: `python/src/agents/document_agent.py:228-288`

```python
@agent.tool
async def create_document(
    ctx: RunContext[DocumentDependencies],
    title: str,
    document_type: str,
    content_description: str,
) -> str:
    # Send progress update if callback available
    if ctx.deps.progress_callback:
        await ctx.deps.progress_callback({
            "step": "ai_generation",
            "log": f"📝 Creating {document_type}: {title}",
        })

    # ... do work ...

    if ctx.deps.progress_callback:
        await ctx.deps.progress_callback({
            "step": "ai_generation",
            "log": f"✅ Successfully created {document_type}: {title}",
        })
```

**Benefits**:
- Access to dependencies via context
- Progress reporting at each step
- Clear error messages with emojis
- Consistent logging pattern

## Proposed Refactoring

### New ImageProcessingAgent

**Location**: `python/src/agents/image_processing_agent.py`

```python
"""
ImageProcessingAgent - PDF Extraction and Image Analysis with PydanticAI

This agent handles PDF processing with MinerU and image analysis with Ollama,
following established PydanticAI patterns in the Archon codebase.
"""

import base64
import logging
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .base_agent import ArchonDependencies, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ImageProcessingDependencies(ArchonDependencies):
    """Dependencies for image processing operations."""

    mineru_service_url: str | None = None  # HTTP service URL if available
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2-vision"
    extract_charts: bool = False
    chart_provider: str = "auto"
    device: str = "mps"  # Apple Silicon GPU
    lang: str = "en"
    progress_callback: Any | None = None


class ExtractedImage(BaseModel):
    """Structured image data extracted from PDF."""

    name: str = Field(description="Image filename")
    base64_data: str = Field(description="Base64-encoded image data")
    page_number: int | None = Field(description="PDF page number (1-indexed)")
    image_index: int = Field(description="Order within page (0-indexed)")
    mime_type: str = Field(description="Image MIME type", default="image/png")
    width: int | None = Field(description="Image width in pixels", default=None)
    height: int | None = Field(description="Image height in pixels", default=None)

    # Ollama analysis results (populated by analyze_with_ollama tool)
    ocr_text: str | None = Field(description="Text extracted from image", default=None)
    description: str | None = Field(description="Image description", default=None)
    classification: str | None = Field(description="Image type classification", default=None)
    confidence: float | None = Field(description="Classification confidence", default=None)


class ProcessingResult(BaseModel):
    """Structured output for PDF processing operations."""

    success: bool = Field(description="Whether processing succeeded")
    filename: str = Field(description="Original filename")
    markdown_text: str = Field(description="Extracted markdown text")
    images: list[ExtractedImage] = Field(description="Extracted and analyzed images")
    metadata: dict[str, Any] = Field(description="Processing metadata")
    message: str = Field(description="Status message")
    error: str | None = Field(description="Error message if failed", default=None)

    # Statistics
    page_count: int = Field(description="Number of pages processed", default=0)
    formula_count: int = Field(description="Number of formulas extracted", default=0)
    table_count: int = Field(description="Number of tables extracted", default=0)
    image_count: int = Field(description="Number of images extracted", default=0)
    processing_time_seconds: float | None = Field(description="Processing duration", default=None)


class ImageProcessingAgent(BaseAgent[ImageProcessingDependencies, ProcessingResult]):
    """
    Agent for PDF extraction and image analysis.

    Capabilities:
    - Extract text, formulas, tables from PDFs using MinerU
    - Extract and encode images with metadata
    - Analyze images with Ollama for OCR and classification
    - Report progress during long-running operations
    - Automatic retry on failures with rate limiting
    """

    def __init__(self, model: str = "openai:gpt-4o", **kwargs):
        super().__init__(
            model=model,
            name="ImageProcessingAgent",
            retries=3,
            enable_rate_limiting=True,
            **kwargs
        )

    def _create_agent(self, **kwargs) -> Agent:
        """Create the PydanticAI agent with tools."""

        agent = Agent(
            model=self.model,
            deps_type=ImageProcessingDependencies,
            result_type=ProcessingResult,
            system_prompt="""You are an Image Processing Agent that extracts and analyzes content from PDF documents.

**Your Capabilities:**
- Extract text, formulas, and tables from PDFs using MinerU
- Extract images with proper encoding and metadata
- Analyze images using Ollama vision models for OCR and classification
- Track progress and report detailed status updates
- Handle errors gracefully with retries

**Your Approach:**
1. **Process PDF** - Use MinerU to extract structured content
2. **Extract Images** - Identify and encode all images with metadata
3. **Analyze Images** - Use Ollama to perform OCR and classification
4. **Report Progress** - Keep user informed of processing steps
5. **Return Results** - Provide structured output with all extracted content

**Progress Reporting:**
- "🔄 Processing PDF with MinerU..."
- "📊 Extracting formulas and tables..."
- "🖼️ Found X images, analyzing..."
- "🤖 Analyzing image Y with Ollama..."
- "✅ Processing complete!"

**Error Handling:**
- Retry on transient failures (rate limits, network errors)
- Skip problematic images and continue processing
- Provide detailed error messages for debugging
- Never return partial results without clear indication""",
            **kwargs,
        )

        # Register tools
        @agent.tool
        async def process_with_mineru(
            ctx: RunContext[ImageProcessingDependencies],
            file_content_base64: str,
            filename: str,
        ) -> str:
            """Process PDF with MinerU to extract text, formulas, tables, and images."""
            try:
                if ctx.deps.progress_callback:
                    await ctx.deps.progress_callback({
                        "step": "pdf_extraction",
                        "log": f"🔄 Processing PDF with MinerU: {filename}"
                    })

                # Decode PDF content
                file_bytes = base64.b64decode(file_content_base64)

                # Get appropriate service (HTTP or CLI)
                from ..services.mineru_service import get_mineru_service
                mineru_service = get_mineru_service()

                # Process PDF
                success, result = await mineru_service.process_pdf(
                    file_content=file_bytes,
                    filename=filename,
                    device=ctx.deps.device,
                    lang=ctx.deps.lang,
                    extract_charts=ctx.deps.extract_charts,
                    chart_provider=ctx.deps.chart_provider,
                )

                if not success:
                    error_msg = result.get("error", "Unknown error")
                    if ctx.deps.progress_callback:
                        await ctx.deps.progress_callback({
                            "step": "pdf_extraction",
                            "log": f"❌ MinerU failed: {error_msg}"
                        })
                    return f"Processing failed: {error_msg}"

                # Extract statistics
                metadata = result.get("metadata", {})
                formula_count = metadata.get("formulas_count", 0)
                table_count = metadata.get("tables_count", 0)
                image_count = len(result.get("charts", []))

                if ctx.deps.progress_callback:
                    await ctx.deps.progress_callback({
                        "step": "pdf_extraction",
                        "log": f"✅ Extracted: {formula_count} formulas, {table_count} tables, {image_count} images"
                    })

                # Return JSON result for agent to parse
                import json
                return json.dumps({
                    "markdown": result.get("markdown", ""),
                    "images": result.get("charts", []),
                    "metadata": metadata,
                })

            except Exception as e:
                logger.error(f"MinerU processing failed: {e}", exc_info=True)
                return f"Error: {str(e)}"

        @agent.tool
        async def analyze_image_with_ollama(
            ctx: RunContext[ImageProcessingDependencies],
            image_base64: str,
            image_name: str,
        ) -> str:
            """Analyze image with Ollama for OCR and classification."""
            try:
                if ctx.deps.progress_callback:
                    await ctx.deps.progress_callback({
                        "step": "image_analysis",
                        "log": f"🤖 Analyzing {image_name} with Ollama..."
                    })

                # Call Ollama vision API
                import httpx

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{ctx.deps.ollama_base_url}/api/generate",
                        json={
                            "model": ctx.deps.ollama_model,
                            "prompt": """Analyze this image and provide:
1. OCR: Extract any visible text
2. Description: Describe what you see
3. Classification: Classify the image type (diagram, chart, photo, equation, table, etc.)

Format your response as JSON:
{
  "ocr_text": "extracted text here",
  "description": "image description",
  "classification": "image type",
  "confidence": 0.95
}""",
                            "images": [image_base64],
                            "stream": False,
                        }
                    )

                    if response.status_code != 200:
                        return f"Ollama error: HTTP {response.status_code}"

                    result = response.json()
                    analysis_text = result.get("response", "{}")

                    if ctx.deps.progress_callback:
                        await ctx.deps.progress_callback({
                            "step": "image_analysis",
                            "log": f"✅ Analyzed {image_name}"
                        })

                    return analysis_text

            except Exception as e:
                logger.error(f"Ollama analysis failed for {image_name}: {e}")
                return f"Analysis failed: {str(e)}"

        return agent

    def get_system_prompt(self) -> str:
        """Get the base system prompt for this agent."""
        return "Image Processing Agent for PDF extraction and analysis."

    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        **kwargs
    ) -> ProcessingResult:
        """
        Process a PDF document and return structured results.

        Args:
            file_content: Raw PDF bytes
            filename: Original filename
            **kwargs: Additional configuration (mineru_service_url, device, etc.)

        Returns:
            Structured ProcessingResult with all extracted content
        """
        import time
        start_time = time.time()

        # Create dependencies
        deps = ImageProcessingDependencies(
            mineru_service_url=kwargs.get("mineru_service_url"),
            ollama_base_url=kwargs.get("ollama_base_url", "http://localhost:11434"),
            ollama_model=kwargs.get("ollama_model", "llama3.2-vision"),
            extract_charts=kwargs.get("extract_charts", False),
            chart_provider=kwargs.get("chart_provider", "auto"),
            device=kwargs.get("device", "mps"),
            lang=kwargs.get("lang", "en"),
            progress_callback=kwargs.get("progress_callback"),
        )

        # Encode file content for agent
        import base64
        file_base64 = base64.b64encode(file_content).decode()

        # Create user prompt for agent
        user_prompt = f"""Process the PDF document '{filename}' and analyze all extracted images.

Steps:
1. Use process_with_mineru tool to extract content
2. For each extracted image, use analyze_image_with_ollama tool
3. Return complete ProcessingResult with all analysis data"""

        try:
            # Run agent with rate limiting and retries
            result = await self.run(user_prompt, deps)

            # Calculate processing time
            processing_time = time.time() - start_time
            result.processing_time_seconds = processing_time

            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)

            # Return error result
            return ProcessingResult(
                success=False,
                filename=filename,
                markdown_text="",
                images=[],
                metadata={},
                message=f"Processing failed: {str(e)}",
                error=str(e),
            )


# Singleton instance
_agent_instance: ImageProcessingAgent | None = None


def get_image_processing_agent() -> ImageProcessingAgent:
    """Get or create ImageProcessingAgent singleton instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ImageProcessingAgent()
    return _agent_instance
```

## Migration Strategy

### Phase 1: Create Agent (Current Phase)
- [ ] Create `image_processing_agent.py` with full implementation
- [ ] Add comprehensive tests for agent tools
- [ ] Verify Ollama integration works
- [ ] Test progress callback reporting

### Phase 2: Parallel Deployment
- [ ] Update `get_mineru_service()` to optionally return agent
- [ ] Add feature flag `USE_IMAGE_PROCESSING_AGENT`
- [ ] Run both implementations in parallel (compare results)
- [ ] Monitor for differences in production

### Phase 3: Gradual Migration
- [ ] Update `knowledge_api.py` to use agent
- [ ] Update `document_processing.py` to use agent
- [ ] Migrate progress tracking to use agent callbacks
- [ ] Update frontend to display new progress format

### Phase 4: Deprecation
- [ ] Mark `MinerUService` as deprecated
- [ ] Mark `MinerUHttpClient` as deprecated
- [ ] Remove old implementations
- [ ] Update documentation

## Benefits of Refactoring

### 1. Type Safety
**Before**: `Tuple[bool, Dict]` with untyped fields
**After**: `ProcessingResult` with validated Pydantic fields

### 2. Progress Reporting
**Before**: Only log messages
**After**: Real-time UI updates with emoji indicators

### 3. Error Handling
**Before**: Mixed exceptions, returns, and logging
**After**: Automatic retries with exponential backoff

### 4. Testability
**Before**: Hard to test (filesystem dependencies)
**After**: Easy dependency injection and mocking

### 5. Consistency
**Before**: Different patterns from other agents
**After**: Follows established BaseAgent pattern

### 6. Maintainability
**Before**: 600+ lines across 3 files
**After**: Single agent class with clear separation of concerns

## Testing Strategy

### Unit Tests
```python
@pytest.mark.asyncio
async def test_process_with_mineru_tool():
    """Test MinerU tool with mocked service."""
    agent = ImageProcessingAgent()
    deps = ImageProcessingDependencies()

    # Mock MinerU service
    with patch("agents.image_processing_agent.get_mineru_service") as mock_service:
        mock_service.return_value.process_pdf.return_value = (True, {
            "markdown": "# Test",
            "charts": [],
            "metadata": {"formulas_count": 0}
        })

        # Test tool execution
        result = await agent.process_document(
            file_content=b"fake pdf",
            filename="test.pdf"
        )

        assert result.success
        assert result.filename == "test.pdf"
```

### Integration Tests
```python
@pytest.mark.integration
async def test_full_pdf_processing():
    """Test end-to-end PDF processing with real MinerU."""
    agent = get_image_processing_agent()

    # Load test PDF
    test_pdf = Path("tests/fixtures/sample.pdf").read_bytes()

    # Process with progress tracking
    progress_logs = []
    def track_progress(update):
        progress_logs.append(update["log"])

    result = await agent.process_document(
        file_content=test_pdf,
        filename="sample.pdf",
        progress_callback=track_progress
    )

    # Verify results
    assert result.success
    assert len(result.images) > 0
    assert len(progress_logs) > 0
    assert any("Processing PDF" in log for log in progress_logs)
```

## Performance Considerations

### Memory Usage
- **Before**: Temporary files on disk (cleanup may fail)
- **After**: In-memory processing with structured cleanup

### Concurrent Processing
- **Before**: No rate limiting (could overwhelm services)
- **After**: Built-in rate limiting prevents service overload

### Error Recovery
- **Before**: Single failure stops processing
- **After**: Automatic retries with exponential backoff

## Conclusion

This refactoring aligns the MinerU PDF processing service with established PydanticAI patterns already used throughout Archon. The benefits include better type safety, progress reporting, error handling, and maintainability while maintaining backward compatibility during migration.

The implementation follows the exact patterns from `DocumentAgent` and `RagAgent`, ensuring consistency across the codebase and making it easier for new developers to understand and maintain the system.
