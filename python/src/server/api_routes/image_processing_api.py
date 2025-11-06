"""
API routes for image content processing.
Provides endpoints to process and retrieve image content using local-only services.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.image_content_processor import get_image_content_processor
from ..services.storage import get_image_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["Image Processing"])


class ProcessImageRequest(BaseModel):
    """Request to process a single image"""

    force_refresh: bool = False


class ProcessSourceImagesRequest(BaseModel):
    """Request to process all images for a source"""

    force_refresh: bool = False


@router.post("/{image_id}/process")
async def process_single_image(image_id: str, request: ProcessImageRequest):
    """
    Process a single image to extract OCR text, classify type, and generate embeddings.

    This uses local-only services (Ollama) for all processing.

    Args:
        image_id: UUID of the image to process
        request: Processing options

    Returns:
        Processing results with extracted content
    """

    try:
        processor = get_image_content_processor()

        # Check if service is available
        if not await processor.is_available():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not available. Please ensure Ollama is running.",
            )

        # Process image
        result = await processor.process_image_content(
            UUID(image_id), force_refresh=request.force_refresh
        )

        return {
            "success": True,
            "message": "Image processed successfully",
            "result": result,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image ID format")
    except Exception as e:
        logger.error(f"Error processing image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/source/{source_id}/process-all")
async def process_source_images(source_id: str, request: ProcessSourceImagesRequest):
    """
    Process all images for a source document.

    This processes multiple images sequentially using local-only services.

    Args:
        source_id: Source document ID
        request: Processing options

    Returns:
        Summary of processing results for all images
    """

    try:
        processor = get_image_content_processor()

        # Check if service is available
        if not await processor.is_available():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not available. Please ensure Ollama is running.",
            )

        # Process all images
        result = await processor.process_all_images_for_source(
            source_id, force_refresh=request.force_refresh
        )

        return {
            "success": True,
            "message": f"Processed {result.get('processed', 0)} images",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error processing images for source {source_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/{image_id}/content")
async def get_image_content(image_id: str):
    """
    Get extracted content for an image.

    Returns OCR text, classification, structured data, and embedding status.

    Args:
        image_id: UUID of the image

    Returns:
        Image content and metadata
    """

    try:
        processor = get_image_content_processor()
        record = await processor._get_image_record(UUID(image_id))

        if not record:
            raise HTTPException(status_code=404, detail="Image not found")

        # Get signed URL
        image_service = get_image_storage_service()
        signed_url = image_service.get_signed_url(record["storage_path"])

        return {
            "success": True,
            "image": {
                "id": record["id"],
                "source_id": record["source_id"],
                "page_number": record.get("page_number"),
                "image_index": record.get("image_index"),
                "image_name": record.get("image_name"),
                "image_url": signed_url,
                "mime_type": record.get("mime_type"),
                "content": {
                    "ocr_text": record.get("ocr_text"),
                    "image_type": record.get("image_type"),
                    "surrounding_text": record.get("surrounding_text"),
                    "structured_data": (
                        record.get("metadata", {}).get("structured_data")
                        if record.get("metadata")
                        else None
                    ),
                    "classification": (
                        record.get("metadata", {}).get("classification")
                        if record.get("metadata")
                        else None
                    ),
                },
                "processing_status": {
                    "ocr_processed": record.get("ocr_processed", False),
                    "embedding_generated": record.get("embedding_generated", False),
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at"),
                },
            },
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image content {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")


@router.get("/source/{source_id}")
async def get_source_images(source_id: str, include_content: bool = False):
    """
    Get all images for a source document.

    Args:
        source_id: Source document ID
        include_content: Whether to include extracted content (default: False)

    Returns:
        List of images with optional content
    """

    try:
        image_service = get_image_storage_service()
        images = await image_service.get_images_by_source(source_id, include_signed_urls=True)

        # If content requested, add it
        if include_content:
            processor = get_image_content_processor()
            for image in images:
                record = await processor._get_image_record(UUID(image["id"]))
                if record:
                    image["content"] = {
                        "ocr_text": record.get("ocr_text"),
                        "image_type": record.get("image_type"),
                        "ocr_processed": record.get("ocr_processed", False),
                        "embedding_generated": record.get("embedding_generated", False),
                    }

        return {
            "success": True,
            "source_id": source_id,
            "total": len(images),
            "images": images,
        }

    except Exception as e:
        logger.error(f"Error getting images for source {source_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get images: {str(e)}")


@router.get("/health")
async def check_service_health():
    """
    Check if image processing services are available.

    Returns:
        Health status of local services (Ollama)
    """

    try:
        processor = get_image_content_processor()
        ollama_available = await processor.is_available()

        return {
            "status": "healthy" if ollama_available else "degraded",
            "services": {
                "ollama": {
                    "available": ollama_available,
                    "vision_model": processor.vision_model,
                    "embed_model": processor.embed_model,
                }
            },
        }

    except Exception as e:
        logger.error(f"Error checking service health: {e}")
        return {"status": "unhealthy", "error": str(e)}
