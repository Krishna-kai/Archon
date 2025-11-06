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
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from PIL import Image

from mineru.backend.pipeline.pipeline_analyze import doc_analyze


# ==================== Configuration ====================

PORT = int(os.getenv("PORT", "9006"))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

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
        for idx, img_obj in enumerate(pdf_images):
            try:
                if isinstance(img_obj, Image.Image):
                    # Convert PIL Image to bytes
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
            except Exception as e:
                log_message("warning", f"Failed to encode embedded image {idx}: {e}")

        # 2. Extract image regions from layout detection
        if pdf_doc and pdf_results:
            log_message("info", f"Extracting {image_count} detected image regions...")
            region_idx = 0

            for page_idx, page_result in enumerate(pdf_results):
                layout_dets = page_result.get('layout_dets', [])

                for det in layout_dets:
                    category_id = det.get('category_id', -1)

                    # Extract images and figures (category 0 or 3)
                    if category_id in [0, 3]:
                        try:
                            # Get bounding box [x0, y0, x1, y1]
                            bbox = det.get('bbox', [])
                            if len(bbox) != 4:
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

                        except Exception as e:
                            log_message("warning", f"Failed to extract region on page {page_idx + 1}: {e}")

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

class ExtractResponse(BaseModel):
    """Response model for structured extraction"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    model: str
    error: Optional[str] = None
    processing_time: float

@app.post("/extract-structured", response_model=ExtractResponse)
async def extract_structured(request: ExtractRequest):
    """
    Extract structured variables from processed PDF text using local LLMs via Ollama.
    """
    start_time = time.time()

    try:
        log_message("info", f"Starting structured extraction with model: {request.model}")

        # Extraction prompt
        prompt = f"""You are a research paper analysis assistant. Extract information from this medical image segmentation research paper.

Extract these variables as valid JSON:
- dataset: Dataset names used
- tissue_type: Tissue types analyzed
- input_format: Input data format
- method: Primary method name
- family: Architecture family
- architecture: Specific architecture
- innovation: Key contribution
- type: Approach type
- metrics: Evaluation metrics
- metric_used: Primary metric
- performance: Key results
- limitations: Limitations mentioned
- future_work: Future directions
- notes: Additional notes

Paper excerpt:
---
{request.text[:10000]}
---

Respond with ONLY a JSON object. No explanations, no markdown."""

        # Call Ollama
        result = subprocess.run(
            ["ollama", "run", request.model, prompt],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Ollama failed: {result.stderr}")

        response_text = result.stdout.strip()

        # Clean JSON from response
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)

        start = response_text.find('{')
        end = response_text.rfind('}')

        if start != -1 and end != -1:
            response_text = response_text[start:end+1]

        # Parse JSON
        extracted_data = json.loads(response_text)

        processing_time = time.time() - start_time

        log_message("success", f"Structured extraction complete in {processing_time:.2f}s")

        return ExtractResponse(
            success=True,
            data=extracted_data,
            model=request.model,
            processing_time=round(processing_time, 2)
        )

    except json.JSONDecodeError as e:
        processing_time = time.time() - start_time
        log_message("error", f"JSON parse error: {e}")
        return ExtractResponse(
            success=False,
            model=request.model,
            error=f"Failed to parse LLM response: {str(e)}",
            processing_time=round(processing_time, 2)
        )

    except subprocess.TimeoutExpired:
        processing_time = time.time() - start_time
        log_message("error", "Ollama request timed out")
        return ExtractResponse(
            success=False,
            model=request.model,
            error="Request timed out after 120 seconds",
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        processing_time = time.time() - start_time
        log_message("error", f"Extraction failed: {e}")
        return ExtractResponse(
            success=False,
            model=request.model,
            error=str(e),
            processing_time=round(processing_time, 2)
        )

@app.get("/models")
async def list_models():
    """
    List available Ollama models for structured extraction.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
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
