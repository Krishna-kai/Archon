"""
Docling OCR Module for Archon MCP Server

This module provides tools for:
- PDF OCR processing
- Image OCR processing
- Service health checking

This uses the Docling service client for HTTP communication.
"""

import base64
import json
import logging
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

# Import Docling service client
from src.server.services.docling_service import get_docling_client

logger = logging.getLogger(__name__)


def register_docling_tools(mcp: FastMCP):
    """Register all Docling tools with the MCP server."""

    @mcp.tool()
    async def docling_process_pdf(
        ctx: Context,
        file_path: str,
        output_format: str = "text",
        do_ocr: bool = False,
        include_tables: bool = True,
    ) -> str:
        """
        Process a PDF document using Docling OCR service.

        IMPORTANT: Docling is optimized for scanned documents and complex layouts.
        For text-based PDFs, PyMuPDF is 19,000x faster. Only use Docling for:
        - Scanned documents requiring OCR
        - Complex layouts with tables
        - Markdown generation with structure preservation

        Args:
            file_path: Absolute path to PDF file
            output_format: Output format - "text", "markdown", "html", "doctags" (default: "text")
            do_ocr: Enable OCR for scanned PDFs (default: False)
            include_tables: Enable table structure recognition (default: True)

        Returns:
            JSON string with structure:
            - success: bool - Operation success status
            - content: str - Extracted content in requested format
            - metadata: dict - Processing metadata (filename, conversion_time, num_pages, num_tables)
            - error: str - Error description if success=False

        Example:
            docling_process_pdf(
                file_path="/path/to/scanned_document.pdf",
                output_format="markdown",
                do_ocr=True,
                include_tables=True
            )
        """
        try:
            docling = get_docling_client()

            # Check if service is available
            if not docling.is_available():
                return json.dumps(
                    {
                        "success": False,
                        "error": "Docling OCR service is not available. "
                        "Start with: docker compose --profile ocr up -d",
                    },
                    indent=2,
                )

            # Read file
            path = Path(file_path)
            if not path.exists():
                return json.dumps(
                    {"success": False, "error": f"File not found: {file_path}"}, indent=2
                )

            if not path.is_file():
                return json.dumps(
                    {"success": False, "error": f"Path is not a file: {file_path}"}, indent=2
                )

            # Read file content
            with open(path, "rb") as f:
                file_content = f.read()

            # Process with Docling
            result = await docling.process_pdf(
                file_content=file_content,
                filename=path.name,
                output_format=output_format,
                do_ocr=do_ocr,
                include_tables=include_tables,
            )

            # Extract content based on format
            content_key = output_format  # "text", "markdown", "html", or "doctags"
            content = result.get(content_key, "")

            return json.dumps(
                {
                    "success": result.get("success", False),
                    "content": content,
                    "metadata": result.get("metadata", {}),
                    "error": result.get("error"),
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error processing PDF with Docling: {e}")
            return json.dumps({"success": False, "error": str(e)}, indent=2)

    @mcp.tool()
    async def docling_process_image(
        ctx: Context,
        file_path: str,
        output_format: str = "text",
        include_tables: bool = True,
    ) -> str:
        """
        Process an image document using Docling OCR service.

        Docling supports: PNG, JPG, JPEG, TIFF

        Args:
            file_path: Absolute path to image file
            output_format: Output format - "text", "markdown", "html", "doctags" (default: "text")
            include_tables: Enable table structure recognition (default: True)

        Returns:
            JSON string with structure:
            - success: bool - Operation success status
            - content: str - Extracted content in requested format
            - metadata: dict - Processing metadata (filename, conversion_time, num_pages, num_tables)
            - error: str - Error description if success=False

        Example:
            docling_process_image(
                file_path="/path/to/scanned_page.png",
                output_format="markdown",
                include_tables=True
            )
        """
        try:
            docling = get_docling_client()

            # Check if service is available
            if not docling.is_available():
                return json.dumps(
                    {
                        "success": False,
                        "error": "Docling OCR service is not available. "
                        "Start with: docker compose --profile ocr up -d",
                    },
                    indent=2,
                )

            # Read file
            path = Path(file_path)
            if not path.exists():
                return json.dumps(
                    {"success": False, "error": f"File not found: {file_path}"}, indent=2
                )

            if not path.is_file():
                return json.dumps(
                    {"success": False, "error": f"Path is not a file: {file_path}"}, indent=2
                )

            # Read file content
            with open(path, "rb") as f:
                file_content = f.read()

            # Process with Docling
            result = await docling.process_image(
                file_content=file_content,
                filename=path.name,
                output_format=output_format,
                include_tables=include_tables,
            )

            # Extract content based on format
            content_key = output_format  # "text", "markdown", "html", or "doctags"
            content = result.get(content_key, "")

            return json.dumps(
                {
                    "success": result.get("success", False),
                    "content": content,
                    "metadata": result.get("metadata", {}),
                    "error": result.get("error"),
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error processing image with Docling: {e}")
            return json.dumps({"success": False, "error": str(e)}, indent=2)

    @mcp.tool()
    async def docling_health(ctx: Context) -> str:
        """
        Check health status of Docling OCR service.

        Returns:
            JSON string with structure:
            - status: str - "healthy", "unhealthy", "unavailable", or "error"
            - message: str - Additional status information
            - service: str - Service name
            - converter_loaded: bool - Whether converter is loaded (if healthy)

        Example:
            docling_health()
        """
        try:
            docling = get_docling_client()
            result = await docling.health_check()

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error checking Docling health: {e}")
            return json.dumps({"status": "error", "message": str(e)}, indent=2)
