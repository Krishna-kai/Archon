"""
LaTeX-OCR Service - Convert formula images to LaTeX
Native ARM64/AMD64 compatible wrapper for pix2tex
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import base64
import io
from PIL import Image

app = FastAPI(
    title="LaTeX-OCR Service",
    description="Convert formula images to LaTeX using pix2tex",
    version="1.0.0"
)

# Lazy load model to save startup time
model = None


def get_model():
    """Lazy load the pix2tex model"""
    global model
    if model is None:
        try:
            from pix2tex.cli import LatexOCR
            print("🔄 Loading pix2tex model...")
            model = LatexOCR()
            print("✅ pix2tex model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load pix2tex model: {e}")
            raise
    return model


class PredictRequest(BaseModel):
    """Request model for LaTeX prediction"""
    image: str  # Base64-encoded image


class PredictResponse(BaseModel):
    """Response model for LaTeX prediction"""
    latex: str
    success: bool
    error: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "OK",
        "status-code": 200,
        "data": {}
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check if model can be loaded
        get_model()
        return {
            "status": "healthy",
            "model_loaded": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "model_loaded": False,
            "error": str(e)
        }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Convert formula image to LaTeX

    - **image**: Base64-encoded image of the formula
    """
    try:
        # Decode base64 image
        try:
            image_data = base64.b64decode(request.image)
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image data: {str(e)}"
            )

        # Get model and predict
        try:
            ocr_model = get_model()
            latex = ocr_model(image)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Model prediction failed: {str(e)}"
            )

        return PredictResponse(
            latex=latex,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        return PredictResponse(
            latex="",
            success=False,
            error=str(e)
        )


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", "9001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
