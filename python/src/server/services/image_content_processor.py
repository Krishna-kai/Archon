"""
Local-only image content processing service.
Uses Ollama for all vision tasks (OCR, classification, chart extraction).
"""

import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional
from uuid import UUID

import httpx

from .client_manager import get_supabase_client
from .storage import get_image_storage_service

logger = logging.getLogger(__name__)


class ImageContentProcessor:
    """Process image content using local-only services (Ollama)"""

    def __init__(self):
        import os
        # Use host.docker.internal when running in Docker, localhost otherwise
        ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.ollama_base_url = ollama_host
        self.vision_model = "llama3.2-vision:11b"
        self.embed_model = "nomic-embed-text"
        self.timeout = 120.0

        self.image_storage = get_image_storage_service()
        self.supabase = get_supabase_client()

    async def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    has_vision = any(self.vision_model in m["name"] for m in models)
                    has_embed = any(self.embed_model in m["name"] for m in models)
                    return has_vision and has_embed
                return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def process_image_content(
        self, image_id: UUID, force_refresh: bool = False
    ) -> Dict:
        """
        Complete local processing pipeline for a single image.

        Args:
            image_id: UUID of image to process
            force_refresh: Re-process even if already processed

        Returns:
            Processing results with all extracted content
        """

        # Check if already processed
        if not force_refresh:
            record = await self._get_image_record(image_id)
            if record and record.get("ocr_processed") and record.get("embedding_generated"):
                logger.info(f"Image {image_id} already processed")
                return {"status": "already_processed", "record": record}

        # Get image data
        image_data = await self._fetch_image_data(image_id)
        if not image_data:
            raise Exception(f"Image {image_id} not found")

        logger.info(f"Processing image {image_id} (type: {image_data.get('mime_type')})")

        # Extract content with Ollama
        ocr_classification = await self._extract_ocr_and_classify(image_data["base64"])

        # Extract structured data if applicable
        structured_data = None
        if ocr_classification["image_type"] in ["chart", "table", "diagram"]:
            try:
                structured_data = await self._extract_structured_data(
                    image_data["base64"], ocr_classification
                )
            except Exception as e:
                logger.warning(f"Structured extraction failed: {e}")

        # Get surrounding text from document
        surrounding_text = await self._get_surrounding_text(
            image_data["source_id"], image_data.get("page_number")
        )

        # Generate embedding
        content_for_embedding = self._prepare_content_for_embedding(
            ocr_classification["ocr_text"], surrounding_text, structured_data
        )

        embedding = await self._generate_embedding_local(content_for_embedding)

        # Update database
        await self._update_image_record(
            image_id=image_id,
            ocr_text=ocr_classification["ocr_text"],
            image_type=ocr_classification["image_type"],
            surrounding_text=surrounding_text,
            metadata={
                "classification": ocr_classification,
                "structured_data": structured_data,
            },
            embedding=embedding,
        )

        logger.info(f"Successfully processed image {image_id}")

        return {
            "status": "success",
            "image_id": str(image_id),
            "ocr_length": len(ocr_classification["ocr_text"]),
            "image_type": ocr_classification["image_type"],
            "has_structured_data": structured_data is not None,
            "embedding_generated": True,
        }

    async def process_all_images_for_source(
        self, source_id: str, force_refresh: bool = False
    ) -> Dict:
        """
        Process all images for a source document.

        Args:
            source_id: Source document ID
            force_refresh: Re-process already processed images

        Returns:
            Summary of processing results
        """

        logger.info(f"Processing all images for source {source_id}")

        # Get all images for source
        images = await self.image_storage.get_images_by_source(
            source_id, include_signed_urls=False
        )

        if not images:
            logger.info(f"No images found for source {source_id}")
            return {"status": "no_images", "source_id": source_id, "processed": 0}

        logger.info(f"Found {len(images)} images to process")

        # Process each image
        results = []
        for image in images:
            try:
                result = await self.process_image_content(
                    UUID(image["id"]), force_refresh=force_refresh
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process image {image['id']}: {e}")
                results.append({"status": "error", "image_id": image["id"], "error": str(e)})

        # Summary
        success_count = sum(1 for r in results if r.get("status") == "success")
        already_processed = sum(1 for r in results if r.get("status") == "already_processed")
        error_count = sum(1 for r in results if r.get("status") == "error")

        logger.info(
            f"Processed {len(images)} images: {success_count} new, "
            f"{already_processed} already done, {error_count} errors"
        )

        return {
            "status": "complete",
            "source_id": source_id,
            "total_images": len(images),
            "processed": success_count,
            "already_processed": already_processed,
            "errors": error_count,
            "results": results,
        }

    async def _extract_ocr_and_classify(self, image_base64: str) -> Dict:
        """Extract OCR text and classify image using Ollama vision model"""

        prompt = """
Analyze this image from a technical/scientific document.

Tasks:
1. Extract ALL visible text using OCR (be thorough and accurate)
2. Classify the image type
3. Identify key elements and technical domain

Return ONLY valid JSON (no markdown, no explanation, no code blocks):
{
  "ocr_text": "complete extracted text from the image",
  "image_type": "chart|diagram|table|formula|photo|flowchart|circuit|screenshot",
  "subtype": "specific type like bar_chart, line_plot, system_diagram, etc",
  "confidence": 0.95,
  "key_elements": ["list", "of", "key", "elements", "visible"],
  "technical_domain": "machine_learning|biology|medical|circuits|mathematics|etc"
}
"""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False,
                        "format": "json",
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")

                result = response.json()
                response_text = result.get("response", "{}")

                # Parse JSON
                try:
                    content = json.loads(response_text)
                except json.JSONDecodeError:
                    # Fallback: try to extract JSON from markdown
                    import re

                    json_match = re.search(
                        r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
                    )
                    if json_match:
                        content = json.loads(json_match.group(1))
                    else:
                        logger.warning(f"Could not parse JSON: {response_text[:200]}")
                        raise

                return content

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise

    async def _extract_structured_data(
        self, image_base64: str, classification: Dict
    ) -> Optional[Dict]:
        """Extract structured data from charts/tables using Ollama"""

        image_type = classification.get("image_type")

        if image_type == "chart":
            prompt = f"""
This is a {classification.get('subtype', 'chart')} from a technical paper.

Extract the chart data in structured format. Be precise with numbers.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "chart_type": "line|bar|scatter|pie|heatmap",
  "axes": {{
    "x": {{"label": "x-axis label", "unit": "unit", "range": [min, max]}},
    "y": {{"label": "y-axis label", "unit": "unit", "range": [min, max]}}
  }},
  "series": [
    {{
      "name": "series name",
      "data_points": [[x1, y1], [x2, y2]]
    }}
  ],
  "legend": ["legend item 1", "legend item 2"],
  "caption": "figure caption text",
  "key_finding": "main insight or pattern"
}}
"""

        elif image_type == "table":
            prompt = """
Extract the table data in structured format. Preserve all values accurately.

Return ONLY valid JSON (no markdown, no explanation):
{
  "headers": ["column1", "column2", "column3"],
  "rows": [
    ["val1", "val2", "val3"],
    ["val4", "val5", "val6"]
  ],
  "caption": "table caption if visible",
  "notes": "any footnotes or notes"
}
"""
        else:
            prompt = """
Extract key information from this diagram.

Return ONLY valid JSON (no markdown, no explanation):
{
  "diagram_type": "flowchart|system_diagram|network|circuit|etc",
  "components": ["component1", "component2"],
  "connections": [{"from": "A", "to": "B", "label": "connection type"}],
  "description": "overall description",
  "key_elements": ["important", "elements"]
}
"""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False,
                        "format": "json",
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")

                result = response.json()
                response_text = result.get("response", "{}")

                # Parse JSON
                try:
                    content = json.loads(response_text)
                except json.JSONDecodeError:
                    import re

                    json_match = re.search(
                        r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
                    )
                    if json_match:
                        content = json.loads(json_match.group(1))
                    else:
                        return None

                return content

        except Exception as e:
            logger.warning(f"Structured extraction failed: {e}")
            return None

    async def _generate_embedding_local(self, text: str) -> List[float]:
        """Generate embedding using local Ollama model"""

        if not text or not text.strip():
            logger.warning("Empty text for embedding, using default")
            text = "empty image content"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text[:2000]},  # Limit length
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama embedding error: {response.status_code}")

                result = response.json()
                return result.get("embedding", [])

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def _prepare_content_for_embedding(
        self, ocr_text: str, surrounding_text: Optional[str], structured_data: Optional[Dict]
    ) -> str:
        """Prepare combined content for embedding generation"""

        parts = []

        if ocr_text:
            parts.append(f"Image text: {ocr_text}")

        if surrounding_text:
            parts.append(f"Context: {surrounding_text}")

        if structured_data:
            parts.append(f"Data: {json.dumps(structured_data)}")

        return "\n\n".join(parts)[:2000]  # Limit total length

    async def _get_image_record(self, image_id: UUID) -> Optional[Dict]:
        """Get image record from database"""

        try:
            result = (
                self.supabase.table("archon_document_images")
                .select("*")
                .eq("id", str(image_id))
                .execute()
            )

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting image record: {e}")
            return None

    async def _fetch_image_data(self, image_id: UUID) -> Optional[Dict]:
        """Fetch image data including base64 from storage"""

        record = await self._get_image_record(image_id)
        if not record:
            return None

        # Get image from storage
        try:
            signed_url = self.image_storage.get_signed_url(record["storage_path"])

            # Download image
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(signed_url)
                if response.status_code != 200:
                    raise Exception(f"Failed to download image: {response.status_code}")

                image_bytes = response.content
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                return {
                    "id": record["id"],
                    "source_id": record["source_id"],
                    "page_number": record.get("page_number"),
                    "mime_type": record.get("mime_type", "image/jpeg"),
                    "base64": image_base64,
                }

        except Exception as e:
            logger.error(f"Error fetching image data: {e}")
            return None

    async def _get_surrounding_text(
        self, source_id: str, page_number: Optional[int]
    ) -> Optional[str]:
        """Get surrounding text from document chunks"""

        try:
            # Query for chunks from the same source
            query = self.supabase.table("documents").select("content").eq("source", source_id)

            # If we have page number, try to get nearby chunks
            if page_number is not None:
                query = query.limit(5)

            result = query.execute()

            if result.data:
                # Combine up to 3 chunks
                chunks = [chunk["content"] for chunk in result.data[:3]]
                return " ".join(chunks)[:500]  # Limit length

            return None

        except Exception as e:
            logger.warning(f"Error getting surrounding text: {e}")
            return None

    async def _update_image_record(
        self,
        image_id: UUID,
        ocr_text: str,
        image_type: str,
        surrounding_text: Optional[str],
        metadata: Dict,
        embedding: List[float],
    ) -> None:
        """Update image record in database with extracted content"""

        try:
            update_data = {
                "ocr_text": ocr_text,
                "image_type": image_type,
                "surrounding_text": surrounding_text,
                "metadata": metadata,
                "embedding": embedding,
                "ocr_processed": True,
                "embedding_generated": True,
                "updated_at": "now()",
            }

            result = (
                self.supabase.table("archon_document_images")
                .update(update_data)
                .eq("id", str(image_id))
                .execute()
            )

            if not result.data:
                raise Exception("Update returned no data")

            logger.info(f"Updated image record {image_id}")

        except Exception as e:
            logger.error(f"Error updating image record: {e}")
            raise


# Singleton instance
_image_content_processor: Optional[ImageContentProcessor] = None


def get_image_content_processor() -> ImageContentProcessor:
    """Get or create singleton image content processor instance"""
    global _image_content_processor
    if _image_content_processor is None:
        _image_content_processor = ImageContentProcessor()
    return _image_content_processor
