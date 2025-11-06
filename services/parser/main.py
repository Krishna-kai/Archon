"""
Parser Service - Production-Ready OCR Pipeline Orchestrator
Combines Docling OCR + LaTeX-OCR for complete document extraction
"""
import asyncio
import base64
import io
import re
import time
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import httpx
import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image


# Configuration
import os
DOCLING_URL = os.getenv("DOCLING_URL", "http://docling-ocr:9000")
LATEX_OCR_URL = os.getenv("LATEX_OCR_URL", "http://latex-ocr:9001")
MAX_CONCURRENT_FORMULAS = 3
FORMULA_TIMEOUT = 10
PDF_MAX_SIZE_MB = 100


# Global HTTP client
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
    print("🚀 Parser Service initialized")
    print(f"   Docling OCR: {DOCLING_URL}")
    print(f"   LaTeX-OCR: {LATEX_OCR_URL}")
    yield
    await http_client.aclose()
    print("🛑 Parser Service shutdown")


app = FastAPI(
    title="Parser Service",
    description="Orchestrates Docling + LaTeX-OCR for complete PDF extraction",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Models
# ============================================================================

class ParseOptions(BaseModel):
    """Options for parsing PDF"""
    extract_formulas: bool = Field(default=True, description="Extract LaTeX formulas")
    extract_images: bool = Field(default=True, description="Extract embedded images")
    extract_tables: bool = Field(default=True, description="Extract tables")
    timeout: int = Field(default=120, description="Total timeout in seconds")


class ParseMetadata(BaseModel):
    """Metadata about parsing results"""
    pages: int = 0
    formulas_extracted: int = 0
    formulas_failed: int = 0
    tables: int = 0
    images: int = 0
    processing_time_ms: int = 0
    docling_time_ms: int = 0
    latex_ocr_time_ms: int = 0


class ParseResponse(BaseModel):
    """Response from parser service"""
    success: bool
    markdown: str
    metadata: ParseMetadata
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    dependencies: Dict[str, str]
    version: str = "1.0.0"


# ============================================================================
# Core Processing Functions
# ============================================================================

async def check_docling_health() -> bool:
    """Check if Docling OCR is available"""
    try:
        response = await http_client.get(f"{DOCLING_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


async def check_latex_ocr_health() -> bool:
    """Check if LaTeX-OCR is available"""
    try:
        response = await http_client.get(f"{LATEX_OCR_URL}/", timeout=5.0)
        return response.status_code in [200, 404]  # 404 means service is up
    except Exception:
        return False


async def call_docling_ocr(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Call Docling OCR to extract document structure
    Returns: Dict with markdown, tables, metadata
    """
    start = time.time()

    try:
        response = await http_client.post(
            f"{DOCLING_URL}/convert/document",
            files={"file": ("document.pdf", pdf_bytes, "application/pdf")},
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()

        elapsed = int((time.time() - start) * 1000)
        print(f"✅ Docling OCR completed in {elapsed}ms")

        return {
            "markdown": result.get("markdown", ""),
            "metadata": result.get("metadata", {}),
            "time_ms": elapsed
        }

    except Exception as e:
        print(f"❌ Docling OCR failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Docling OCR failed: {str(e)}"
        )


def detect_formula_placeholders(markdown: str) -> List[int]:
    """
    Find all formula placeholder positions in markdown
    Returns: List of match positions
    """
    pattern = r'<!-- formula-not-decoded -->'
    matches = list(re.finditer(pattern, markdown))
    print(f"🔍 Found {len(matches)} formula placeholders")
    return [match.start() for match in matches]


def extract_formula_images_from_pdf(pdf_bytes: bytes, max_formulas: int = 50) -> List[str]:
    """
    Extract formula regions from PDF as base64 images
    This is a simplified version - in production, would use bounding boxes from Docling
    Returns: List of base64-encoded images
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        formula_images = []

        # For now, extract small images that are likely formulas (heuristic)
        for page_num in range(min(doc.page_count, 20)):  # Limit to first 20 pages
            page = doc[page_num]
            images = page.get_images()

            for img_index, img in enumerate(images):
                if len(formula_images) >= max_formulas:
                    break

                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # Filter by size (formulas are usually small images)
                    if len(image_bytes) < 50000:  # Less than 50KB
                        # Convert to base64
                        base64_img = base64.b64encode(image_bytes).decode('utf-8')
                        formula_images.append(base64_img)

                except Exception as e:
                    print(f"⚠️  Failed to extract image {img_index} from page {page_num}: {e}")
                    continue

        doc.close()
        print(f"📸 Extracted {len(formula_images)} potential formula images")
        return formula_images

    except Exception as e:
        print(f"❌ PDF image extraction failed: {str(e)}")
        return []


async def call_latex_ocr(image_base64: str) -> Optional[str]:
    """
    Call LaTeX-OCR to convert formula image to LaTeX
    Returns: LaTeX string or None if failed
    """
    try:
        response = await http_client.post(
            f"{LATEX_OCR_URL}/predict",
            json={"image": image_base64},
            timeout=FORMULA_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()

        # Extract LaTeX from response (exact format depends on pix2tex API)
        latex = result.get("latex", result.get("prediction", ""))
        return latex if latex else None

    except Exception as e:
        print(f"⚠️  LaTeX-OCR failed: {str(e)}")
        return None


async def process_formulas(formula_images: List[str]) -> List[Optional[str]]:
    """
    Process multiple formula images in parallel
    Returns: List of LaTeX strings (None for failed conversions)
    """
    start = time.time()

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FORMULAS)

    async def process_one(image_b64: str) -> Optional[str]:
        async with semaphore:
            return await call_latex_ocr(image_b64)

    # Process all formulas
    tasks = [process_one(img) for img in formula_images]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    latex_results = []
    for r in results:
        if isinstance(r, Exception):
            latex_results.append(None)
        else:
            latex_results.append(r)

    elapsed = int((time.time() - start) * 1000)
    success_count = sum(1 for r in latex_results if r is not None)
    print(f"✅ Processed {len(latex_results)} formulas in {elapsed}ms ({success_count} successful)")

    return latex_results, elapsed


def merge_formulas_into_markdown(
    markdown: str,
    placeholder_positions: List[int],
    latex_formulas: List[Optional[str]]
) -> str:
    """
    Replace formula placeholders with LaTeX in markdown
    Returns: Updated markdown
    """
    if not placeholder_positions or not latex_formulas:
        return markdown

    # Replace from end to start to maintain positions
    result = markdown
    placeholder = '<!-- formula-not-decoded -->'

    for pos, latex in zip(reversed(placeholder_positions), reversed(latex_formulas)):
        if latex:
            # Wrap in inline math
            latex_formatted = f"${latex}$"
            result = result[:pos] + latex_formatted + result[pos + len(placeholder):]

    replaced = sum(1 for l in latex_formulas if l is not None)
    print(f"📝 Replaced {replaced}/{len(placeholder_positions)} formula placeholders")

    return result


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service and dependency health"""
    docling_ok = await check_docling_health()
    latex_ocr_ok = await check_latex_ocr_health()

    overall_status = "healthy" if (docling_ok and latex_ocr_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        dependencies={
            "docling": "healthy" if docling_ok else "unhealthy",
            "latex_ocr": "healthy" if latex_ocr_ok else "unhealthy"
        }
    )


@app.post("/parse", response_model=ParseResponse)
async def parse_pdf(
    file: UploadFile = File(...),
    extract_formulas: bool = True,
    extract_images: bool = False,  # Not implemented yet
    extract_tables: bool = True
):
    """
    Parse PDF with complete extraction

    - **file**: PDF file to parse
    - **extract_formulas**: Extract LaTeX formulas (default: true)
    - **extract_images**: Extract embedded images (default: false, future)
    - **extract_tables**: Extract tables (default: true)
    """
    start_time = time.time()

    # Read PDF
    pdf_bytes = await file.read()

    # Size check
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > PDF_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large: {size_mb:.1f}MB (max {PDF_MAX_SIZE_MB}MB)"
        )

    print(f"📄 Processing PDF: {file.filename} ({size_mb:.1f}MB)")

    try:
        # Stage 1: Docling OCR
        docling_result = await call_docling_ocr(pdf_bytes)
        markdown = docling_result["markdown"]
        docling_time = docling_result["time_ms"]

        # Initialize metadata
        metadata = ParseMetadata(
            pages=docling_result["metadata"].get("num_pages", 0),
            docling_time_ms=docling_time
        )

        # Stage 2: Formula extraction (if enabled)
        latex_ocr_time = 0
        if extract_formulas:
            # Detect placeholders
            placeholder_positions = detect_formula_placeholders(markdown)
            metadata.formulas_extracted = len(placeholder_positions)

            if placeholder_positions:
                # Extract formula images from PDF
                formula_images = extract_formula_images_from_pdf(
                    pdf_bytes,
                    max_formulas=len(placeholder_positions)
                )

                # Limit to available images
                num_to_process = min(len(formula_images), len(placeholder_positions))

                if num_to_process > 0:
                    # Process formulas with LaTeX-OCR
                    latex_results, latex_ocr_time = await process_formulas(
                        formula_images[:num_to_process]
                    )

                    # Merge results
                    markdown = merge_formulas_into_markdown(
                        markdown,
                        placeholder_positions[:num_to_process],
                        latex_results
                    )

                    # Update metadata
                    metadata.formulas_failed = sum(1 for r in latex_results if r is None)
                    metadata.formulas_extracted = sum(1 for r in latex_results if r is not None)
                    metadata.latex_ocr_time_ms = latex_ocr_time

        # Calculate total time
        total_time = int((time.time() - start_time) * 1000)
        metadata.processing_time_ms = total_time

        print(f"✅ Parsing complete in {total_time}ms")
        print(f"   - Docling: {docling_time}ms")
        print(f"   - LaTeX-OCR: {latex_ocr_time}ms")
        print(f"   - Formulas: {metadata.formulas_extracted}/{metadata.formulas_extracted + metadata.formulas_failed}")

        return ParseResponse(
            success=True,
            markdown=markdown,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Parsing failed: {str(e)}")
        import traceback
        traceback.print_exc()

        return ParseResponse(
            success=False,
            markdown="",
            metadata=ParseMetadata(),
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
