"""
DeepSeek-OCR MLX Service for Archon
Native Mac M4 service with Apple Metal GPU acceleration
"""
import os
import io
import tempfile
from pathlib import Path
from typing import Optional, List
import time
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image

# MLX imports - will be loaded dynamically
mlx_vlm = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepSeek-OCR MLX Service",
    description="Vision-language OCR service powered by DeepSeek-OCR with Apple Metal GPU acceleration",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model configuration
MODEL_NAME = "mlx-community/DeepSeek-OCR-8bit"
model_loaded = False


class OCRResponse(BaseModel):
    """Response model for OCR operations"""
    success: bool
    result: Optional[str] = None
    markdown: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    model_loaded: bool
    model: str
    backend: str
    platform: str


# Prompt templates for different OCR modes
PROMPTS = {
    "markdown": "<image>\n<|grounding|>Convert the document to markdown.",
    "plain": "<image>\nFree OCR.",
    "figure": "<image>\nParse the figure.",
    "table": "<image>\nExtract the table structure.",
    "formula": "<image>\nExtract mathematical formulas.",
}


def load_mlx():
    """Load MLX-VLM library"""
    global mlx_vlm
    try:
        import mlx_vlm as _mlx_vlm
        mlx_vlm = _mlx_vlm
        return True
    except ImportError as e:
        logger.error(f"Failed to import mlx_vlm: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    global model_loaded

    logger.info("🚀 Initializing DeepSeek-OCR MLX model...")
    start_time = time.time()

    try:
        # Load MLX-VLM
        if not load_mlx():
            raise RuntimeError("Failed to load MLX-VLM library. Please install: pip install mlx-vlm")

        logger.info(f"📦 Model: {MODEL_NAME}")
        logger.info("✅ MLX framework ready (models load on first use)")
        model_loaded = True

        load_time = time.time() - start_time
        logger.info(f"✅ DeepSeek-OCR MLX initialized in {load_time:.2f} seconds")
    except Exception as e:
        logger.error(f"❌ Failed to initialize: {str(e)}")
        model_loaded = False


@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "service": "DeepSeek-OCR MLX",
        "version": "1.0.0",
        "status": "running",
        "model": MODEL_NAME,
        "endpoints": {
            "health": "/health",
            "ocr": "/ocr/",
            "batch_ocr": "/batch-ocr/"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="deepseek-ocr-mlx",
        model_loaded=model_loaded,
        model=MODEL_NAME,
        backend="MLX (Apple Metal)",
        platform="Mac M4 native"
    )


@app.post("/ocr/", response_model=OCRResponse)
async def process_ocr(
    file: UploadFile = File(...),
    mode: str = Form("markdown"),
    custom_prompt: str = Form(None),
    max_tokens: int = Form(2000),
    temperature: float = Form(0.0)
):
    """
    Process image or document with OCR

    Args:
        file: Image file (JPG, PNG, BMP, TIFF)
        mode: OCR mode (markdown, plain, figure, table, formula, custom)
        custom_prompt: Custom prompt (used when mode=custom)
        max_tokens: Maximum output tokens
        temperature: Generation temperature (0.0 = deterministic)

    Returns:
        OCRResponse with extracted text
    """
    if not model_loaded:
        raise HTTPException(status_code=503, detail="Model not initialized")

    if mlx_vlm is None:
        raise HTTPException(status_code=503, detail="MLX-VLM library not loaded")

    start_time = time.time()
    temp_path = None

    try:
        # Read and save image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # Save to temp file (MLX-VLM needs file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", mode='wb') as tmp:
            image.save(tmp, "PNG")
            temp_path = tmp.name

        # Select prompt
        if mode == "custom" and custom_prompt:
            prompt = f"<image>\n{custom_prompt}"
        else:
            prompt = PROMPTS.get(mode, PROMPTS["markdown"])

        # Run OCR with MLX
        logger.info(f"🔍 Processing: {file.filename} (mode: {mode})")
        result = mlx_vlm.generate(
            model=MODEL_NAME,
            prompt=prompt,
            image=temp_path,
            max_tokens=max_tokens,
            temperature=temperature
        )

        processing_time = time.time() - start_time

        # Clean up
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

        logger.info(f"✅ OCR completed in {processing_time:.2f}s: {file.filename}")

        return OCRResponse(
            success=True,
            result=result,
            markdown=result if mode == "markdown" else None,
            text=result if mode == "plain" else None,
            metadata={
                "filename": file.filename,
                "mode": mode,
                "model": MODEL_NAME,
                "processing_time": round(processing_time, 2),
                "max_tokens": max_tokens,
                "temperature": temperature,
                "result_length": len(result) if result else 0
            }
        )

    except Exception as e:
        # Clean up on error
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

        logger.error(f"❌ OCR failed for {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.post("/batch-ocr/")
async def batch_process_ocr(
    files: List[UploadFile] = File(...),
    mode: str = Form("markdown"),
    max_tokens: int = Form(2000),
    temperature: float = Form(0.0)
):
    """
    Process multiple images in batch

    Args:
        files: List of image files
        mode: OCR mode
        max_tokens: Maximum output tokens per image
        temperature: Generation temperature

    Returns:
        List of OCR results
    """
    logger.info(f"📦 Batch processing {len(files)} files...")
    results = []
    start_time = time.time()

    for idx, file in enumerate(files, 1):
        try:
            logger.info(f"Processing {idx}/{len(files)}: {file.filename}")

            # Process each file
            response = await process_ocr(
                file=file,
                mode=mode,
                max_tokens=max_tokens,
                temperature=temperature
            )

            results.append({
                "filename": file.filename,
                "success": True,
                "result": response.result,
                "metadata": response.metadata
            })
        except Exception as e:
            logger.error(f"Failed to process {file.filename}: {str(e)}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    total_time = time.time() - start_time
    successful = sum(1 for r in results if r["success"])

    logger.info(f"✅ Batch processing complete: {successful}/{len(files)} successful in {total_time:.2f}s")

    return {
        "batch_results": results,
        "summary": {
            "total": len(files),
            "successful": successful,
            "failed": len(files) - successful,
            "total_time": round(total_time, 2),
            "avg_time_per_file": round(total_time / len(files), 2) if files else 0
        }
    }


@app.get("/models")
async def list_models():
    """List available models"""
    return {
        "models": [
            {
                "id": MODEL_NAME,
                "name": "DeepSeek-OCR-8bit",
                "description": "8-bit quantized DeepSeek-OCR model optimized for Apple Silicon",
                "capabilities": ["ocr", "markdown", "table", "formula", "figure"],
                "loaded": model_loaded
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 9005))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🚀 Starting DeepSeek-OCR MLX Service on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
