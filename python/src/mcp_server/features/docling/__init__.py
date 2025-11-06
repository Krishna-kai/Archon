"""
Docling OCR tools for Archon MCP Server.

This module provides tools for document OCR operations:
- docling_process_pdf: Process PDF documents with Docling OCR
- docling_process_image: Process image documents with Docling OCR
- docling_health: Check Docling service availability
"""

from .docling_tools import register_docling_tools

__all__ = ["register_docling_tools"]
