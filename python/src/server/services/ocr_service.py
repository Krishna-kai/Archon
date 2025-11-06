"""
OCR Service

This module provides OCR capabilities using the DeepSeek OCR service.
Handles communication with the DeepSeek OCR microservice for document image recognition.
"""

import httpx
from typing import Optional

from ..config.logfire_config import get_logger, safe_logfire_error, safe_logfire_info

logger = get_logger(__name__)

# DeepSeek OCR service configuration
import os

# Auto-detect environment and set appropriate URL
# In Docker Compose, SERVICE_DISCOVERY_MODE=docker_compose is set
SERVICE_DISCOVERY_MODE = os.getenv("SERVICE_DISCOVERY_MODE", "local")

if SERVICE_DISCOVERY_MODE == "docker_compose":
    DEEPSEEK_OCR_URL = "http://deepseek-ocr:9001"  # Docker container name
    DEEPSEEK_OCR_MLX_URL = "http://deepseek-ocr-mlx:9005"  # Docker container name
else:
    DEEPSEEK_OCR_URL = "http://localhost:9001"  # Local development
    DEEPSEEK_OCR_MLX_URL = os.getenv("DEEPSEEK_OCR_MLX_URL", "http://localhost:9005")  # MLX service (native Mac)


class OCRService:
    """Service for performing OCR on images and PDFs using DeepSeek OCR."""

    def __init__(self, service_url: str = DEEPSEEK_OCR_URL):
        """
        Initialize the OCR service.

        Args:
            service_url: URL of the DeepSeek OCR service
        """
        self.service_url = service_url.rstrip("/")
        self.timeout = 120.0  # OCR can take time, especially on CPU

    async def check_health(self) -> dict:
        """
        Check if the OCR service is healthy and available.

        Returns:
            Health status dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.service_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            safe_logfire_error(f"OCR service health check failed | error={str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "deepseek-ocr"
            }

    async def ocr_image(
        self,
        file_content: bytes,
        filename: str,
        prompt: str = "<image>\n<|grounding|>Convert the document to markdown.",
        output_format: str = "markdown"
    ) -> tuple[bool, dict]:
        """
        Perform OCR on an image file.

        Args:
            file_content: Raw image bytes
            filename: Name of the file (for logging)
            prompt: OCR prompt to guide extraction
            output_format: Output format (markdown or text)

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            safe_logfire_info(
                f"Starting OCR on image | filename={filename} | size={len(file_content)} bytes"
            )

            # Prepare multipart form data
            files = {
                'file': (filename, file_content, 'image/jpeg')
            }
            data = {
                'prompt': prompt,
                'output_format': output_format
            }

            # Call OCR service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/ocr/image",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                result = response.json()

            if result.get('success'):
                extracted_text = result.get('markdown') or result.get('text', '')
                metadata = result.get('metadata', {})

                safe_logfire_info(
                    f"OCR completed successfully | filename={filename} | "
                    f"extracted_length={len(extracted_text)} | "
                    f"processing_time={metadata.get('processing_time')}"
                )

                return True, {
                    'text': extracted_text,
                    'metadata': metadata,
                    'backend': result.get('backend')
                }
            else:
                error_msg = result.get('error', 'OCR failed')
                safe_logfire_error(f"OCR failed | filename={filename} | error={error_msg}")
                return False, {'error': error_msg}

        except httpx.TimeoutException:
            error_msg = f"OCR timeout after {self.timeout}s - document may be too large or complex"
            safe_logfire_error(f"OCR timeout | filename={filename}")
            return False, {'error': error_msg}

        except httpx.HTTPStatusError as e:
            error_msg = f"OCR service error: {e.response.status_code}"
            safe_logfire_error(
                f"OCR HTTP error | filename={filename} | status={e.response.status_code}"
            )
            return False, {'error': error_msg}

        except Exception as e:
            error_msg = f"OCR failed: {str(e)}"
            safe_logfire_error(f"OCR exception | filename={filename} | error={str(e)}")
            return False, {'error': error_msg}

    async def ocr_pdf(
        self,
        file_content: bytes,
        filename: str,
        prompt: str = "<image>\n<|grounding|>Convert the document to markdown."
    ) -> tuple[bool, dict]:
        """
        Perform OCR on a PDF file.

        Args:
            file_content: Raw PDF bytes
            filename: Name of the file (for logging)
            prompt: OCR prompt to guide extraction

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            safe_logfire_info(
                f"Starting OCR on PDF | filename={filename} | size={len(file_content)} bytes"
            )

            # Prepare multipart form data
            files = {
                'file': (filename, file_content, 'application/pdf')
            }
            data = {
                'prompt': prompt,
                'output_format': 'markdown'
            }

            # Call OCR service
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:  # Longer timeout for PDFs
                response = await client.post(
                    f"{self.service_url}/ocr/pdf",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                result = response.json()

            if result.get('success'):
                extracted_text = result.get('markdown') or result.get('text', '')
                metadata = result.get('metadata', {})

                safe_logfire_info(
                    f"PDF OCR completed successfully | filename={filename} | "
                    f"extracted_length={len(extracted_text)} | "
                    f"processing_time={metadata.get('processing_time')}"
                )

                return True, {
                    'text': extracted_text,
                    'metadata': metadata,
                    'backend': result.get('backend')
                }
            else:
                error_msg = result.get('error', 'PDF OCR failed')
                safe_logfire_error(f"PDF OCR failed | filename={filename} | error={error_msg}")
                return False, {'error': error_msg}

        except Exception as e:
            error_msg = f"PDF OCR failed: {str(e)}"
            safe_logfire_error(f"PDF OCR exception | filename={filename} | error={str(e)}")
            return False, {'error': error_msg}


class DeepSeekOCRMLXService:
    """Service for performing OCR using DeepSeek-OCR MLX (Apple Silicon optimized)."""

    def __init__(self, service_url: str = DEEPSEEK_OCR_MLX_URL):
        """
        Initialize the MLX OCR service.

        Args:
            service_url: URL of the DeepSeek-OCR MLX service
        """
        self.service_url = service_url.rstrip("/")
        self.timeout = 120.0  # OCR can take time

    async def check_health(self) -> dict:
        """
        Check if the MLX OCR service is healthy and available.

        Returns:
            Health status dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.service_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            safe_logfire_error(f"DeepSeek-OCR MLX service health check failed | error={str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "deepseek-ocr-mlx"
            }

    async def ocr_image(
        self,
        file_content: bytes,
        filename: str,
        mode: str = "markdown",
        custom_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.0
    ) -> tuple[bool, dict]:
        """
        Perform OCR on an image file using MLX.

        Args:
            file_content: Raw image bytes
            filename: Name of the file (for logging)
            mode: OCR mode (markdown, plain, figure, table, formula, custom)
            custom_prompt: Custom prompt (if mode=custom)
            max_tokens: Maximum output tokens
            temperature: Generation temperature

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            safe_logfire_info(
                f"Starting MLX OCR on image | filename={filename} | mode={mode} | size={len(file_content)} bytes"
            )

            # Prepare multipart form data
            files = {
                'file': (filename, file_content, 'image/jpeg')
            }
            data = {
                'mode': mode,
                'max_tokens': str(max_tokens),
                'temperature': str(temperature)
            }
            if custom_prompt:
                data['custom_prompt'] = custom_prompt

            # Call MLX OCR service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/ocr/",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                result = response.json()

            if result.get('success'):
                extracted_text = result.get('result') or result.get('markdown') or result.get('text', '')
                metadata = result.get('metadata', {})

                safe_logfire_info(
                    f"MLX OCR completed successfully | filename={filename} | "
                    f"extracted_length={len(extracted_text)} | "
                    f"processing_time={metadata.get('processing_time')}"
                )

                return True, {
                    'text': extracted_text,
                    'metadata': metadata,
                    'backend': 'MLX (Apple Metal)'
                }
            else:
                error_msg = result.get('error', 'MLX OCR failed')
                safe_logfire_error(f"MLX OCR failed | filename={filename} | error={error_msg}")
                return False, {'error': error_msg}

        except httpx.TimeoutException:
            error_msg = f"MLX OCR timeout after {self.timeout}s"
            safe_logfire_error(f"MLX OCR timeout | filename={filename}")
            return False, {'error': error_msg}

        except httpx.HTTPStatusError as e:
            error_msg = f"MLX OCR service error: {e.response.status_code}"
            safe_logfire_error(
                f"MLX OCR HTTP error | filename={filename} | status={e.response.status_code}"
            )
            return False, {'error': error_msg}

        except Exception as e:
            error_msg = f"MLX OCR failed: {str(e)}"
            safe_logfire_error(f"MLX OCR exception | filename={filename} | error={str(e)}")
            return False, {'error': error_msg}


# Singleton instances for reuse
_ocr_service_instance: Optional[OCRService] = None
_ocr_mlx_service_instance: Optional[DeepSeekOCRMLXService] = None


def get_ocr_service() -> OCRService:
    """
    Get or create the singleton OCR service instance.

    Returns:
        OCRService instance
    """
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = OCRService()
    return _ocr_service_instance


def get_ocr_mlx_service() -> DeepSeekOCRMLXService:
    """
    Get or create the singleton MLX OCR service instance.

    Returns:
        DeepSeekOCRMLXService instance
    """
    global _ocr_mlx_service_instance
    if _ocr_mlx_service_instance is None:
        _ocr_mlx_service_instance = DeepSeekOCRMLXService()
    return _ocr_mlx_service_instance
