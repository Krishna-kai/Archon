"""
OCRmyPDF Service for Archon
FastAPI service providing OCR capabilities using OCRmyPDF container

Optimized for Mac M4 with native ARM64 support
"""
import os
import io
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import time

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="OCRmyPDF Service",
    description="Document OCR service powered by OCRmyPDF (ARM64-native)",
    version="1.0.0"
)

# Configuration
OCRMYPDF_IMAGE = os.getenv("OCRMYPDF_IMAGE", "jbarlow83/ocrmypdf-alpine")
SERVICE_MODE = os.getenv("SERVICE_MODE", "docker")  # docker or native


class OCRResponse(BaseModel):
    """Response model for OCR operations"""
    success: bool
    text: Optional[str] = None
    markdown: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None
    backend: str = "ocrmypdf"


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from OCR'd PDF using pdfminer or similar
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")

        doc.close()
        return "\n".join(text_parts)

    except Exception as e:
        raise Exception(f"Failed to extract text from OCR'd PDF: {e}")


def run_ocrmypdf_docker(input_path: str, output_path: str) -> bool:
    """
    Run OCRmyPDF using Docker container with stdin/stdout
    Returns True on success
    """
    try:
        # Read input PDF
        with open(input_path, 'rb') as f:
            input_data = f.read()

        # Run OCRmyPDF with stdin/stdout to avoid volume mounting issues
        cmd = [
            "docker", "run", "--rm", "-i",
            OCRMYPDF_IMAGE,
            "--deskew",           # Straighten pages
            "--rotate-pages",     # Auto-rotate pages
            "--optimize", "1",    # Light optimization
            "--output-type", "pdf",
            "--skip-text",        # Skip pages that already have text
            "-",                  # Read from stdin
            "-"                   # Write to stdout
        ]

        print(f"Running OCRmyPDF via stdin/stdout: {' '.join(cmd[:5])}...")

        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            # Write output PDF
            with open(output_path, 'wb') as f:
                f.write(result.stdout)
            print(f"OCRmyPDF completed successfully ({len(result.stdout)} bytes)")
            return True
        else:
            error_msg = result.stderr.decode() if result.stderr else "Unknown error"
            print(f"OCRmyPDF failed: {error_msg}")
            return False

    except subprocess.TimeoutExpired:
        raise Exception("OCR processing timed out after 5 minutes")
    except Exception as e:
        raise Exception(f"Failed to run OCRmyPDF: {e}")


@app.on_event("startup")
async def startup_event():
    """Check OCRmyPDF availability on startup"""
    print("🚀 OCRmyPDF Service starting...")
    print(f"Service mode: {SERVICE_MODE}")
    print(f"OCRmyPDF image: {OCRMYPDF_IMAGE}")

    # Check if Docker is available
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Docker available: {result.stdout.strip()}")
        else:
            print("⚠️  Docker not available - OCR will fail")
    except Exception as e:
        print(f"⚠️  Docker check failed: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check Docker availability
    docker_available = False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5
        )
        docker_available = result.returncode == 0
    except:
        pass

    return {
        "status": "healthy" if docker_available else "degraded",
        "service": "ocrmypdf",
        "backend": "docker",
        "docker_available": docker_available,
        "image": OCRMYPDF_IMAGE
    }


@app.post("/ocr/pdf", response_model=OCRResponse)
async def ocr_pdf(
    file: UploadFile = File(...),
    output_format: str = Form("markdown")
):
    """
    OCR a PDF document using OCRmyPDF

    Args:
        file: PDF file
        output_format: Output format (markdown, text)

    Returns:
        OCRResponse with extracted content
    """
    start_time = time.time()

    try:
        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            input_path = os.path.join(temp_dir, "input.pdf")
            output_path = os.path.join(temp_dir, "output.pdf")

            with open(input_path, "wb") as f:
                contents = await file.read()
                f.write(contents)

            print(f"Processing PDF: {file.filename} ({len(contents)} bytes)")

            # Run OCRmyPDF
            success = run_ocrmypdf_docker(input_path, output_path)

            if not success:
                return OCRResponse(
                    success=False,
                    error="OCRmyPDF processing failed. Check logs for details.",
                    backend="ocrmypdf"
                )

            # Extract text from OCR'd PDF
            try:
                extracted_text = extract_text_from_pdf(output_path)
            except Exception as e:
                return OCRResponse(
                    success=False,
                    error=f"Text extraction failed: {str(e)}",
                    backend="ocrmypdf"
                )

            processing_time = time.time() - start_time

            # Count pages
            import fitz
            doc = fitz.open(output_path)
            page_count = len(doc)
            doc.close()

            print(f"OCR completed: {page_count} pages in {processing_time:.2f}s")

            return OCRResponse(
                success=True,
                text=extracted_text if output_format == "text" else None,
                markdown=extracted_text if output_format == "markdown" else None,
                metadata={
                    "filename": file.filename,
                    "page_count": page_count,
                    "processing_time": f"{processing_time:.2f}s",
                    "backend": "ocrmypdf",
                    "docker_image": OCRMYPDF_IMAGE
                },
                backend="ocrmypdf"
            )

    except Exception as e:
        print(f"PDF OCR error: {str(e)}")
        return OCRResponse(
            success=False,
            error=str(e),
            backend="ocrmypdf"
        )


@app.post("/ocr/image", response_model=OCRResponse)
async def ocr_image(
    file: UploadFile = File(...),
    output_format: str = Form("markdown")
):
    """
    OCR an image by converting to PDF first, then using OCRmyPDF

    Args:
        file: Image file (PNG, JPG, JPEG, TIFF)
        output_format: Output format (markdown, text)

    Returns:
        OCRResponse with extracted content
    """
    try:
        from PIL import Image
        import img2pdf

        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded image
            image_path = os.path.join(temp_dir, f"image{Path(file.filename).suffix}")
            with open(image_path, "wb") as f:
                contents = await file.read()
                f.write(contents)

            # Convert image to PDF
            pdf_path = os.path.join(temp_dir, "image.pdf")
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_path))

            # Use the PDF OCR endpoint
            # Create a new UploadFile from the PDF
            with open(pdf_path, "rb") as f:
                from fastapi import UploadFile
                pdf_file = UploadFile(filename="image.pdf", file=f)
                return await ocr_pdf(pdf_file, output_format)

    except Exception as e:
        return OCRResponse(
            success=False,
            error=f"Image OCR failed: {str(e)}",
            backend="ocrmypdf"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9001))
    uvicorn.run(app, host="0.0.0.0", port=port)
