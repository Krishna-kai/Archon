"""
Chart Extraction Service (Hybrid Local + Cloud)

Provides chart and graph extraction capabilities using:
- LOCAL: Ollama vision models (llama3.2-vision, llava) - Free, private
- CLOUD: Claude 3.5 Sonnet Vision API - Paid, high accuracy

Follows local-first pattern: tries Ollama first, falls back to cloud if needed.
"""

import asyncio
import base64
import json
import logging
import os
import shutil
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class ChartType(str, Enum):
    """Supported chart types"""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    BOX_PLOT = "box_plot"
    HISTOGRAM = "histogram"
    AREA = "area"
    MULTI_PANEL = "multi_panel"
    UNKNOWN = "unknown"


class ChartProvider(str, Enum):
    """Chart extraction provider options"""

    AUTO = "auto"  # Try local first, fallback to cloud
    LOCAL = "local"  # Ollama only
    CLAUDE = "claude"  # Anthropic only
    OPENAI = "openai"  # OpenAI only (future)
    GEMINI = "gemini"  # Google only (future)


class ChartExtractionService:
    """Service for extracting structured data from charts using vision models"""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize the chart extraction service.

        Args:
            anthropic_api_key: Anthropic API key. If None, will use credentials service
        """
        self.anthropic_api_key = anthropic_api_key

        # Cloud model configuration
        self.claude_model = "claude-3-5-sonnet-20241022"
        self.max_image_size_mb = 5  # Claude Vision limit

        # Local model configuration
        self.ollama_model = "llama3.2-vision:11b"  # Default local model
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # Timeout settings
        self.cloud_timeout = 60.0  # 1 minute for cloud APIs
        self.local_timeout = 120.0  # 2 minutes for local models (can be slower)

    def is_available(self, provider: ChartProvider = ChartProvider.AUTO) -> bool:
        """
        Check if chart extraction service is available

        Args:
            provider: Which provider to check availability for
        """
        if provider == ChartProvider.LOCAL:
            return self._is_ollama_available()
        elif provider == ChartProvider.CLAUDE:
            return self._is_anthropic_available()
        elif provider == ChartProvider.AUTO:
            return self._is_ollama_available() or self._is_anthropic_available()
        else:
            return False

    def _is_ollama_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            import requests

            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                # Check if vision model is installed
                tags = response.json().get("models", [])
                for model in tags:
                    if "vision" in model.get("name", "").lower():
                        return True
                logger.warning("Ollama available but no vision models installed")
                return False
            return False
        except Exception:
            return False

    def _is_anthropic_available(self) -> bool:
        """Check if Anthropic SDK is available"""
        try:
            import anthropic

            return True
        except ImportError:
            return False

    async def health_check(self, provider: ChartProvider = ChartProvider.AUTO) -> Dict:
        """
        Check chart extraction service health.

        Args:
            provider: Which provider to check

        Returns:
            Health status dictionary
        """
        if provider == ChartProvider.AUTO:
            # Check both local and cloud
            local_health = await self._health_check_ollama()
            cloud_health = await self._health_check_claude()

            return {
                "status": "healthy"
                if local_health["status"] == "healthy" or cloud_health["status"] == "healthy"
                else "unavailable",
                "local": local_health,
                "cloud": cloud_health,
                "default": "local"
                if local_health["status"] == "healthy"
                else "cloud"
                if cloud_health["status"] == "healthy"
                else "none",
            }
        elif provider == ChartProvider.LOCAL:
            return await self._health_check_ollama()
        elif provider == ChartProvider.CLAUDE:
            return await self._health_check_claude()
        else:
            return {"status": "unavailable", "error": f"Unknown provider: {provider}"}

    async def _health_check_ollama(self) -> Dict:
        """Check Ollama health"""
        if not self._is_ollama_available():
            return {
                "status": "unavailable",
                "message": "Ollama not available or no vision models installed",
            }

        try:
            import requests

            # Test Ollama API
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                vision_models = [m for m in models if "vision" in m.get("name", "").lower()]

                return {
                    "status": "healthy",
                    "service": "ollama",
                    "models": [m["name"] for m in vision_models],
                    "base_url": self.ollama_base_url,
                }

            return {"status": "unhealthy", "error": "Ollama API returned non-200 status"}

        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _health_check_claude(self) -> Dict:
        """Check Claude Vision API health"""
        if not self._is_anthropic_available():
            return {
                "status": "unavailable",
                "message": "Anthropic SDK is not installed. Run: uv pip install anthropic",
            }

        try:
            # Get API key from credentials service if not provided
            if not self.anthropic_api_key:
                from .credential_service import credential_service

                provider_config = await credential_service.get_provider_config("anthropic")
                if not provider_config or not provider_config.get("api_key"):
                    return {
                        "status": "unavailable",
                        "message": "Anthropic API key not configured",
                    }
                self.anthropic_api_key = provider_config["api_key"]

            # Test API connection with simple request
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)

            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.claude_model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Test"}],
                ),
                timeout=5.0,
            )

            return {
                "status": "healthy",
                "service": "claude_vision",
                "model": self.claude_model,
            }

        except asyncio.TimeoutError:
            return {"status": "unhealthy", "error": "Health check timed out"}
        except Exception as e:
            logger.error(f"Claude health check failed: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def extract_chart_data(
        self,
        image_content: bytes,
        chart_type: Optional[ChartType] = None,
        context: Optional[str] = None,
        provider: ChartProvider = ChartProvider.AUTO,
    ) -> Tuple[bool, Dict]:
        """
        Extract structured data from a chart image using vision models.

        Args:
            image_content: Raw image bytes (PNG, JPEG, etc.)
            chart_type: Optional hint about chart type
            context: Optional context about the chart
            provider: Which provider to use (auto|local|claude|openai|gemini)

        Returns:
            Tuple of (success: bool, result: Dict)
            Result contains:
            - chart_type: Detected chart type
            - title: Chart title
            - data: Structured data extracted from chart
            - labels: Axis labels and legend
            - description: Natural language description
            - confidence: Confidence score (0-1)
            - provider_used: Which provider was used
        """
        if provider == ChartProvider.AUTO:
            # Try local first, fallback to cloud
            logger.info("Using AUTO provider: trying local first")

            if self._is_ollama_available():
                logger.info("Attempting local extraction with Ollama...")
                success, result = await self._extract_with_ollama(
                    image_content, chart_type, context
                )
                if success:
                    result["provider_used"] = "ollama"
                    return True, result
                else:
                    logger.warning(
                        f"Local extraction failed: {result.get('error')}, falling back to cloud"
                    )

            # Fallback to cloud
            if self._is_anthropic_available():
                logger.info("Falling back to Claude Vision...")
                success, result = await self._extract_with_claude(
                    image_content, chart_type, context
                )
                if success:
                    result["provider_used"] = "claude"
                return success, result
            else:
                return False, {
                    "error": "No providers available (Ollama failed, Claude not configured)"
                }

        elif provider == ChartProvider.LOCAL:
            # Local only
            success, result = await self._extract_with_ollama(image_content, chart_type, context)
            if success:
                result["provider_used"] = "ollama"
            return success, result

        elif provider == ChartProvider.CLAUDE:
            # Cloud only
            success, result = await self._extract_with_claude(image_content, chart_type, context)
            if success:
                result["provider_used"] = "claude"
            return success, result

        else:
            return False, {"error": f"Unsupported provider: {provider}"}

    async def _extract_with_ollama(
        self,
        image_content: bytes,
        chart_type: Optional[ChartType] = None,
        context: Optional[str] = None,
    ) -> Tuple[bool, Dict]:
        """Extract chart data using Ollama vision model (local)"""
        try:
            import requests

            # Encode image to base64
            image_base64 = base64.b64encode(image_content).decode("utf-8")

            # Build prompt
            prompt = self._build_extraction_prompt(chart_type, context)

            # Call Ollama API
            logger.info(f"Extracting chart with Ollama ({self.ollama_model})...")

            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=self.local_timeout,
            )

            if response.status_code != 200:
                return False, {
                    "error": f"Ollama API error: {response.status_code} - {response.text}"
                }

            result_data = response.json()
            response_text = result_data.get("response", "")

            # Parse response
            result = self._parse_vision_response_text(response_text)

            logger.info(
                f"Ollama extraction complete: type={result.get('chart_type')}, "
                f"confidence={result.get('confidence', 0):.2f}"
            )

            return True, result

        except requests.Timeout:
            logger.error(f"Ollama extraction timed out after {self.local_timeout}s")
            return False, {"error": "Ollama extraction timeout"}
        except Exception as e:
            logger.error(f"Ollama extraction failed: {str(e)}", exc_info=True)
            return False, {"error": str(e)}

    async def _extract_with_claude(
        self,
        image_content: bytes,
        chart_type: Optional[ChartType] = None,
        context: Optional[str] = None,
    ) -> Tuple[bool, Dict]:
        """Extract chart data using Claude Vision API (cloud)"""
        try:
            # Get API key from credentials if not set
            if not self.anthropic_api_key:
                from .credential_service import credential_service

                provider_config = await credential_service.get_provider_config("anthropic")
                if not provider_config or not provider_config.get("api_key"):
                    return False, {"error": "Anthropic API key not configured"}
                self.anthropic_api_key = provider_config["api_key"]

            # Validate image size
            image_size_mb = len(image_content) / (1024 * 1024)
            if image_size_mb > self.max_image_size_mb:
                logger.warning(
                    f"Image size {image_size_mb:.2f}MB exceeds limit {self.max_image_size_mb}MB, "
                    f"compressing..."
                )
                image_content = await self._compress_image(image_content)

            # Encode image to base64
            image_base64 = base64.b64encode(image_content).decode("utf-8")

            # Detect media type
            media_type = self._detect_media_type(image_content)

            # Build prompt
            prompt = self._build_extraction_prompt(chart_type, context)

            # Call Claude Vision API
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)

            logger.info(f"Extracting chart with Claude Vision ({self.claude_model})...")

            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.claude_model,
                    max_tokens=2048,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_base64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                ),
                timeout=self.cloud_timeout,
            )

            # Parse response
            result = self._parse_claude_response(response)

            logger.info(
                f"Claude extraction complete: type={result.get('chart_type')}, "
                f"confidence={result.get('confidence', 0):.2f}"
            )

            return True, result

        except asyncio.TimeoutError:
            logger.error(f"Claude extraction timed out after {self.cloud_timeout}s")
            return False, {"error": "Claude extraction timeout"}
        except Exception as e:
            logger.error(f"Claude extraction failed: {str(e)}", exc_info=True)
            return False, {"error": str(e)}

    async def _compress_image(self, image_content: bytes) -> bytes:
        """Compress image to meet size requirements"""
        try:
            img = Image.open(BytesIO(image_content))

            # Convert RGBA to RGB if needed
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background

            # Resize if too large
            max_dimension = 2048
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save compressed
            output = BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            compressed = output.getvalue()

            logger.info(
                f"Compressed image from {len(image_content) / (1024 * 1024):.2f}MB to "
                f"{len(compressed) / (1024 * 1024):.2f}MB"
            )

            return compressed

        except Exception as e:
            logger.error(f"Image compression failed: {str(e)}")
            return image_content

    def _detect_media_type(self, image_content: bytes) -> str:
        """Detect image media type from content"""
        if image_content.startswith(b"\x89PNG"):
            return "image/png"
        elif image_content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif image_content.startswith(b"GIF"):
            return "image/gif"
        elif image_content.startswith(b"WEBP"):
            return "image/webp"
        else:
            return "image/png"

    def _build_extraction_prompt(
        self, chart_type: Optional[ChartType], context: Optional[str]
    ) -> str:
        """Build prompt for chart extraction"""
        prompt_parts = [
            "Extract structured data from this chart/graph image.",
            "",
            "Provide a JSON response with the following structure:",
            "{",
            '  "chart_type": "bar|line|pie|scatter|heatmap|box_plot|histogram|area|multi_panel|unknown",',
            '  "title": "Chart title from image",',
            '  "x_axis": {"label": "X-axis label", "unit": "unit if present"},',
            '  "y_axis": {"label": "Y-axis label", "unit": "unit if present"},',
            '  "legend": ["Series 1", "Series 2", ...],',
            '  "data": [',
            '    {"label": "Category/X value", "value": number, "series": "series name"},',
            "    ...",
            "  ],",
            '  "description": "Natural language description of the chart",',
            '  "confidence": 0.0-1.0',
            "}",
            "",
            "Extract ALL visible data points accurately with numeric precision.",
        ]

        if chart_type:
            prompt_parts.insert(
                2, f"Expected chart type: {chart_type.value} (but verify from image)"
            )

        if context:
            prompt_parts.insert(2, f"Context: {context}")

        return "\n".join(prompt_parts)

    def _parse_claude_response(self, response: Any) -> Dict:
        """Parse Claude Vision API response"""
        try:
            # Extract text from response
            text_content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_content += block.text

            return self._parse_vision_response_text(text_content)

        except Exception as e:
            logger.error(f"Failed to parse Claude response: {str(e)}")
            return {"chart_type": ChartType.UNKNOWN, "error": str(e), "confidence": 0.0}

    def _parse_vision_response_text(self, text_content: str) -> Dict:
        """Parse vision model response text (works for both Ollama and Claude)"""
        try:
            # Try to extract JSON from response
            import re

            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r"\{.*\}", text_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return {
                        "chart_type": ChartType.UNKNOWN,
                        "description": text_content,
                        "confidence": 0.5,
                        "raw_response": text_content,
                    }

            # Parse JSON
            result = json.loads(json_str)

            if "chart_type" not in result:
                result["chart_type"] = ChartType.UNKNOWN

            if "confidence" not in result:
                result["confidence"] = 0.8

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {
                "chart_type": ChartType.UNKNOWN,
                "description": text_content if text_content else "Failed to extract data",
                "confidence": 0.3,
                "error": "JSON parsing failed",
                "raw_response": text_content,
            }
        except Exception as e:
            logger.error(f"Failed to parse vision response: {str(e)}")
            return {
                "chart_type": ChartType.UNKNOWN,
                "error": str(e),
                "confidence": 0.0,
            }


# Singleton instance
_chart_extraction_service: Optional[ChartExtractionService] = None


def get_chart_extraction_service() -> ChartExtractionService:
    """Get the singleton chart extraction service instance"""
    global _chart_extraction_service
    if _chart_extraction_service is None:
        _chart_extraction_service = ChartExtractionService()
    return _chart_extraction_service
