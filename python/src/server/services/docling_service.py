"""
Docling OCR Service Client

Provides HTTP client interface for Docling OCR service with service discovery integration.
"""

import httpx
import logging
from typing import Optional

from ..config.service_discovery import get_docling_ocr_url, is_service_available

logger = logging.getLogger(__name__)


class DoclingServiceClient:
    """HTTP client for Docling OCR service"""

    def __init__(self):
        self.service_name = "docling_ocr"

    def is_available(self) -> bool:
        """Check if Docling OCR service is configured and available"""
        return is_service_available(self.service_name)

    async def process_pdf(
        self,
        file_content: bytes,
        filename: str,
        output_format: str = "text",
        do_ocr: bool = False,
        include_tables: bool = True,
    ) -> dict:
        """
        Process PDF document using Docling OCR service.

        Args:
            file_content: PDF file content as bytes
            filename: Original filename
            output_format: Output format - "text", "markdown", "html", "doctags"
            do_ocr: Enable OCR for scanned PDFs
            include_tables: Enable table structure recognition

        Returns:
            dict: Response from Docling service with keys:
                - success: bool
                - text/markdown/html/doctags: Content based on output_format
                - metadata: Processing metadata (filename, conversion_time, num_pages, num_tables)
                - error: Error message if success=False

        Raises:
            RuntimeError: If Docling service is not available
            httpx.HTTPError: If HTTP request fails
        """
        if not self.is_available():
            raise RuntimeError(
                "Docling OCR service is not available. "
                "Start the service with: docker compose --profile ocr up -d"
            )

        docling_url = get_docling_ocr_url()
        if not docling_url:
            raise RuntimeError("Could not resolve Docling OCR service URL")

        endpoint = f"{docling_url}/ocr/pdf"

        files = {"file": (filename, file_content, "application/pdf")}
        data = {
            "output_format": output_format,
            "do_ocr": str(do_ocr).lower(),
            "include_tables": str(include_tables).lower(),
        }

        logger.info(
            f"Processing PDF with Docling: {filename} "
            f"(format={output_format}, ocr={do_ocr}, tables={include_tables})"
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(endpoint, files=files, data=data)
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                logger.info(
                    f"Docling processing complete: {filename} "
                    f"({result.get('metadata', {}).get('conversion_time', 'unknown')})"
                )
            else:
                logger.error(
                    f"Docling processing failed: {filename} - {result.get('error', 'Unknown error')}"
                )

            return result

    async def process_image(
        self,
        file_content: bytes,
        filename: str,
        output_format: str = "text",
        include_tables: bool = True,
    ) -> dict:
        """
        Process image document using Docling OCR service.

        Args:
            file_content: Image file content as bytes
            filename: Original filename
            output_format: Output format - "text", "markdown", "html", "doctags"
            include_tables: Enable table structure recognition

        Returns:
            dict: Response from Docling service with same structure as process_pdf

        Raises:
            RuntimeError: If Docling service is not available
            httpx.HTTPError: If HTTP request fails
        """
        if not self.is_available():
            raise RuntimeError(
                "Docling OCR service is not available. "
                "Start the service with: docker compose --profile ocr up -d"
            )

        docling_url = get_docling_ocr_url()
        if not docling_url:
            raise RuntimeError("Could not resolve Docling OCR service URL")

        endpoint = f"{docling_url}/ocr/image"

        # Determine MIME type from filename extension
        ext = filename.lower().split(".")[-1]
        mime_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "tiff": "image/tiff",
            "tif": "image/tiff",
        }
        mime_type = mime_types.get(ext, "image/jpeg")

        files = {"file": (filename, file_content, mime_type)}
        data = {
            "output_format": output_format,
            "include_tables": str(include_tables).lower(),
        }

        logger.info(
            f"Processing image with Docling: {filename} "
            f"(format={output_format}, tables={include_tables})"
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(endpoint, files=files, data=data)
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                logger.info(
                    f"Docling processing complete: {filename} "
                    f"({result.get('metadata', {}).get('conversion_time', 'unknown')})"
                )
            else:
                logger.error(
                    f"Docling processing failed: {filename} - {result.get('error', 'Unknown error')}"
                )

            return result

    async def health_check(self) -> dict:
        """
        Check health status of Docling OCR service.

        Returns:
            dict: Health status information or error dict
        """
        if not self.is_available():
            return {
                "status": "unavailable",
                "message": "Docling OCR service is not configured. Use --profile ocr to start.",
            }

        docling_url = get_docling_ocr_url()
        if not docling_url:
            return {"status": "error", "message": "Could not resolve Docling OCR service URL"}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{docling_url}/health")
                if response.status_code == 200:
                    return response.json()
                return {"status": "unhealthy", "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Docling health check failed: {str(e)}")
            return {"status": "error", "message": str(e)}


# Global instance for convenience
_docling_client: Optional[DoclingServiceClient] = None


def get_docling_client() -> DoclingServiceClient:
    """Get or create the global DoclingServiceClient instance"""
    global _docling_client
    if _docling_client is None:
        _docling_client = DoclingServiceClient()
    return _docling_client
