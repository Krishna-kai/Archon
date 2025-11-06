"""
FastAPI service for Docling Document Conversion
Provides OCR and document parsing endpoints for Archon
"""
import os
import io
import tempfile
from pathlib import Path
from typing import Optional, List
import time

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

app = FastAPI(
    title="Docling OCR Service",
    description="Document parsing and OCR service powered by IBM Docling (ARM64-native)",
    version="1.0.0"
)

# Initialize converter (happens once at startup)
converter = None

class OCRResponse(BaseModel):
    """Response model for OCR operations"""
    success: bool
    markdown: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    doctags: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


def safe_count_tables(document) -> int:
    """Safely count tables in document, handling various data structures"""
    try:
        if not hasattr(document, 'pages'):
            return 0

        table_count = 0
        for page in document.pages:
            # Skip if page is not an object (e.g., int page number)
            if not hasattr(page, '__dict__'):
                continue

            # Check if page has assembled attribute
            if hasattr(page, 'assembled'):
                assembled = page.assembled
                # Check if assembled has elements
                if hasattr(assembled, 'elements'):
                    for item in assembled.elements:
                        # Check if item is a table
                        if hasattr(item, '__class__') and 'Table' in item.__class__.__name__:
                            table_count += 1
        return table_count
    except Exception as e:
        print(f"Warning: Could not count tables: {str(e)}")
        return 0


def safe_get_page_count(document) -> int:
    """Safely get page count from document"""
    try:
        if hasattr(document, 'pages'):
            pages = document.pages
            # Check if pages is iterable and count
            if hasattr(pages, '__len__'):
                return len(pages)
            elif hasattr(pages, '__iter__'):
                return sum(1 for _ in pages)
        return 1  # Default to 1 page if unknown
    except Exception as e:
        print(f"Warning: Could not count pages: {str(e)}")
        return 1


@app.on_event("startup")
async def startup_event():
    """Initialize Docling converter on startup"""
    global converter

    print("🚀 Initializing Docling converter...")
    start_time = time.time()

    # Configure pipeline options for better performance
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True  # Enable OCR for scanned documents
    pipeline_options.do_table_structure = True  # Enable table recognition

    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.IMAGE,
            InputFormat.DOCX,
            InputFormat.PPTX,
            InputFormat.HTML,
            InputFormat.XLSX,
            InputFormat.MD,
        ]
    )

    load_time = time.time() - start_time
    print(f"✅ Docling converter initialized in {load_time:.2f} seconds")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "docling-ocr",
        "converter_loaded": converter is not None,
        "backend": "pypdfium2",
        "platform": "Mac M4 compatible"
    }


@app.post("/ocr/image", response_model=OCRResponse)
async def ocr_image(
    file: UploadFile = File(...),
    output_format: str = Form("markdown"),
    include_tables: bool = Form(True)
):
    """
    OCR a single image

    Args:
        file: Image file (PNG, JPG, JPEG, TIFF)
        output_format: Output format (markdown, html, text, doctags)
        include_tables: Enable table structure recognition

    Returns:
        OCRResponse with extracted content
    """
    try:
        if not converter:
            raise HTTPException(status_code=500, detail="Converter not initialized")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Convert document
            start_time = time.time()
            result = converter.convert(tmp_path)
            conversion_time = time.time() - start_time

            # Export to requested format
            if output_format == "markdown":
                content = result.document.export_to_markdown()
            elif output_format == "html":
                content = result.document.export_to_html()
            elif output_format == "text":
                content = result.document.export_to_markdown()  # Use markdown as text base
            elif output_format == "doctags":
                content = result.document.export_to_doctags()
            else:
                content = result.document.export_to_markdown()

            # Prepare metadata with safe extraction
            metadata = {
                "filename": file.filename,
                "output_format": output_format,
                "conversion_time": f"{conversion_time:.2f}s",
                "num_pages": safe_get_page_count(result.document),
                "num_tables": safe_count_tables(result.document),
            }

            return OCRResponse(
                success=True,
                markdown=content if output_format == "markdown" else None,
                text=content if output_format == "text" else None,
                html=content if output_format == "html" else None,
                doctags=content if output_format == "doctags" else None,
                metadata=metadata
            )

        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        return OCRResponse(
            success=False,
            error=str(e)
        )


@app.post("/ocr/pdf", response_model=OCRResponse)
async def ocr_pdf(
    file: UploadFile = File(...),
    output_format: str = Form("markdown"),
    include_tables: bool = Form(True),
    do_ocr: bool = Form(True)
):
    """
    OCR a PDF document (all pages)

    Args:
        file: PDF file
        output_format: Output format (markdown, html, text, doctags)
        include_tables: Enable table structure recognition
        do_ocr: Enable OCR for scanned PDFs

    Returns:
        OCRResponse with extracted content from all pages
    """
    try:
        if not converter:
            raise HTTPException(status_code=500, detail="Converter not initialized")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Convert document
            start_time = time.time()
            result = converter.convert(tmp_path)
            conversion_time = time.time() - start_time

            # Export to requested format
            if output_format == "markdown":
                content = result.document.export_to_markdown()
            elif output_format == "html":
                content = result.document.export_to_html()
            elif output_format == "text":
                content = result.document.export_to_markdown()
            elif output_format == "doctags":
                content = result.document.export_to_doctags()
            else:
                content = result.document.export_to_markdown()

            # Prepare metadata with safe extraction
            metadata = {
                "filename": file.filename,
                "output_format": output_format,
                "conversion_time": f"{conversion_time:.2f}s",
                "num_pages": safe_get_page_count(result.document),
                "num_tables": safe_count_tables(result.document),
            }

            return OCRResponse(
                success=True,
                markdown=content if output_format == "markdown" else None,
                text=content if output_format == "text" else None,
                html=content if output_format == "html" else None,
                doctags=content if output_format == "doctags" else None,
                metadata=metadata
            )

        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        return OCRResponse(
            success=False,
            error=str(e)
        )


@app.post("/ocr/batch", response_model=List[OCRResponse])
async def ocr_batch(
    files: List[UploadFile] = File(...),
    output_format: str = Form("markdown"),
    include_tables: bool = Form(True)
):
    """
    OCR multiple files in batch

    Args:
        files: List of files (images or PDFs)
        output_format: Output format (markdown, html, text, doctags)
        include_tables: Enable table structure recognition

    Returns:
        List of OCRResponse objects
    """
    responses = []

    for file in files:
        try:
            # Determine if PDF or image
            suffix = Path(file.filename).suffix.lower()
            if suffix == '.pdf':
                response = await ocr_pdf(file, output_format, include_tables)
            else:
                response = await ocr_image(file, output_format, include_tables)
            responses.append(response)
        except Exception as e:
            responses.append(OCRResponse(
                success=False,
                error=f"Failed to process {file.filename}: {str(e)}"
            ))

    return responses


@app.post("/convert/document")
async def convert_document(
    file: UploadFile = File(...),
    output_format: str = Form("markdown")
):
    """
    Convert any supported document format
    Supports: PDF, DOCX, PPTX, XLSX, HTML, MD, images

    Args:
        file: Document file
        output_format: Output format (markdown, html, text, doctags)

    Returns:
        Converted document content
    """
    return await ocr_pdf(file, output_format) if file.filename.endswith('.pdf') else await ocr_image(file, output_format)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
