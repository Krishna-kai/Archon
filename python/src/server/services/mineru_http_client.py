"""
MinerU HTTP Client for Native Service Integration

This client calls the native MinerU service running on the host machine,
enabling Docker containers to leverage Apple Silicon GPU acceleration for PDF processing.
"""

import base64
import logging
from typing import Dict, List, Tuple

import httpx

logger = logging.getLogger(__name__)


class MinerUHttpClient:
    """
    HTTP client for native MinerU service.

    Provides the same interface as MinerUService but calls the HTTP service
    instead of executing the CLI locally. This allows Docker containers to
    use the native Mac service with Apple GPU acceleration.
    """

    def __init__(self, service_url: str):
        """
        Initialize HTTP client.

        Args:
            service_url: Base URL of MinerU service (e.g., "http://host.docker.internal:8055")
        """
        self.service_url = service_url.rstrip('/')
        self.timeout = 300.0  # 5 minutes for large PDFs

    def is_available(self) -> bool:
        """
        Check if MinerU HTTP service is accessible.

        Returns:
            True if service responds to health check, False otherwise
        """
        try:
            response = httpx.get(f"{self.service_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MinerU service unavailable at {self.service_url}: {e}")
            return False

    async def process_pdf(
        self,
        file_content: bytes,
        filename: str,
        device: str = "mps",
        lang: str = "en",
        extract_charts: bool = False,
        chart_provider: str = "auto",
    ) -> Tuple[bool, Dict]:
        """
        Process PDF using native MinerU service via HTTP.

        Args:
            file_content: Raw PDF file bytes
            filename: Original filename
            device: Device to use (e.g., "mps", "cpu")
            lang: Language code (e.g., "en", "zh")
            extract_charts: Whether to extract charts from PDF
            chart_provider: Chart extraction provider ("auto", "deepseek", etc.)

        Returns:
            Tuple of (success: bool, result: dict)
            Result dict contains:
                - success: bool
                - markdown: str (extracted text)
                - metadata: dict
                - charts: list[dict] - Image data with base64 encoding
                    Each image dict contains:
                        - name: str (filename)
                        - base64: str (base64-encoded image data)
                        - page_number: int | None (PDF page, 1-indexed)
                        - image_index: int (order within page, 0-indexed)
                        - mime_type: str (e.g., "image/jpeg")
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare multipart form data
                files = {"file": (filename, file_content, "application/pdf")}
                data = {
                    "device": device,
                    "lang": lang,
                    "extract_charts": str(extract_charts).lower(),
                    "chart_provider": chart_provider,
                }

                logger.info(
                    f"Sending PDF to MinerU service: {filename} "
                    f"(device={device}, extract_charts={extract_charts})"
                )

                # Call native service
                response = await client.post(
                    f"{self.service_url}/process",
                    files=files,
                    data=data
                )
                response.raise_for_status()

                result = response.json()

                # Extract image data
                images = result.get("images", [])
                image_count = len(images)

                logger.info(
                    f"MinerU processed {filename}: "
                    f"{len(result.get('text', ''))} chars text, "
                    f"{image_count} images extracted"
                )

                # Transform response to match MinerUService format
                # Note: "charts" key maintained for backward compatibility
                # but now contains structured ImageData objects with base64
                return True, {
                    "success": result.get("success", True),
                    "markdown": result.get("text", ""),
                    "metadata": result.get("metadata", {}),
                    "charts": images,
                }

        except httpx.TimeoutException as e:
            logger.error(f"MinerU service timeout processing {filename}: {e}")
            return False, {
                "error": f"Service timeout after {self.timeout}s",
                "details": str(e)
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"MinerU service HTTP error processing {filename}: {e}")
            return False, {
                "error": f"HTTP {e.response.status_code}",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"MinerU service failed processing {filename}: {e}", exc_info=True)
            return False, {
                "error": "Service call failed",
                "details": str(e)
            }
