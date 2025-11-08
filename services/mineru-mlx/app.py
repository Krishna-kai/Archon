"""
MinerU MLX Service

FastAPI service that runs MinerU natively on macOS with Apple Silicon GPU acceleration.
Optimized for Apple Metal (MLX) with comprehensive error handling and monitoring.

Port: 9006
Version: 2.0.0
"""

import asyncio
import base64
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from PIL import Image
from openai import OpenAI
import httpx
from anthropic import Anthropic
import fitz  # PyMuPDF

from mineru.backend.pipeline.pipeline_analyze import doc_analyze
from template_loader import template_loader, ExtractionTemplate


# ==================== Configuration ====================

PORT = int(os.getenv("PORT", "9006"))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

# LLM Provider Configuration (ENV-based)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Determine available providers based on ENV
AVAILABLE_PROVIDERS = ["ollama"]  # Always available (local)
if OPENAI_API_KEY:
    AVAILABLE_PROVIDERS.append("openai")
if ANTHROPIC_API_KEY:
    AVAILABLE_PROVIDERS.append("claude")

# Service metadata
SERVICE_VERSION = "2.0.0"
SERVICE_NAME = "mineru-mlx"


# ==================== FastAPI Application ====================

app = FastAPI(
    title="MinerU MLX Service",
    description="Native MinerU PDF processing service for Apple Silicon with Metal GPU acceleration",
    version=SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Data Models ====================

class ImageData(BaseModel):
    """Image extracted from PDF with metadata"""
    name: str
    base64: str
    page_number: Optional[int] = None
    image_index: int
    mime_type: str = "image/png"


class ProcessResponse(BaseModel):
    """Response model for PDF processing"""
    success: bool
    text: str
    images: list[ImageData]
    metadata: dict
    message: Optional[str] = None
    processing_time: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str
    port: int
    backend: str
    platform: str
    timestamp: str


class ServiceInfo(BaseModel):
    """Service information model"""
    service: str
    version: str
    status: str
    port: int
    backend: str
    platform: str
    endpoints: dict


# ==================== Helper Functions ====================

def log_message(level: str, message: str):
    """Enhanced logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level_emoji = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "debug": "🔍"
    }
    emoji = level_emoji.get(level.lower(), "📝")
    print(f"[{timestamp}] {emoji} [{level.upper()}] {message}", flush=True)


def get_platform_info() -> str:
    """Get platform information"""
    import platform
    return f"macOS {platform.mac_ver()[0]} on {platform.machine()}"


# ==================== API Endpoints ====================

@app.get("/", response_model=ServiceInfo)
async def root():
    """Root endpoint with comprehensive service information"""
    return ServiceInfo(
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        status="running",
        port=PORT,
        backend="MinerU with Apple Metal GPU",
        platform=get_platform_info(),
        endpoints={
            "health": "/health",
            "process": "/process (POST)",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check endpoint"""
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        port=PORT,
        backend="MinerU with Apple Metal GPU",
        platform=get_platform_info(),
        timestamp=datetime.now().isoformat()
    )


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon to prevent 404 errors"""
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/ui")
async def serve_ui():
    """Serve the MinerU processing UI"""
    from fastapi.responses import FileResponse
    ui_path = Path(__file__).parent / "mineru_ui.html"
    if ui_path.exists():
        return FileResponse(ui_path, media_type="text/html")
    else:
        raise HTTPException(status_code=404, detail="UI file not found")


@app.post("/process", response_model=ProcessResponse)
async def process_pdf(
    file: UploadFile = File(...),
    extract_charts: bool = Form(False),
    chart_provider: str = Form("auto"),
    device: str = Form("mps"),
    lang: str = Form("en")
):
    """
    Process a PDF file with MinerU using Apple Metal GPU acceleration

    Args:
        file: PDF file to process
        extract_charts: Whether to extract chart data from images
        chart_provider: Chart extraction provider ("auto", "local", "claude")
        device: Device to use ("mps" for Apple GPU, "cpu" for CPU)
        lang: Language code (default: "en")

    Returns:
        Extracted text, images, and metadata with processing statistics
    """
    start_time = time.time()

    try:
        log_message("info", f"Processing PDF: {file.filename} (device: {device}, lang: {lang})")

        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only PDF files are supported."
            )

        # Read PDF content
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        log_message("info", f"PDF size: {file_size_mb:.2f} MB")

        # Process PDF with MinerU
        log_message("info", "Starting MinerU processing...")
        result_tuple = await asyncio.to_thread(
            doc_analyze,
            [content],  # pdf_bytes_list - list of PDF bytes
            [lang],  # lang_list - list of language codes
            parse_method="auto",  # parsing method
            formula_enable=True,  # enable formula extraction
            table_enable=True  # enable table extraction
        )

        # Unpack the results
        infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = result_tuple

        # Extract results for the first (and only) PDF
        pdf_results = infer_results[0] if infer_results else []
        pdf_images = all_image_lists[0] if all_image_lists else []
        pdf_doc = all_pdf_docs[0] if all_pdf_docs else None

        # Count and identify different element types from layout detections
        # MinerU category IDs: 0=image, 3=figure, 5=table, 7=title, 13=formula, 14=text
        formula_count = 0
        table_count = 0
        image_count = 0

        for page_result in pdf_results:
            layout_dets = page_result.get('layout_dets', [])
            for det in layout_dets:
                category_id = det.get('category_id', -1)
                if category_id == 13:  # Formula
                    formula_count += 1
                elif category_id == 5:  # Table
                    table_count += 1
                elif category_id in [0, 3]:  # Image or Figure
                    image_count += 1

        # Extract text using PdfDocument object (pypdfium2)
        text_parts = []
        total_chars_extracted = 0

        if pdf_doc:
            page_count = len(pdf_doc)
            log_message("info", f"Extracting text from {page_count} pages...")

            for page_idx in range(page_count):
                text_parts.append(f"## Page {page_idx + 1}\n")

                try:
                    # Get page and extract text using pypdfium2
                    page = pdf_doc[page_idx]
                    textpage = page.get_textpage()
                    page_text = textpage.get_text_bounded()

                    if page_text:
                        text_parts.append(page_text)
                        text_parts.append("\n")
                        total_chars_extracted += len(page_text)

                except Exception as e:
                    log_message("warning", f"Page {page_idx + 1} text extraction error: {str(e)}")
                    text_parts.append("[Text extraction failed for this page]\n\n")

        text = "\n".join(text_parts)

        # Process all images (embedded + detected regions)
        image_data_list = []

        # 1. Process embedded images from all_image_lists
        log_message("info", f"Processing {len(pdf_images)} embedded images...")

        # DEBUG: Check what we actually got
        if pdf_images:
            log_message("info", f"DEBUG: pdf_images type: {type(pdf_images)}, first item type: {type(pdf_images[0]).__module__}.{type(pdf_images[0]).__name__}")
            if isinstance(pdf_images[0], dict):
                log_message("info", f"DEBUG: Dictionary keys: {list(pdf_images[0].keys())}")

        for idx, img_obj in enumerate(pdf_images):
            try:
                # Handle dict format from MinerU
                if isinstance(img_obj, dict):
                    # MinerU returns dicts with image data - check for common keys
                    pil_img = None

                    # Try common key names
                    for key in ['img_pil', 'image', 'img']:
                        if key in img_obj:
                            if isinstance(img_obj[key], Image.Image):
                                pil_img = img_obj[key]
                                break
                            else:
                                log_message("warning", f"Embedded image {idx} dict['{key}'] is not PIL Image (type: {type(img_obj[key])})")

                    if pil_img is None:
                        log_message("warning", f"Embedded image {idx} is dict but has no PIL Image in keys: {list(img_obj.keys())}")
                        continue

                    # Convert PIL Image to bytes
                    img_buffer = io.BytesIO()
                    pil_img.save(img_buffer, format='PNG')
                    img_bytes = img_buffer.getvalue()

                    # Encode to base64
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                    # Add to list
                    image_data_list.append(ImageData(
                        name=f"embedded_{idx}.png",
                        base64=img_base64,
                        page_number=img_obj.get('page_number', None),
                        image_index=idx,
                        mime_type="image/png"
                    ))

                elif isinstance(img_obj, Image.Image):
                    # Direct PIL Image (legacy format)
                    img_buffer = io.BytesIO()
                    img_obj.save(img_buffer, format='PNG')
                    img_bytes = img_buffer.getvalue()

                    # Encode to base64
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                    # Add to list
                    image_data_list.append(ImageData(
                        name=f"embedded_{idx}.png",
                        base64=img_base64,
                        page_number=None,
                        image_index=idx,
                        mime_type="image/png"
                    ))
                else:
                    log_message("warning", f"Embedded image {idx} is neither dict nor PIL Image (type: {type(img_obj).__module__}.{type(img_obj).__name__}), skipping")
            except Exception as e:
                log_message("warning", f"Failed to encode embedded image {idx}: {e}")

        # 2. Extract image regions from layout detection
        # DEBUG: Check if pdf_doc and pdf_results are available
        log_message("info", f"DEBUG: pdf_doc={pdf_doc is not None}, pdf_results={len(pdf_results) if pdf_results else 0} pages")
        if pdf_doc and pdf_results:
            log_message("info", f"Extracting {image_count} detected image regions...")
            region_idx = 0
            regions_found = 0
            regions_extracted = 0

            for page_idx, page_result in enumerate(pdf_results):
                layout_dets = page_result.get('layout_dets', [])

                for det in layout_dets:
                    category_id = det.get('category_id', -1)

                    # Extract images and figures (category 0 or 3)
                    if category_id in [0, 3]:
                        regions_found += 1
                        try:
                            # Get bounding box [x0, y0, x1, y1]
                            bbox = det.get('bbox', [])
                            if len(bbox) != 4:
                                log_message("warning", f"Skipping region on page {page_idx + 1}: invalid bbox length {len(bbox)}, bbox={bbox}")
                                continue

                            x0, y0, x1, y1 = bbox

                            # Render page to image
                            page = pdf_doc[page_idx]
                            # Scale factor for higher resolution
                            scale = 2.0
                            bitmap = page.render(scale=scale)
                            pil_image = bitmap.to_pil()

                            # Crop to bounding box (scale coordinates)
                            crop_box = (
                                int(x0 * scale),
                                int(y0 * scale),
                                int(x1 * scale),
                                int(y1 * scale)
                            )
                            cropped_img = pil_image.crop(crop_box)

                            # Convert to base64
                            img_buffer = io.BytesIO()
                            cropped_img.save(img_buffer, format='PNG')
                            img_bytes = img_buffer.getvalue()
                            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                            # Add to list
                            image_data_list.append(ImageData(
                                name=f"page_{page_idx + 1}_region_{region_idx}.png",
                                base64=img_base64,
                                page_number=page_idx + 1,
                                image_index=region_idx,
                                mime_type="image/png"
                            ))
                            region_idx += 1
                            regions_extracted += 1

                        except Exception as e:
                            log_message("warning", f"Failed to extract region on page {page_idx + 1}, bbox {bbox}: {e}")

            log_message("info", f"DEBUG: Regions found={regions_found}, extracted={regions_extracted}, total_images_in_list={len(image_data_list)}")

        processing_time = time.time() - start_time

        # Log processing summary
        log_message("success",
            f"Processed {file.filename}: {len(pdf_results)} pages, "
            f"{total_chars_extracted} chars, {formula_count} formulas, "
            f"{table_count} tables, {len(image_data_list)} images "
            f"({image_count} detected + {len(pdf_images)} embedded) "
            f"in {processing_time:.2f}s"
        )

        # Build response
        return ProcessResponse(
            success=True,
            text=text,
            images=image_data_list,
            metadata={
                "filename": file.filename,
                "file_size_mb": round(file_size_mb, 2),
                "pages": len(pdf_results),
                "page_count": len(pdf_results),
                "chars_extracted": total_chars_extracted,
                "formulas_count": formula_count,
                "formulas_detected": formula_count,
                "tables_count": table_count,
                "tables_detected": table_count,
                "images_extracted": len(image_data_list),
                "images_detected": image_count,
                "images_embedded": len(pdf_images),
                "extract_charts": extract_charts,
                "chart_provider": chart_provider,
                "device": device,
                "lang": lang,
                "backend": "MinerU with Apple Metal GPU",
                "service_version": SERVICE_VERSION,
                "ocr_enabled": ocr_enabled_list[0] if ocr_enabled_list else False
            },
            message="PDF processed successfully",
            processing_time=round(processing_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        processing_time = time.time() - start_time
        error_detail = f"MinerU processing failed after {processing_time:.2f}s: {str(e)}"
        full_traceback = traceback.format_exc()

        log_message("error", error_detail)
        log_message("debug", full_traceback)

        raise HTTPException(
            status_code=500,
            detail={
                "error": error_detail,
                "traceback": full_traceback if LOG_LEVEL == "debug" else None,
                "processing_time": round(processing_time, 2)
            }
        )


# ==================== Structured Extraction ====================

class ExtractRequest(BaseModel):
    """Request model for structured extraction"""
    text: str
    model: str = "qwen2.5-coder:7b"
    provider: str = "ollama"  # ollama, openai, claude
    template_id: Optional[str] = None  # Template ID (medical_research, legal_document, technical_document, general_document)
    variables_template: Optional[List[Dict[str, Any]]] = None  # CSV template data (DEPRECATED - use template_id instead)
    temperature: Optional[float] = None  # Override template temperature
    max_tokens: Optional[int] = None  # Override template max_tokens
    max_text_length: Optional[int] = None  # Override template max_text_length
    timeout: Optional[int] = None  # Override template timeout

class ExtractResponse(BaseModel):
    """Response model for structured extraction"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    model: str
    provider: str
    error: Optional[str] = None
    processing_time: float


@app.get("/providers")
async def list_providers():
    """
    List available LLM providers based on ENV configuration.
    Local Ollama is always available. Cloud providers require API keys in ENV.
    """
    return {
        "providers": AVAILABLE_PROVIDERS,
        "default": "ollama",
        "details": {
            "ollama": {"available": True, "description": "Local LLM via Ollama"},
            "openai": {"available": "openai" in AVAILABLE_PROVIDERS, "description": "OpenAI GPT models"},
            "claude": {"available": "claude" in AVAILABLE_PROVIDERS, "description": "Anthropic Claude models"}
        }
    }


@app.get("/templates")
async def list_templates():
    """List available extraction templates"""
    templates = template_loader.list_templates()
    return {
        "templates": templates,
        "count": len(templates),
        "message": "Use template_id in extraction requests to select a template"
    }


@app.get("/templates/{template_id}")
async def get_template_detail(template_id: str):
    """Get detailed information about a specific template"""
    template = template_loader.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "variables": [
            {
                "name": var.name,
                "description": var.description,
                "type": var.type,
                "required": var.required
            }
            for var in template.variables
        ],
        "parameters": {
            "max_text_length": template.parameters.max_text_length,
            "temperature": template.parameters.temperature,
            "max_tokens": template.parameters.max_tokens,
            "timeout": template.parameters.timeout
        },
        "output_format": {
            "null_handling": template.output_format.null_handling,
            "strict_schema": template.output_format.strict_schema
        }
    }


def get_template_and_params(
    template_id: Optional[str],
    variables_template: Optional[List[Dict]],
    temperature_override: Optional[float],
    max_tokens_override: Optional[int],
    max_text_length_override: Optional[int],
    timeout_override: Optional[int]
) -> tuple[ExtractionTemplate, Dict[str, Any]]:
    """
    Get extraction template and parameters with overrides.

    Returns:
        tuple: (template, params_dict)
    """
    if variables_template:
        log_message("warning", "variables_template is DEPRECATED - please use template_id instead")
        template = template_loader.get_default_template()
    elif template_id:
        template = template_loader.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
    else:
        template = template_loader.get_default_template()

    params = {
        "temperature": temperature_override or template.parameters.temperature,
        "max_tokens": max_tokens_override or template.parameters.max_tokens,
        "max_text_length": max_text_length_override or template.parameters.max_text_length,
        "timeout": timeout_override or template.parameters.timeout
    }

    return template, params


async def extract_with_openai(
    text: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int
) -> Dict:
    """Extract using OpenAI API with template parameters"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured. Set OPENAI_API_KEY environment variable to enable OpenAI provider.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )

    response_text = response.choices[0].message.content

    # Clean and parse JSON
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*', '', response_text)
    start = response_text.find('{')
    end = response_text.rfind('}')
    if start != -1 and end != -1:
        response_text = response_text[start:end+1]

    return json.loads(response_text)


async def extract_with_claude(
    text: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int
) -> Dict:
    """Extract using Anthropic Claude API with template parameters"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured. Set ANTHROPIC_API_KEY environment variable to enable Claude provider.")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    response_text = message.content[0].text

    # Clean and parse JSON
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*', '', response_text)
    start = response_text.find('{')
    end = response_text.rfind('}')
    if start != -1 and end != -1:
        response_text = response_text[start:end+1]

    return json.loads(response_text)


async def extract_with_ollama(
    text: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: int
) -> Dict:
    """Extract using local Ollama HTTP API with JSON mode for structured output"""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # Combine system and user prompts
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    # Add instruction to output JSON only (helps with non-JSON-mode models)
    full_prompt += "\n\nIMPORTANT: Respond with ONLY valid JSON. No explanations, no thinking, no markdown formatting."

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "format": "json",  # Force JSON output
                    "stream": False,   # Get complete response at once
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            response_text = result.get("response", "")

            if not response_text:
                raise HTTPException(status_code=500, detail="Ollama returned empty response")

            # Parse JSON response
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                log_message("error", f"Failed to parse Ollama JSON response: {e}")
                log_message("error", f"Response text: {response_text[:500]}...")
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama returned invalid JSON: {str(e)}"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama request timed out after {timeout} seconds"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama connection error: {str(e)}. Is Ollama running?"
        )


@app.post("/extract-structured", response_model=ExtractResponse)
async def extract_structured(request: ExtractRequest):
    """
    Extract structured variables from processed PDF text using selected LLM provider.
    Supports Ollama (local), OpenAI, and Claude APIs with optional CSV templates.
    """
    start_time = time.time()

    try:
        log_message("info", f"Starting extraction with {request.provider}/{request.model}")

        # Validate provider is available
        if request.provider not in AVAILABLE_PROVIDERS:
            return ExtractResponse(
                success=False,
                model=request.model,
                provider=request.provider,
                error=f"Provider '{request.provider}' not available. Check ENV configuration.",
                processing_time=0
            )

        # Get template and parameters with overrides
        template, params = get_template_and_params(
            request.template_id,
            request.variables_template,
            request.temperature,
            request.max_tokens,
            request.max_text_length,
            request.timeout
        )

        # Build prompts from template
        system_prompt, user_prompt = template_loader.build_prompt(
            template,
            request.text,
            params["max_text_length"]
        )

        log_message("info", f"Using template: {template.id} ({template.name})")

        # Route to appropriate provider with template parameters
        if request.provider == "openai":
            extracted_data = await extract_with_openai(
                request.text,
                request.model,
                system_prompt,
                user_prompt,
                params["temperature"],
                params["max_tokens"]
            )
        elif request.provider == "claude":
            extracted_data = await extract_with_claude(
                request.text,
                request.model,
                system_prompt,
                user_prompt,
                params["temperature"],
                params["max_tokens"]
            )
        else:  # ollama (default)
            extracted_data = await extract_with_ollama(
                request.text,
                request.model,
                system_prompt,
                user_prompt,
                params["temperature"],
                params["max_tokens"],
                params["timeout"]
            )

        processing_time = time.time() - start_time
        log_message("success", f"Extraction complete in {processing_time:.2f}s")

        return ExtractResponse(
            success=True,
            data=extracted_data,
            model=request.model,
            provider=request.provider,
            processing_time=round(processing_time, 2)
        )

    except json.JSONDecodeError as e:
        processing_time = time.time() - start_time
        log_message("error", f"JSON parse error: {e}")
        return ExtractResponse(
            success=False,
            model=request.model,
            provider=request.provider,
            error=f"Failed to parse LLM response: {str(e)}",
            processing_time=round(processing_time, 2)
        )

    except subprocess.TimeoutExpired:
        processing_time = time.time() - start_time
        log_message("error", f"Request timed out after {params['timeout']} seconds")
        return ExtractResponse(
            success=False,
            model=request.model,
            provider=request.provider,
            error=f"Request timed out after {params['timeout']} seconds",
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        processing_time = time.time() - start_time
        log_message("error", f"Extraction failed: {e}")
        return ExtractResponse(
            success=False,
            model=request.model,
            provider=request.provider,
            error=str(e),
            processing_time=round(processing_time, 2)
        )

@app.post("/extract-images-only")
async def extract_images_only(file: UploadFile = File(...)):
    """
    Extract all images from PDF using PyMuPDF (bypasses MinerU layout detection).
    This is faster and more reliable for image-only extraction, ideal for zooming.

    Args:
        file: PDF file to process

    Returns:
        All embedded images from the PDF with base64 encoding
    """
    start_time = time.time()

    try:
        log_message("info", f"Extracting images from: {file.filename}")

        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only PDF files are supported."
            )

        # Read PDF content
        pdf_bytes = await file.read()
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        log_message("info", f"PDF size: {file_size_mb:.2f} MB")

        # Open PDF with PyMuPDF
        pdf_doc = fitz.open("pdf", pdf_bytes)
        page_count = len(pdf_doc)
        log_message("info", f"Processing {page_count} pages for images...")

        image_data_list = []
        total_images = 0

        # Extract images from each page
        for page_num in range(page_count):
            page = pdf_doc[page_num]
            image_list = page.get_images(full=True)

            log_message("info", f"Page {page_num + 1}: Found {len(image_list)} images")

            for img_index, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    base_image = pdf_doc.extract_image(xref)

                    # Get image bytes and convert to base64
                    image_bytes = base_image["image"]
                    img_base64 = base64.b64encode(image_bytes).decode('utf-8')

                    # Determine image format
                    img_ext = base_image.get("ext", "png")
                    mime_type = f"image/{img_ext}"

                    # Get image dimensions
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)

                    image_data_list.append(ImageData(
                        name=f"page_{page_num + 1}_img_{img_index + 1}.{img_ext}",
                        base64=img_base64,
                        page_number=page_num + 1,
                        image_index=img_index,
                        mime_type=mime_type
                    ))

                    total_images += 1
                    log_message("info",
                        f"  ✓ Extracted: page_{page_num + 1}_img_{img_index + 1}.{img_ext} "
                        f"({width}x{height})")

                except Exception as img_err:
                    log_message("warning",
                        f"Failed to extract image {img_index + 1} from page {page_num + 1}: {img_err}")

        pdf_doc.close()
        processing_time = time.time() - start_time

        log_message("success",
            f"Extracted {total_images} images in {processing_time:.2f}s")

        return ProcessResponse(
            success=True,
            text="",  # No text extraction in this endpoint
            images=image_data_list,
            metadata={
                "filename": file.filename,
                "file_size_mb": round(file_size_mb, 2),
                "pages": page_count,
                "images_extracted": total_images,
                "chars_extracted": 0,
                "formulas_detected": 0,
                "tables_detected": 0,
                "backend": "PyMuPDF (direct image extraction)",
                "processing_time": round(processing_time, 2)
            },
            message=f"Extracted {total_images} images from {page_count} pages",
            processing_time=round(processing_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        log_message("error", f"Image extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Image extraction failed: {str(e)}"
        )


@app.get("/models")
async def list_models():
    """
    List available Ollama models for structured extraction.
    """
    try:
        # Use full path to ollama binary
        ollama_path = os.getenv("OLLAMA_PATH", "/opt/homebrew/bin/ollama")
        result = subprocess.run(
            [ollama_path, "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Failed to list models")

        # Parse ollama list output
        lines = result.stdout.strip().split('\n')
        models = []

        for line in lines[1:]:  # Skip header
            parts = line.split()
            if parts:
                model_name = parts[0]
                # Filter out embedding models (nomic) - they don't support text generation
                if 'nomic' not in model_name.lower():
                    models.append(model_name)

        return {
            "success": True,
            "models": models
        }

    except Exception as e:
        log_message("error", f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Startup / Shutdown ====================

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    log_message("info", "=" * 60)
    log_message("info", f"🚀 Starting {SERVICE_NAME} v{SERVICE_VERSION}")
    log_message("info", f"📍 Port: {PORT}")
    log_message("info", f"🖥️  Platform: {get_platform_info()}")
    log_message("info", f"🔥 Backend: MinerU with Apple Metal GPU")
    log_message("info", f"📝 Log Level: {LOG_LEVEL.upper()}")
    log_message("info", "=" * 60)
    log_message("success", "Service ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information"""
    log_message("info", "Shutting down MinerU MLX service...")


# ==================== Main ====================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
        access_log=True
    )
