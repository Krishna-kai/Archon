"""
Tests for ImageProcessingAgent

This module tests the new PydanticAI-based image processing agent.
"""

import asyncio
import base64
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.image_processing_agent import (
    ExtractedImage,
    ImageProcessingAgent,
    ImageProcessingDependencies,
    ProcessingResult,
    get_image_processing_agent,
)


# Set dummy OpenAI API key for testing (PydanticAI requires it but we won't actually call the LLM)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-testing-only")


@pytest.fixture
def sample_pdf_bytes():
    """Create fake PDF bytes for testing."""
    return b"%PDF-1.4\n%Fake PDF content for testing\n%%EOF"


@pytest.fixture
def mock_mineru_result():
    """Mock MinerU service result."""
    return {
        "success": True,
        "markdown": "# Test Document\n\nThis is a test document with formulas $E=mc^2$.",
        "charts": [
            {
                "name": "image_0.png",
                "base64": base64.b64encode(b"fake_image_data").decode(),
                "page_number": 1,
                "image_index": 0,
                "mime_type": "image/png",
            }
        ],
        "metadata": {
            "filename": "test.pdf",
            "formulas_count": 5,
            "tables_count": 2,
            "pages": 3,
        },
    }


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "response": """{
  "ocr_text": "Figure 1: Test diagram",
  "description": "A technical diagram showing system architecture",
  "classification": "diagram",
  "confidence": 0.92
}"""
    }


class TestImageProcessingAgent:
    """Test suite for ImageProcessingAgent."""

    def test_agent_initialization(self):
        """Test agent can be initialized with default settings."""
        agent = ImageProcessingAgent()
        assert agent.name == "ImageProcessingAgent"
        assert agent.retries == 3
        assert agent.enable_rate_limiting is True

    def test_singleton_pattern(self):
        """Test that get_image_processing_agent returns singleton."""
        agent1 = get_image_processing_agent()
        agent2 = get_image_processing_agent()
        assert agent1 is agent2

    @pytest.mark.asyncio
    async def test_process_document_basic(
        self, sample_pdf_bytes, mock_mineru_result
    ):
        """Test basic document processing without Ollama."""
        agent = ImageProcessingAgent()

        # Mock the MinerU service
        with patch("src.server.services.mineru_service.get_mineru_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_pdf.return_value = (True, mock_mineru_result)
            mock_get_service.return_value = mock_service

            # Process document
            result = await agent.process_document(
                file_content=sample_pdf_bytes,
                filename="test.pdf",
                analyze_images=False,  # Skip Ollama for this test
            )

            # Verify result
            assert result.success is True
            assert result.filename == "test.pdf"
            assert result.page_count == 3
            assert result.formula_count == 5
            assert result.table_count == 2
            assert result.image_count == 1
            assert len(result.images) == 1
            assert result.markdown_text == "# Test Document\n\nThis is a test document with formulas $E=mc^2$."

    @pytest.mark.asyncio
    async def test_process_document_with_ollama(
        self, sample_pdf_bytes, mock_mineru_result, mock_ollama_response
    ):
        """Test document processing with Ollama image analysis."""
        agent = ImageProcessingAgent()

        # Mock the MinerU service
        with patch("src.server.services.mineru_service.get_mineru_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_pdf.return_value = (True, mock_mineru_result)
            mock_get_service.return_value = mock_service

            # Mock httpx client for Ollama
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()  # Not async - it's a response object
                mock_response.status_code = 200
                mock_response.json.return_value = mock_ollama_response
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Process document with Ollama analysis
                result = await agent.process_document(
                    file_content=sample_pdf_bytes,
                    filename="test.pdf",
                    analyze_images=True,
                    ollama_base_url="http://localhost:11434",
                    ollama_model="llama3.2-vision",
                )

                # Verify result
                assert result.success is True
                assert result.image_count == 1
                assert len(result.images) == 1

                # Verify Ollama analysis was applied
                image = result.images[0]
                assert image.ocr_text == "Figure 1: Test diagram"
                assert image.description == "A technical diagram showing system architecture"
                assert image.classification == "diagram"
                assert image.confidence == 0.92

    @pytest.mark.asyncio
    async def test_process_document_with_progress_callback(
        self, sample_pdf_bytes, mock_mineru_result
    ):
        """Test that progress callbacks are called during processing."""
        agent = ImageProcessingAgent()
        progress_logs = []

        async def track_progress(update):
            progress_logs.append(update)

        # Mock the MinerU service
        with patch("src.server.services.mineru_service.get_mineru_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_pdf.return_value = (True, mock_mineru_result)
            mock_get_service.return_value = mock_service

            # Process document with progress callback
            result = await agent.process_document(
                file_content=sample_pdf_bytes,
                filename="test.pdf",
                progress_callback=track_progress,
                analyze_images=False,
            )

            # Verify progress was tracked
            assert result.success is True
            assert len(progress_logs) >= 2  # At least start and complete
            assert any("Processing PDF" in log.get("log", "") for log in progress_logs)
            assert any("complete" in log.get("log", "").lower() for log in progress_logs)

    @pytest.mark.asyncio
    async def test_process_document_mineru_failure(self, sample_pdf_bytes):
        """Test handling of MinerU processing failure."""
        agent = ImageProcessingAgent()

        # Mock the MinerU service to fail
        with patch("src.server.services.mineru_service.get_mineru_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_pdf.return_value = (
                False,
                {"error": "MinerU processing failed"},
            )
            mock_get_service.return_value = mock_service

            # Process document
            result = await agent.process_document(
                file_content=sample_pdf_bytes,
                filename="test.pdf",
            )

            # Verify error handling
            assert result.success is False
            assert "MinerU processing failed" in result.message
            assert result.error is not None
            assert result.image_count == 0

    @pytest.mark.asyncio
    async def test_process_document_ollama_failure_continues(
        self, sample_pdf_bytes, mock_mineru_result
    ):
        """Test that Ollama failure doesn't stop processing."""
        agent = ImageProcessingAgent()

        # Mock the MinerU service
        with patch("src.server.services.mineru_service.get_mineru_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_pdf.return_value = (True, mock_mineru_result)
            mock_get_service.return_value = mock_service

            # Mock httpx client for Ollama to fail
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()  # Not async - it's a response object
                mock_response.status_code = 500  # Simulate Ollama failure
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Process document with Ollama analysis
                result = await agent.process_document(
                    file_content=sample_pdf_bytes,
                    filename="test.pdf",
                    analyze_images=True,
                )

                # Verify processing succeeded despite Ollama failure
                assert result.success is True
                assert result.image_count == 1
                # Image should exist but without Ollama analysis
                assert result.images[0].ocr_text is None

    def test_extracted_image_model(self):
        """Test ExtractedImage Pydantic model validation."""
        image = ExtractedImage(
            name="test.png",
            base64_data="fake_base64_data",
            page_number=1,
            image_index=0,
            mime_type="image/png",
        )

        assert image.name == "test.png"
        assert image.page_number == 1
        assert image.image_index == 0
        assert image.ocr_text is None  # Optional field
        assert image.description is None

    def test_processing_result_model(self):
        """Test ProcessingResult Pydantic model validation."""
        result = ProcessingResult(
            success=True,
            filename="test.pdf",
            markdown_text="# Test",
            images=[],
            metadata={"pages": 1},
            message="Success",
            page_count=1,
            formula_count=0,
            table_count=0,
            image_count=0,
        )

        assert result.success is True
        assert result.filename == "test.pdf"
        assert result.page_count == 1
        assert result.error is None  # Optional field


@pytest.mark.integration
class TestImageProcessingAgentIntegration:
    """Integration tests requiring real services."""

    @pytest.mark.asyncio
    async def test_real_pdf_processing(self):
        """
        Integration test with a real PDF file.

        Note: This test requires:
        1. MinerU service running (native or Docker)
        2. Sample PDF file in tests/fixtures/
        """
        pytest.skip("Integration test - requires MinerU service")

        agent = get_image_processing_agent()
        pdf_path = Path("tests/fixtures/sample.pdf")

        if not pdf_path.exists():
            pytest.skip(f"Sample PDF not found: {pdf_path}")

        pdf_bytes = pdf_path.read_bytes()
        progress_logs = []

        async def track_progress(update):
            progress_logs.append(update)
            print(f"[{update['step']}] {update['log']}")

        result = await agent.process_document(
            file_content=pdf_bytes,
            filename="sample.pdf",
            progress_callback=track_progress,
            analyze_images=False,  # Skip Ollama for faster test
        )

        # Verify basic processing
        assert result.success is True
        assert len(result.markdown_text) > 0
        assert len(progress_logs) > 0

    @pytest.mark.asyncio
    async def test_real_ollama_analysis(self):
        """
        Integration test with real Ollama service.

        Note: This test requires:
        1. Ollama running locally on port 11434
        2. llama3.2-vision model installed
        """
        pytest.skip("Integration test - requires Ollama service")

        agent = get_image_processing_agent()

        # Create a simple test image (1x1 red pixel PNG)
        import io
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        # Create fake PDF with this image
        fake_mineru_result = {
            "success": True,
            "markdown": "# Test",
            "charts": [
                {
                    "name": "test.png",
                    "base64": base64.b64encode(img_bytes).decode(),
                    "page_number": 1,
                    "image_index": 0,
                    "mime_type": "image/png",
                }
            ],
            "metadata": {"pages": 1, "formulas_count": 0, "tables_count": 0},
        }

        with patch("src.agents.image_processing_agent.get_mineru_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.process_pdf.return_value = (True, fake_mineru_result)
            mock_get_service.return_value = mock_service

            result = await agent.process_document(
                file_content=b"fake_pdf",
                filename="test.pdf",
                analyze_images=True,
                ollama_base_url="http://localhost:11434",
                ollama_model="llama3.2-vision",
            )

            # Verify Ollama was called and returned some analysis
            assert result.success is True
            assert len(result.images) == 1
            # Ollama should have provided some description
            assert result.images[0].description is not None or result.images[0].ocr_text is not None


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_image_processing_agent.py -v
    pytest.main([__file__, "-v", "--tb=short"])
