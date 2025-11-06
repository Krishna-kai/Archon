"""
Marker PDF to Markdown FastAPI Service
Converts PDFs to Markdown with LaTeX formulas and structured tables using marker CLI
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import tempfile
import os
import subprocess
import json

app = FastAPI(
    title="Marker PDF Service",
    description="PDF to Markdown with formula and table extraction for Archon",
    version="1.0.0"
)

marker_available = False

@app.on_event("startup")
async def startup_event():
    """Check if Marker CLI is available"""
    global marker_available
    print("🚀 Checking Marker CLI availability...")
    try:
        result = subprocess.run(
            ["marker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        marker_available = (result.returncode == 0)
        if marker_available:
            print(f"✅ Marker CLI initialized successfully")
        else:
            print(f"❌ Marker CLI not working: {result.stderr}")
    except Exception as e:
        print(f"❌ Marker CLI check failed: {e}")
        marker_available = False

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if marker_available else "initializing",
        "service": "marker-pdf",
        "marker_loaded": marker_available
    }

class MarkerResponse(BaseModel):
    """Response model for Marker PDF conversion"""
    success: bool
    markdown: Optional[str] = None
    metadata: Optional[Dict] = None
    error: Optional[str] = None

@app.post("/convert", response_model=MarkerResponse)
async def convert_pdf_to_markdown(file: UploadFile = File(...)):
    """
    Convert PDF to Markdown with LaTeX formulas and tables using marker CLI

    Args:
        file: PDF file upload

    Returns:
        MarkerResponse with markdown content and metadata
    """
    if not marker_available:
        raise HTTPException(status_code=500, detail="Marker CLI not available")

    # Create temporary directory for input and output
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Save uploaded PDF
            pdf_path = os.path.join(tmpdir, "input.pdf")
            with open(pdf_path, "wb") as f:
                contents = await file.read()
                f.write(contents)

            print(f"Converting: {file.filename} ({len(contents)} bytes)")

            # Run marker CLI
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir, exist_ok=True)

            result = subprocess.run(
                [
                    "marker",
                    pdf_path,
                    "--output_dir", output_dir,
                    "--output_format", "markdown"
                ],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                print(f"Marker CLI failed: {result.stderr}")
                return MarkerResponse(
                    success=False,
                    markdown="",
                    error=f"Marker conversion failed: {result.stderr}"
                )

            # Read the generated markdown file
            markdown_file = os.path.join(output_dir, "input.md")
            if not os.path.exists(markdown_file):
                return MarkerResponse(
                    success=False,
                    markdown="",
                    error="Marker output file not found"
                )

            with open(markdown_file, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # Try to read metadata if available
            metadata_file = os.path.join(output_dir, "input_meta.json")
            metadata = {}
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                except:
                    pass

            metadata.update({
                "filename": file.filename,
                "file_size": len(contents),
                "service": "marker"
            })

            print(f"✅ Conversion successful: {len(markdown_content)} chars")

            return MarkerResponse(
                success=True,
                markdown=markdown_content,
                metadata=metadata
            )

        except subprocess.TimeoutExpired:
            print(f"Marker conversion timed out for {file.filename}")
            return MarkerResponse(
                success=False,
                markdown="",
                error="Conversion timed out (>2 minutes)"
            )
        except Exception as e:
            print(f"Marker conversion failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return MarkerResponse(
                success=False,
                markdown="",
                error=str(e)
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
