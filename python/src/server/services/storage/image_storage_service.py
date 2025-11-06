"""
Image Storage Service

Handles storage and retrieval of document images in Supabase Storage and metadata in PostgreSQL.
Supports extracting images from PDFs (charts, formulas, diagrams) for enhanced document understanding.
"""

import base64
import logging
from datetime import timedelta
from typing import Optional
from uuid import UUID, uuid4

from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


class ImageStorageService:
    """Service for managing document images in Supabase Storage and database."""

    BUCKET_NAME = "document-images"
    SIGNED_URL_EXPIRY = timedelta(hours=1)  # URLs valid for 1 hour

    def __init__(self, supabase_client=None):
        """
        Initialize image storage service.

        Args:
            supabase_client: Supabase client instance (auto-initialized if None)
        """
        if supabase_client is None:
            from ...utils import get_supabase_client

            supabase_client = get_supabase_client()
        self.supabase = supabase_client

    def _generate_storage_path(
        self, source_id: str, page_number: Optional[int], image_index: int, mime_type: str
    ) -> str:
        """
        Generate storage path for an image.

        Format: {source_id}/{page_number}_{image_index}.{ext}
        For file uploads without pages: {source_id}/img_{image_index}.{ext}

        Args:
            source_id: Source document ID
            page_number: PDF page number (1-indexed, None for file uploads)
            image_index: Image index within page (0-indexed)
            mime_type: MIME type (e.g., "image/jpeg")

        Returns:
            Storage path string
        """
        # Determine file extension from MIME type
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        ext = ext_map.get(mime_type, "jpg")

        # Build filename
        if page_number is not None:
            filename = f"page_{page_number}_img_{image_index}.{ext}"
        else:
            filename = f"img_{image_index}.{ext}"

        return f"{source_id}/{filename}"

    async def upload_image(
        self,
        source_id: str,
        image_data: str,
        mime_type: str,
        page_number: Optional[int] = None,
        image_index: int = 0,
        image_name: Optional[str] = None,
        page_id: Optional[UUID] = None,
        image_type: Optional[str] = None,
        ocr_text: Optional[str] = None,
    ) -> dict:
        """
        Upload image to Supabase Storage and store metadata in database.

        Args:
            source_id: Source document ID
            image_data: Base64-encoded image data
            mime_type: MIME type (e.g., "image/jpeg")
            page_number: PDF page number (1-indexed, None for file uploads)
            image_index: Image index within page (0-indexed)
            image_name: Original image filename
            page_id: Optional page UUID for web crawls
            image_type: Optional type classification (chart, diagram, formula, etc.)
            ocr_text: Optional OCR text extracted from image

        Returns:
            dict with image metadata including id, storage_path, and signed_url
        """
        try:
            # Decode base64 image data
            image_bytes = base64.b64decode(image_data)

            # Generate storage path
            storage_path = self._generate_storage_path(
                source_id, page_number, image_index, mime_type
            )

            # Upload to Supabase Storage
            logger.info(f"Uploading image to storage: {storage_path}")
            result = self.supabase.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=image_bytes,
                file_options={"content-type": mime_type, "upsert": "true"},
            )

            if not result:
                raise Exception("Storage upload returned no result")

            # Store metadata in database
            image_id = uuid4()
            image_metadata = {
                "id": str(image_id),
                "source_id": source_id,
                "page_id": str(page_id) if page_id else None,
                "page_number": page_number,
                "image_index": image_index,
                "storage_path": storage_path,
                "file_name": image_name,
                "mime_type": mime_type,
                "file_size": len(image_bytes),
                "image_type": image_type,
                "ocr_text": ocr_text,
                "width": None,  # TODO: Extract from image if needed
                "height": None,  # TODO: Extract from image if needed
            }

            db_result = (
                self.supabase.table("archon_document_images").insert(image_metadata).execute()
            )

            if not db_result.data:
                raise Exception("Database insert returned no data")

            # Generate signed URL for immediate access
            signed_url = self.get_signed_url(storage_path)

            logger.info(f"Successfully uploaded image: {storage_path}")
            return {
                **db_result.data[0],
                "signed_url": signed_url,
            }

        except APIError as e:
            logger.error(f"Supabase API error uploading image: {e}")
            raise Exception(f"Failed to upload image: {e}")
        except Exception as e:
            logger.error(f"Error uploading image: {e}", exc_info=True)
            raise

    def get_signed_url(self, storage_path: str, expires_in: Optional[int] = None) -> str:
        """
        Generate signed URL for accessing an image.

        Args:
            storage_path: Storage path of the image
            expires_in: Optional expiration time in seconds (default: 1 hour)

        Returns:
            Signed URL string
        """
        try:
            if expires_in is None:
                expires_in = int(self.SIGNED_URL_EXPIRY.total_seconds())

            result = self.supabase.storage.from_(self.BUCKET_NAME).create_signed_url(
                path=storage_path, expires_in=expires_in
            )

            if not result or "signedURL" not in result:
                raise Exception("Failed to generate signed URL")

            return result["signedURL"]

        except Exception as e:
            logger.error(f"Error generating signed URL for {storage_path}: {e}")
            raise

    async def get_images_by_source(
        self, source_id: str, include_signed_urls: bool = True
    ) -> list[dict]:
        """
        Retrieve all images for a source document.

        Args:
            source_id: Source document ID
            include_signed_urls: Whether to generate signed URLs (default: True)

        Returns:
            List of image metadata dicts with optional signed URLs
        """
        try:
            result = (
                self.supabase.table("archon_document_images")
                .select("*")
                .eq("source_id", source_id)
                .order("page_number", desc=False)
                .order("image_index", desc=False)
                .execute()
            )

            images = result.data or []

            # Add signed URLs if requested
            if include_signed_urls:
                for image in images:
                    try:
                        image["signed_url"] = self.get_signed_url(image["storage_path"])
                    except Exception as e:
                        logger.warning(f"Failed to generate URL for {image['storage_path']}: {e}")
                        image["signed_url"] = None

            logger.info(f"Retrieved {len(images)} images for source {source_id}")
            return images

        except Exception as e:
            logger.error(f"Error retrieving images for source {source_id}: {e}")
            raise

    async def get_images_by_page(
        self, page_id: UUID, include_signed_urls: bool = True
    ) -> list[dict]:
        """
        Retrieve all images for a specific page (web crawls only).

        Args:
            page_id: Page UUID
            include_signed_urls: Whether to generate signed URLs (default: True)

        Returns:
            List of image metadata dicts with optional signed URLs
        """
        try:
            result = (
                self.supabase.table("archon_document_images")
                .select("*")
                .eq("page_id", str(page_id))
                .order("image_index", desc=False)
                .execute()
            )

            images = result.data or []

            # Add signed URLs if requested
            if include_signed_urls:
                for image in images:
                    try:
                        image["signed_url"] = self.get_signed_url(image["storage_path"])
                    except Exception as e:
                        logger.warning(f"Failed to generate URL for {image['storage_path']}: {e}")
                        image["signed_url"] = None

            logger.info(f"Retrieved {len(images)} images for page {page_id}")
            return images

        except Exception as e:
            logger.error(f"Error retrieving images for page {page_id}: {e}")
            raise

    async def delete_images_by_source(self, source_id: str) -> int:
        """
        Delete all images for a source document (storage + database).

        Args:
            source_id: Source document ID

        Returns:
            Number of images deleted
        """
        try:
            # Get all images for this source
            images = await self.get_images_by_source(source_id, include_signed_urls=False)

            if not images:
                logger.info(f"No images found for source {source_id}")
                return 0

            # Delete from storage
            storage_paths = [img["storage_path"] for img in images]
            for path in storage_paths:
                try:
                    self.supabase.storage.from_(self.BUCKET_NAME).remove([path])
                except Exception as e:
                    logger.warning(f"Failed to delete storage file {path}: {e}")

            # Delete from database (CASCADE will handle this if source is deleted)
            # But explicitly delete for cleanup operations
            result = (
                self.supabase.table("archon_document_images")
                .delete()
                .eq("source_id", source_id)
                .execute()
            )

            deleted_count = len(result.data) if result.data else len(images)
            logger.info(f"Deleted {deleted_count} images for source {source_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting images for source {source_id}: {e}")
            raise

    async def update_image_ocr(self, image_id: UUID, ocr_text: str) -> dict:
        """
        Update OCR text for an image (for searchability).

        Args:
            image_id: Image UUID
            ocr_text: Extracted OCR text

        Returns:
            Updated image metadata
        """
        try:
            result = (
                self.supabase.table("archon_document_images")
                .update({"ocr_text": ocr_text})
                .eq("id", str(image_id))
                .execute()
            )

            if not result.data:
                raise Exception(f"Image {image_id} not found")

            logger.info(f"Updated OCR text for image {image_id}")
            return result.data[0]

        except Exception as e:
            logger.error(f"Error updating OCR for image {image_id}: {e}")
            raise


# Singleton instance
_image_storage_service: Optional[ImageStorageService] = None


def get_image_storage_service() -> ImageStorageService:
    """Get or create singleton image storage service instance."""
    global _image_storage_service
    if _image_storage_service is None:
        _image_storage_service = ImageStorageService()
    return _image_storage_service
