"""
MinerU Native Service

FastAPI service that runs MinerU natively on macOS with Apple Silicon GPU acceleration.
Designed to be called by the Docker backend for advanced PDF processing.
"""

import asyncio
import base64
import json
from pathlib import Path
from typing import Optional
from PIL import Image
import io
import fitz  # PyMuPDF for image extraction

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

from mineru.backend.pipeline.pipeline_analyze import doc_analyze


app = FastAPI(
    title="MinerU Native Service",
    description="Native MinerU PDF processing service for Apple Silicon",
    version="1.0.0"
)

# Add CORS middleware to allow browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ImageData(BaseModel):
    """Image extracted from PDF with metadata"""
    name: str
    base64: str
    page_number: Optional[int] = None
    image_index: int
    mime_type: str = "image/png"


class ProcessResponse(BaseModel):
    success: bool
    text: str
    images: list[ImageData]
    metadata: dict
    message: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mineru-native"}


@app.post("/process", response_model=ProcessResponse)
async def process_pdf(
    file: UploadFile = File(...),
    extract_charts: bool = Form(False),
    chart_provider: str = Form("auto"),
    device: str = Form("mps"),
    lang: str = Form("en")
):
    """
    Process a PDF file with MinerU

    Args:
        file: PDF file to process
        extract_charts: Whether to extract chart data from images
        chart_provider: Chart extraction provider ("auto", "local", "claude")
        device: Device to use ("mps" for Apple GPU, "cpu" for CPU)
        lang: Language code (default: "en")

    Returns:
        Extracted text, images, and metadata
    """
    try:
        # Read PDF content
        content = await file.read()

        # Process PDF with MinerU
        # Returns: (infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list)
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

        # Count formulas and tables from layout detections
        # MinerU uses category_id to identify different element types
        # Based on MinerU source: category_id 13 = formula, category_id 5 = table
        formula_count = 0
        table_count = 0
        for page_result in pdf_results:
            layout_dets = page_result.get('layout_dets', [])
            for det in layout_dets:
                category_id = det.get('category_id', -1)
                if category_id == 13:  # Formula
                    formula_count += 1
                elif category_id == 5:  # Table
                    table_count += 1

        # Extract text using PdfDocument object (pypdfium2)
        text_parts = []
        total_chars_extracted = 0

        if pdf_doc:
            page_count = len(pdf_doc)
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
                    print(f"Warning: Page {page_idx + 1} text extraction error - {str(e)}")
                    text_parts.append("[Text extraction failed for this page]\n\n")

        text = "\n".join(text_parts)

        # Extract images using PyMuPDF (more reliable than MinerU for raw image extraction)
        image_data_list = []
        try:
            pdf_doc_fitz = fitz.open(stream=content, filetype="pdf")
            img_idx = 0

            for page_num in range(len(pdf_doc_fitz)):
                page = pdf_doc_fitz[page_num]
                images = page.get_images()

                for img in images:
                    try:
                        xref = img[0]  # xref is the image reference
                        base_image = pdf_doc_fitz.extract_image(xref)

                        if base_image:
                            img_bytes = base_image["image"]
                            img_ext = base_image["ext"]

                            # Convert to PIL Image to standardize format
                            pil_image = Image.open(io.BytesIO(img_bytes))

                            # Convert to PNG
                            png_buffer = io.BytesIO()
                            pil_image.save(png_buffer, format='PNG')
                            png_bytes = png_buffer.getvalue()

                            # Encode to base64
                            img_base64 = base64.b64encode(png_bytes).decode('utf-8')

                            image_data_list.append(ImageData(
                                name=f"page{page_num + 1}_image{img_idx + 1}.png",
                                base64=img_base64,
                                page_number=page_num + 1,
                                image_index=img_idx,
                                mime_type="image/png"
                            ))
                            img_idx += 1
                    except Exception as e:
                        print(f"Warning: Failed to extract image {img_idx} from page {page_num + 1}: {e}")

            pdf_doc_fitz.close()
        except Exception as e:
            print(f"Warning: Image extraction failed: {e}")
            # Continue without images rather than failing

        # Log processing summary
        print(f"Processed {file.filename}: {len(pdf_results)} pages, "
              f"{total_chars_extracted} chars, {formula_count} formulas, "
              f"{table_count} tables, {len(image_data_list)} images")

        # Build response
        return ProcessResponse(
            success=True,
            text=text,
            images=image_data_list,
            metadata={
                "filename": file.filename,
                "pages": len(pdf_results),  # Expected by backend
                "page_count": len(pdf_results),  # Kept for compatibility
                "chars_extracted": total_chars_extracted,
                "formulas_count": formula_count,  # Expected by backend
                "tables_count": table_count,  # Expected by backend
                "images_extracted": len(image_data_list),
                "extract_charts": extract_charts,
                "chart_provider": chart_provider,
                "device": device,
                "lang": lang
            },
            message="PDF processed successfully"
        )

    except Exception as e:
        import traceback
        error_detail = f"MinerU processing failed: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "MinerU Native Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "process": "/process (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    # Run service on port 8055
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8055,
        log_level="info"
    )
