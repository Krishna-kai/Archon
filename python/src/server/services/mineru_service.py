"""
MinerU OCR Service

Provides PDF extraction capabilities using native MinerU (Magic-PDF) installation.
Handles formula detection, table extraction, and text recognition with high accuracy.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MinerUService:
    """Service for PDF extraction using native MinerU CLI"""

    def __init__(self, mineru_path: Optional[str] = None):
        """
        Initialize the MinerU service.

        Args:
            mineru_path: Path to mineru executable. If None, uses 'mineru' from PATH
        """
        if mineru_path is None:
            # Auto-detect mineru in venv or system PATH
            venv_mineru = Path(__file__).parent.parent.parent.parent / ".venv" / "bin" / "mineru"
            if venv_mineru.exists():
                mineru_path = str(venv_mineru)
            else:
                mineru_path = shutil.which("mineru")

        self.mineru_path = mineru_path
        self.timeout = 300.0  # 5 minutes max for PDF processing

    def is_available(self) -> bool:
        """Check if MinerU is installed and accessible"""
        return self.mineru_path is not None and Path(self.mineru_path).exists()

    async def health_check(self) -> Dict:
        """
        Check MinerU service health.

        Returns:
            Health status dictionary
        """
        if not self.is_available():
            return {
                "status": "unavailable",
                "message": "MinerU is not installed. Run: uv pip install -U 'mineru[core]'",
            }

        try:
            # Test mineru with --version flag
            process = await asyncio.create_subprocess_exec(
                self.mineru_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)

            if process.returncode == 0:
                version_info = stdout.decode().strip() if stdout else "unknown"
                return {
                    "status": "healthy",
                    "service": "mineru",
                    "version": version_info,
                    "path": self.mineru_path,
                }
            else:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                return {
                    "status": "unhealthy",
                    "error": error_msg,
                }

        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Health check timed out",
            }
        except Exception as e:
            logger.error(f"MinerU health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }

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
        Process PDF document using MinerU for formula and table extraction.

        Args:
            file_content: PDF file content as bytes
            filename: Original filename
            device: Processing device - "mps" (Apple Silicon), "cuda", "cpu"
            lang: Document language - "en", "zh", etc.
            extract_charts: Whether to extract chart data from images
            chart_provider: Chart extraction provider - "auto", "local", "claude"

        Returns:
            Tuple of (success: bool, result: dict)
            Result dict contains:
                - success: bool
                - markdown: Full markdown text with formulas
                - metadata: Processing metadata (filename, processing_time, formulas, tables, charts)
                - charts: List of extracted chart data (if extract_charts=True)
                - error: Error message if success=False
        """
        if not self.is_available():
            return False, {
                "error": "MinerU is not installed. Install with: uv pip install -U 'mineru[core]'",
            }

        temp_dir = None
        temp_pdf = None

        try:
            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="mineru_")
            temp_pdf = Path(temp_dir) / filename
            output_dir = Path(temp_dir) / "output"

            # Write PDF to temporary file
            temp_pdf.write_bytes(file_content)

            logger.info(
                f"Processing PDF with MinerU: {filename} "
                f"(size={len(file_content)} bytes, device={device}, lang={lang})"
            )

            # Execute MinerU CLI
            process = await asyncio.create_subprocess_exec(
                self.mineru_path,
                "-p",
                str(temp_pdf),
                "-o",
                str(output_dir),
                "--device",
                device,
                "--lang",
                lang,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                error_msg = f"MinerU processing timed out after {self.timeout}s"
                logger.error(f"{error_msg} for {filename}")
                return False, {"error": error_msg}

            # Check process exit code
            if process.returncode != 0:
                error_msg = f"MinerU failed with exit code {process.returncode}"
                stderr_text = stderr.decode() if stderr else ""
                logger.error(f"{error_msg} for {filename}: {stderr_text}")
                return False, {"error": error_msg, "stderr": stderr_text}

            # Parse MinerU output
            result = self._parse_mineru_output(output_dir, filename)

            if result["success"]:
                logger.info(
                    f"MinerU processing complete: {filename} "
                    f"(formulas={result['metadata'].get('formulas_count', 0)}, "
                    f"tables={result['metadata'].get('tables_count', 0)})"
                )

                # Extract charts from images if requested
                if extract_charts:
                    charts_data = await self._extract_charts_from_images(
                        output_dir, filename, chart_provider
                    )
                    result["charts"] = charts_data
                    result["metadata"]["charts_count"] = len(charts_data)
                    logger.info(
                        f"Chart extraction complete: {filename} "
                        f"(charts={len(charts_data)})"
                    )
            else:
                logger.error(f"MinerU output parsing failed for {filename}")

            return result["success"], result

        except Exception as e:
            error_msg = f"MinerU processing failed: {str(e)}"
            logger.error(f"{error_msg} for {filename}", exc_info=True)
            return False, {"error": error_msg}

        finally:
            # Cleanup temporary files
            if temp_dir and Path(temp_dir).exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

    async def _extract_charts_from_images(
        self, output_dir: Path, original_filename: str, chart_provider: str
    ) -> list:
        """
        Extract chart data from images in MinerU output directory.

        Args:
            output_dir: Directory containing MinerU output
            original_filename: Original PDF filename
            chart_provider: Chart extraction provider ("auto", "local", "claude")

        Returns:
            List of chart extraction results
        """
        charts_data = []

        try:
            # MinerU creates: <pdf_name>/auto/images/
            pdf_name = Path(original_filename).stem
            images_dir = output_dir / pdf_name / "auto" / "images"

            if not images_dir.exists():
                # Try alternative structure
                images_dir = output_dir / "auto" / "images"

            if not images_dir.exists():
                logger.info(f"No images directory found for chart extraction: {images_dir}")
                return []

            # Find all image files
            image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))

            if not image_files:
                logger.info(f"No image files found for chart extraction in {images_dir}")
                return []

            logger.info(f"Found {len(image_files)} images for chart extraction")

            # Import chart extraction service
            from .chart_extraction_service import ChartProvider, get_chart_extraction_service

            # Map provider string to enum
            provider_map = {
                "auto": ChartProvider.AUTO,
                "local": ChartProvider.LOCAL,
                "claude": ChartProvider.CLAUDE,
                "openai": ChartProvider.OPENAI,
                "gemini": ChartProvider.GEMINI,
            }
            provider_enum = provider_map.get(chart_provider.lower(), ChartProvider.AUTO)

            chart_service = get_chart_extraction_service()

            # Extract charts from each image
            for i, image_file in enumerate(image_files, 1):
                try:
                    logger.info(f"Extracting chart from image {i}/{len(image_files)}: {image_file.name}")

                    # Read image bytes
                    image_bytes = image_file.read_bytes()

                    # Extract chart data
                    success, result = await chart_service.extract_chart_data(
                        image_content=image_bytes,
                        chart_type=None,  # Let the service auto-detect
                        context=f"Image from {original_filename}",
                        provider=provider_enum,
                    )

                    if success:
                        charts_data.append({
                            "image_filename": image_file.name,
                            "success": True,
                            "data": result,
                        })
                        logger.info(f"Successfully extracted chart from {image_file.name}")
                    else:
                        logger.warning(f"Failed to extract chart from {image_file.name}: {result.get('error')}")
                        charts_data.append({
                            "image_filename": image_file.name,
                            "success": False,
                            "error": result.get("error", "Unknown error"),
                        })

                except Exception as e:
                    logger.error(f"Error extracting chart from {image_file.name}: {str(e)}", exc_info=True)
                    charts_data.append({
                        "image_filename": image_file.name,
                        "success": False,
                        "error": str(e),
                    })

            logger.info(f"Chart extraction complete: {len(charts_data)} images processed")

        except Exception as e:
            logger.error(f"Chart extraction failed: {str(e)}", exc_info=True)

        return charts_data

    def _parse_mineru_output(self, output_dir: Path, original_filename: str) -> Dict:
        """
        Parse MinerU output files to extract markdown and metadata.

        Args:
            output_dir: Directory containing MinerU output
            original_filename: Original PDF filename

        Returns:
            Dictionary with success, markdown, metadata, and error fields
        """
        try:
            # MinerU creates: <pdf_name>/auto/<pdf_name>.md and <pdf_name>_content_list.json
            pdf_name = Path(original_filename).stem
            auto_dir = output_dir / pdf_name / "auto"

            if not auto_dir.exists():
                # Try alternative structure (some versions)
                auto_dir = output_dir / "auto"

            if not auto_dir.exists():
                return {
                    "success": False,
                    "error": f"MinerU output directory not found: {auto_dir}",
                }

            # Find markdown file
            md_files = list(auto_dir.glob("*.md"))
            if not md_files:
                return {
                    "success": False,
                    "error": "No markdown file found in MinerU output",
                }

            markdown_file = md_files[0]
            markdown_text = markdown_file.read_text(encoding="utf-8")

            # Find metadata JSON (content_list.json)
            json_files = list(auto_dir.glob("*_content_list.json"))
            metadata = {"filename": original_filename}

            if json_files:
                try:
                    content_list = json.loads(json_files[0].read_text(encoding="utf-8"))

                    # Count formulas and tables from content list
                    formulas_count = 0
                    tables_count = 0

                    for page in content_list:
                        if isinstance(page, dict):
                            # Count inline and display formulas
                            inline_formulas = page.get("preproc_blocks", [])
                            formulas_count += sum(
                                1
                                for block in inline_formulas
                                if block.get("type") in ["inline_equation", "interline_equation"]
                            )

                            # Count tables
                            layout_blocks = page.get("layout_dets", [])
                            tables_count += sum(
                                1 for block in layout_blocks if block.get("category_id") == 5
                            )

                    metadata.update(
                        {
                            "formulas_count": formulas_count,
                            "tables_count": tables_count,
                            "pages": len(content_list),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Failed to parse content_list.json: {e}")

            # Count formulas from markdown (fallback/verification)
            inline_formulas = markdown_text.count("$") // 2  # Pairs of $...$
            display_formulas = markdown_text.count("$$") // 2  # Pairs of $$...$$

            if "formulas_count" not in metadata:
                metadata["formulas_count"] = inline_formulas + display_formulas

            metadata["inline_formulas"] = inline_formulas
            metadata["display_formulas"] = display_formulas
            metadata["markdown_length"] = len(markdown_text)

            return {
                "success": True,
                "markdown": markdown_text,
                "metadata": metadata,
                "backend": "mineru",
            }

        except Exception as e:
            logger.error(f"Failed to parse MinerU output: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Output parsing failed: {str(e)}",
            }


# Singleton instance for local CLI service
_mineru_service_instance: Optional[MinerUService] = None


def get_mineru_service() -> Union[MinerUService, "MinerUHttpClient"]:
    """
    Get MinerU service instance based on configuration.

    Returns HTTP client if MINERU_SERVICE_URL is set, otherwise returns
    local CLI service. This enables Docker containers to use native Mac
    service with Apple GPU acceleration when available.

    Returns:
        MinerUHttpClient if MINERU_SERVICE_URL env var is set,
        MinerUService (local CLI) otherwise
    """
    mineru_url = os.getenv("MINERU_SERVICE_URL")

    if mineru_url:
        from .mineru_http_client import MinerUHttpClient
        logger.info(f"Using MinerU HTTP client: {mineru_url}")
        return MinerUHttpClient(mineru_url)
    else:
        global _mineru_service_instance
        if _mineru_service_instance is None:
            _mineru_service_instance = MinerUService()
        logger.info("Using MinerU local CLI service")
        return _mineru_service_instance
