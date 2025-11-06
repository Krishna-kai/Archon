#!/usr/bin/env python3
"""
Test script for local-only image content processing.
Tests Ollama vision capabilities on sample images.

Usage:
    python scripts/test_local_image_processing.py <image_path>
"""

import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Dict

import httpx


class LocalImageProcessor:
    """Test local image processing with Ollama"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.vision_model = "llama3.2-vision:11b"
        self.embed_model = "nomic-embed-text"
        self.timeout = 120.0

    async def check_ollama_health(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    has_vision = any(
                        self.vision_model in model["name"] for model in models
                    )
                    has_embed = any(
                        self.embed_model in model["name"] for model in models
                    )

                    print(f"✅ Ollama is running")
                    print(f"   Vision model ({self.vision_model}): {'✅' if has_vision else '❌'}")
                    print(f"   Embed model ({self.embed_model}): {'✅' if has_embed else '❌'}")

                    return has_vision and has_embed

                return False
        except Exception as e:
            print(f"❌ Ollama is not available: {e}")
            return False

    def load_image_as_base64(self, image_path: str) -> str:
        """Load image and convert to base64"""
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        return base64.b64encode(image_bytes).decode("utf-8")

    async def extract_ocr_and_classify(self, image_base64: str) -> Dict:
        """
        Extract OCR text and classify image using Ollama vision model.
        """

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
  "technical_domain": "machine_learning|circuits|biology|mathematics|etc"
}
"""

        print("\n📊 Extracting OCR and classifying image...")
        print(f"   Model: {self.vision_model}")
        print(f"   Prompt length: {len(prompt)} chars")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False,
                        "format": "json",
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

                result = response.json()

                # Parse the response
                response_text = result.get("response", "{}")

                # Try to parse as JSON
                try:
                    content = json.loads(response_text)
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract JSON from markdown
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                    if json_match:
                        content = json.loads(json_match.group(1))
                    else:
                        raise Exception(f"Could not parse JSON from response: {response_text[:200]}")

                print("✅ OCR and classification complete")
                return content

        except Exception as e:
            print(f"❌ Error during OCR extraction: {e}")
            raise

    async def extract_structured_data(
        self, image_base64: str, classification: Dict
    ) -> Dict:
        """
        Extract structured data from charts/tables.
        """

        image_type = classification.get("image_type")

        if image_type not in ["chart", "table", "diagram"]:
            print(f"⏭️  Skipping structured extraction (not a {image_type})")
            return None

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
      "data_points": [[x1, y1], [x2, y2], [x3, y3]]
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

        print(f"\n🔍 Extracting structured data from {image_type}...")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
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
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                    if json_match:
                        content = json.loads(json_match.group(1))
                    else:
                        print(f"⚠️  Could not parse structured data")
                        return None

                print("✅ Structured data extraction complete")
                return content

        except Exception as e:
            print(f"⚠️  Error during structured extraction: {e}")
            return None

    async def generate_embedding(self, text: str) -> list:
        """Generate embedding using Ollama"""

        print(f"\n🧮 Generating embedding for text ({len(text)} chars)...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text},
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")

                result = response.json()
                embedding = result.get("embedding", [])

                print(f"✅ Generated embedding (dimension: {len(embedding)})")
                return embedding

        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise

    async def process_image(self, image_path: str):
        """Complete processing pipeline for a single image"""

        print(f"\n{'='*70}")
        print(f"🖼️  PROCESSING IMAGE: {image_path}")
        print(f"{'='*70}")

        # Check Ollama health
        if not await self.check_ollama_health():
            print("\n❌ Cannot proceed - Ollama is not available")
            return

        # Load image
        print(f"\n📁 Loading image: {image_path}")
        try:
            image_base64 = self.load_image_as_base64(image_path)
            image_size_kb = len(image_base64) * 3 / 4 / 1024  # Approximate size in KB
            print(f"✅ Image loaded ({image_size_kb:.1f} KB)")
        except Exception as e:
            print(f"❌ Error loading image: {e}")
            return

        # Step 1: OCR + Classification
        try:
            classification = await self.extract_ocr_and_classify(image_base64)

            print(f"\n📋 CLASSIFICATION RESULTS:")
            print(f"   Type: {classification.get('image_type')} ({classification.get('subtype')})")
            print(f"   Confidence: {classification.get('confidence', 0):.2%}")
            print(f"   Domain: {classification.get('technical_domain')}")
            print(f"   Key Elements: {', '.join(classification.get('key_elements', []))}")
            print(f"\n📝 OCR TEXT:")
            ocr_text = classification.get('ocr_text', '')
            print(f"   Length: {len(ocr_text)} characters")
            if ocr_text:
                preview = ocr_text[:200] + "..." if len(ocr_text) > 200 else ocr_text
                print(f"   Preview: {preview}")

        except Exception as e:
            print(f"\n❌ Classification failed: {e}")
            return

        # Step 2: Structured Data Extraction
        structured_data = await self.extract_structured_data(image_base64, classification)

        if structured_data:
            print(f"\n📊 STRUCTURED DATA:")
            print(json.dumps(structured_data, indent=2))

        # Step 3: Generate Embedding
        try:
            content_for_embedding = ocr_text
            if structured_data:
                content_for_embedding += f"\n\nStructured data: {json.dumps(structured_data)}"

            embedding = await self.generate_embedding(content_for_embedding)

        except Exception as e:
            print(f"\n⚠️  Embedding generation failed: {e}")
            embedding = None

        # Summary
        print(f"\n{'='*70}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'='*70}")
        print(f"   OCR Text: {len(ocr_text)} chars")
        print(f"   Image Type: {classification.get('image_type')}")
        print(f"   Structured Data: {'Yes' if structured_data else 'No'}")
        print(f"   Embedding: {'Generated' if embedding else 'Failed'}")
        print(f"{'='*70}\n")

        return {
            "classification": classification,
            "structured_data": structured_data,
            "embedding": embedding,
            "embedding_dim": len(embedding) if embedding else 0,
        }


async def main():
    """Main test function"""

    if len(sys.argv) < 2:
        print("Usage: python test_local_image_processing.py <image_path>")
        print("\nExample:")
        print("  python test_local_image_processing.py /path/to/chart.png")
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"❌ Error: Image not found: {image_path}")
        sys.exit(1)

    processor = LocalImageProcessor()
    await processor.process_image(image_path)


if __name__ == "__main__":
    asyncio.run(main())
