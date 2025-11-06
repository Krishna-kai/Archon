"""
ImageProcessingAgent - PDF Extraction and Image Analysis with PydanticAI

This agent handles PDF processing with MinerU and image analysis with Ollama,
following established PydanticAI patterns in the Archon codebase.
"""

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .base_agent import ArchonDependencies, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ImageProcessingDependencies(ArchonDependencies):
    """Dependencies for image processing operations."""

    mineru_service_url: str | None = None  # HTTP service URL if available (from MINERU_SERVICE_URL env)
    ollama_base_url: str = None  # Ollama API URL (from OLLAMA_BASE_URL env, default: http://localhost:11434)
    ollama_model: str = None  # Ollama model (from OLLAMA_MODEL env, default: llama3.2-vision)
    extract_charts: bool = False
    chart_provider: str = "auto"
    device: str = None  # Processing device (from MINERU_DEVICE env, default: mps)
    lang: str = None  # Language (from MINERU_LANG env, default: en)
    progress_callback: Any | None = None

    def __post_init__(self):
        """Apply environment variable defaults."""
        if self.ollama_base_url is None:
            self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        if self.ollama_model is None:
            self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2-vision")
        if self.device is None:
            self.device = os.getenv("MINERU_DEVICE", "mps")
        if self.lang is None:
            self.lang = os.getenv("MINERU_LANG", "en")
        if self.mineru_service_url is None:
            self.mineru_service_url = os.getenv("MINERU_SERVICE_URL")


class ExtractedImage(BaseModel):
    """Structured image data extracted from PDF."""

    name: str = Field(description="Image filename")
    base64_data: str = Field(description="Base64-encoded image data")
    page_number: int | None = Field(description="PDF page number (1-indexed)", default=None)
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
                from ..server.services.mineru_service import get_mineru_service
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
                    return json.dumps({
                        "success": False,
                        "error": error_msg
                    })

                # Extract statistics
                metadata = result.get("metadata", {})
                formula_count = metadata.get("formulas_count", 0)
                table_count = metadata.get("tables_count", 0)
                images = result.get("charts", [])
                image_count = len(images)

                if ctx.deps.progress_callback:
                    await ctx.deps.progress_callback({
                        "step": "pdf_extraction",
                        "log": f"✅ Extracted: {formula_count} formulas, {table_count} tables, {image_count} images"
                    })

                # Return JSON result for agent to parse
                return json.dumps({
                    "success": True,
                    "markdown": result.get("markdown", ""),
                    "images": images,
                    "metadata": metadata,
                })

            except Exception as e:
                logger.error(f"MinerU processing failed: {e}", exc_info=True)
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })

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
                        error_msg = f"Ollama error: HTTP {response.status_code}"
                        if ctx.deps.progress_callback:
                            await ctx.deps.progress_callback({
                                "step": "image_analysis",
                                "log": f"⚠️ {error_msg} for {image_name}"
                            })
                        return json.dumps({
                            "success": False,
                            "error": error_msg
                        })

                    result = response.json()
                    analysis_text = result.get("response", "{}")

                    if ctx.deps.progress_callback:
                        await ctx.deps.progress_callback({
                            "step": "image_analysis",
                            "log": f"✅ Analyzed {image_name}"
                        })

                    # Try to parse as JSON, fallback to text
                    try:
                        analysis_json = json.loads(analysis_text)
                        return json.dumps({
                            "success": True,
                            **analysis_json
                        })
                    except json.JSONDecodeError:
                        # Return as-is if not valid JSON
                        return json.dumps({
                            "success": True,
                            "analysis_text": analysis_text
                        })

            except Exception as e:
                logger.error(f"Ollama analysis failed for {image_name}: {e}")
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })

        return agent

    def get_system_prompt(self) -> str:
        """Get the base system prompt for this agent."""
        return "Image Processing Agent for PDF extraction and analysis."

    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        mineru_service_url: str | None = None,  # Defaults to MINERU_SERVICE_URL env var
        ollama_base_url: str | None = None,  # Defaults to OLLAMA_BASE_URL env var or http://localhost:11434
        ollama_model: str | None = None,  # Defaults to OLLAMA_MODEL env var or llama3.2-vision
        extract_charts: bool = False,
        chart_provider: str = "auto",
        device: str | None = None,  # Defaults to MINERU_DEVICE env var or "mps"
        lang: str | None = None,  # Defaults to MINERU_LANG env var or "en"
        progress_callback: Any = None,
        analyze_images: bool = False,
    ) -> ProcessingResult:
        """
        Process a PDF document and return structured results.

        Args:
            file_content: Raw PDF bytes
            filename: Original filename
            mineru_service_url: Optional HTTP service URL (defaults to MINERU_SERVICE_URL env)
            ollama_base_url: Ollama API base URL (defaults to OLLAMA_BASE_URL env or http://localhost:11434)
            ollama_model: Ollama model to use for analysis (defaults to OLLAMA_MODEL env or llama3.2-vision)
            extract_charts: Whether to extract charts from PDF
            chart_provider: Chart extraction provider
            device: Processing device (defaults to MINERU_DEVICE env or "mps" for Apple Silicon)
            lang: Document language (defaults to MINERU_LANG env or "en")
            progress_callback: Optional callback for progress updates
            analyze_images: Whether to analyze images with Ollama

        Returns:
            Structured ProcessingResult with all extracted content

        Environment Variables:
            - MINERU_SERVICE_URL: URL of native MinerU HTTP service
            - OLLAMA_BASE_URL: Base URL for Ollama API (default: http://localhost:11434)
            - OLLAMA_MODEL: Ollama model name (default: llama3.2-vision)
            - MINERU_DEVICE: Processing device (default: mps)
            - MINERU_LANG: Document language (default: en)
        """
        start_time = time.time()

        # Create dependencies (will apply env var defaults via __post_init__)
        deps = ImageProcessingDependencies(
            mineru_service_url=mineru_service_url,  # Will use env var if None
            ollama_base_url=ollama_base_url,  # Will use env var if None
            ollama_model=ollama_model,  # Will use env var if None
            extract_charts=extract_charts,
            chart_provider=chart_provider,
            device=device,  # Will use env var if None
            lang=lang,  # Will use env var if None
            progress_callback=progress_callback,
        )

        try:
            # Step 1: Process PDF with MinerU (without using agent)
            if progress_callback:
                await progress_callback({
                    "step": "pdf_extraction",
                    "log": f"🔄 Processing PDF with MinerU: {filename}"
                })

            from ..server.services.mineru_service import get_mineru_service
            mineru_service = get_mineru_service()

            success, mineru_result = await mineru_service.process_pdf(
                file_content=file_content,
                filename=filename,
                device=device,
                lang=lang,
                extract_charts=extract_charts,
                chart_provider=chart_provider,
            )

            if not success:
                error_msg = mineru_result.get("error", "Unknown error")
                if progress_callback:
                    await progress_callback({
                        "step": "pdf_extraction",
                        "log": f"❌ MinerU failed: {error_msg}"
                    })

                return ProcessingResult(
                    success=False,
                    filename=filename,
                    markdown_text="",
                    images=[],
                    metadata={},
                    message=f"MinerU processing failed: {error_msg}",
                    error=error_msg,
                )

            # Extract results
            markdown_text = mineru_result.get("markdown", "")
            raw_images = mineru_result.get("charts", [])
            metadata = mineru_result.get("metadata", {})

            formula_count = metadata.get("formulas_count", 0)
            table_count = metadata.get("tables_count", 0)
            page_count = metadata.get("pages", 0)
            image_count = len(raw_images)

            if progress_callback:
                await progress_callback({
                    "step": "pdf_extraction",
                    "log": f"✅ Extracted: {formula_count} formulas, {table_count} tables, {image_count} images"
                })

            # Step 2: Convert images to structured format
            extracted_images = []
            for img_data in raw_images:
                extracted_images.append(ExtractedImage(
                    name=img_data.get("name", f"image_{img_data.get('image_index', 0)}.png"),
                    base64_data=img_data.get("base64", ""),
                    page_number=img_data.get("page_number"),
                    image_index=img_data.get("image_index", 0),
                    mime_type=img_data.get("mime_type", "image/png"),
                ))

            # Step 3: Optionally analyze images with Ollama
            if analyze_images and image_count > 0:
                if progress_callback:
                    await progress_callback({
                        "step": "image_analysis",
                        "log": f"🖼️ Analyzing {image_count} images with Ollama..."
                    })

                import httpx

                for i, img in enumerate(extracted_images, 1):
                    try:
                        if progress_callback:
                            await progress_callback({
                                "step": "image_analysis",
                                "log": f"🤖 Analyzing image {i}/{image_count}: {img.name}"
                            })

                        async with httpx.AsyncClient(timeout=60.0) as client:
                            response = await client.post(
                                f"{ollama_base_url}/api/generate",
                                json={
                                    "model": ollama_model,
                                    "prompt": """Analyze this image and provide:
1. OCR: Extract any visible text
2. Description: Describe what you see in 1-2 sentences
3. Classification: Classify the image type (diagram, chart, photo, equation, table, graph, etc.)

Format your response as JSON:
{
  "ocr_text": "extracted text here or empty string if no text",
  "description": "brief image description",
  "classification": "image type",
  "confidence": 0.95
}""",
                                    "images": [img.base64_data],
                                    "stream": False,
                                }
                            )

                            if response.status_code == 200:
                                result = response.json()
                                analysis_text = result.get("response", "{}")

                                # Try to parse as JSON
                                try:
                                    analysis = json.loads(analysis_text)
                                    img.ocr_text = analysis.get("ocr_text", "")
                                    img.description = analysis.get("description", "")
                                    img.classification = analysis.get("classification", "")
                                    img.confidence = analysis.get("confidence")

                                    if progress_callback:
                                        await progress_callback({
                                            "step": "image_analysis",
                                            "log": f"✅ Analyzed {img.name}: {img.classification}"
                                        })

                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse Ollama response as JSON: {analysis_text[:100]}")
                                    img.description = analysis_text[:200]  # Use first 200 chars

                            else:
                                logger.warning(f"Ollama returned HTTP {response.status_code} for {img.name}")

                    except Exception as e:
                        logger.error(f"Failed to analyze image {img.name}: {e}")
                        if progress_callback:
                            await progress_callback({
                                "step": "image_analysis",
                                "log": f"⚠️ Skipped {img.name}: {str(e)[:50]}"
                            })
                        # Continue processing other images

            # Calculate processing time
            processing_time = time.time() - start_time

            # Build final result
            result = ProcessingResult(
                success=True,
                filename=filename,
                markdown_text=markdown_text,
                images=extracted_images,
                metadata=metadata,
                message=f"Successfully processed {filename}: {page_count} pages, {formula_count} formulas, {table_count} tables, {image_count} images",
                page_count=page_count,
                formula_count=formula_count,
                table_count=table_count,
                image_count=image_count,
                processing_time_seconds=processing_time,
            )

            if progress_callback:
                await progress_callback({
                    "step": "complete",
                    "log": f"✅ Processing complete in {processing_time:.1f}s!"
                })

            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            processing_time = time.time() - start_time

            if progress_callback:
                await progress_callback({
                    "step": "error",
                    "log": f"❌ Processing failed: {str(e)}"
                })

            return ProcessingResult(
                success=False,
                filename=filename,
                markdown_text="",
                images=[],
                metadata={},
                message=f"Processing failed: {str(e)}",
                error=str(e),
                processing_time_seconds=processing_time,
            )


# Singleton instance
_agent_instance: ImageProcessingAgent | None = None


def get_image_processing_agent() -> ImageProcessingAgent:
    """Get or create ImageProcessingAgent singleton instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ImageProcessingAgent()
    return _agent_instance
