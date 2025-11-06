"""
Example Usage: ImageProcessingAgent

This script demonstrates how to use the PydanticAI-based ImageProcessingAgent
to process PDF documents with MinerU and optional Ollama image analysis.

Environment Variables:
    MINERU_SERVICE_URL - URL of native MinerU HTTP service (optional, uses CLI if not set)
    OLLAMA_BASE_URL - Base URL for Ollama API (default: http://localhost:11434)
    OLLAMA_MODEL - Ollama model name (default: llama3.2-vision)
    MINERU_DEVICE - Processing device (default: mps)
    MINERU_LANG - Document language (default: en)

Requirements:
    - MinerU v2.6.4+ installed (either CLI or running HTTP service)
    - Ollama running locally with llama3.2-vision model (if using image analysis)
    - Sample PDF file
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.image_processing_agent import (
    ImageProcessingAgent,
    ProcessingResult,
    get_image_processing_agent,
)


async def progress_callback(update: dict) -> None:
    """
    Progress callback for tracking processing status.

    Args:
        update: Progress update dictionary with 'step' and 'log' fields
    """
    step = update.get("step", "unknown")
    log = update.get("log", "")
    print(f"[{step}] {log}")


async def example_basic_processing():
    """
    Example 1: Basic PDF processing without Ollama analysis.

    This is the fastest option - processes PDF and extracts images,
    but doesn't analyze image content with Ollama.
    """
    print("\n" + "=" * 80)
    print("Example 1: Basic PDF Processing (No Ollama)")
    print("=" * 80 + "\n")

    # Get singleton agent instance
    agent = get_image_processing_agent()

    # Sample PDF path - replace with your actual PDF
    pdf_path = Path("tests/fixtures/sample.pdf")

    if not pdf_path.exists():
        print(f"❌ Sample PDF not found: {pdf_path}")
        print("   Please place a PDF file at this location or update the path")
        return

    # Read PDF bytes
    pdf_bytes = pdf_path.read_bytes()

    # Process document without Ollama analysis
    result: ProcessingResult = await agent.process_document(
        file_content=pdf_bytes,
        filename=pdf_path.name,
        progress_callback=progress_callback,
        analyze_images=False,  # Skip Ollama analysis
    )

    # Display results
    print_processing_result(result)


async def example_with_ollama():
    """
    Example 2: PDF processing WITH Ollama image analysis.

    This provides detailed image analysis including:
    - OCR text extraction
    - Image classification (diagram, chart, photo, etc.)
    - Detailed descriptions
    - Confidence scores

    Note: Requires Ollama running locally with llama3.2-vision model
    """
    print("\n" + "=" * 80)
    print("Example 2: PDF Processing WITH Ollama Analysis")
    print("=" * 80 + "\n")

    # Get singleton agent instance
    agent = get_image_processing_agent()

    # Sample PDF path - replace with your actual PDF
    pdf_path = Path("tests/fixtures/sample.pdf")

    if not pdf_path.exists():
        print(f"❌ Sample PDF not found: {pdf_path}")
        print("   Please place a PDF file at this location or update the path")
        return

    # Read PDF bytes
    pdf_bytes = pdf_path.read_bytes()

    # Process document with Ollama analysis
    result: ProcessingResult = await agent.process_document(
        file_content=pdf_bytes,
        filename=pdf_path.name,
        progress_callback=progress_callback,
        analyze_images=True,  # Enable Ollama analysis
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2-vision"),
    )

    # Display results with detailed image analysis
    print_processing_result(result, show_image_details=True)


async def example_custom_configuration():
    """
    Example 3: Custom configuration with environment variables.

    Demonstrates how to override default configurations:
    - Custom MinerU service URL
    - Custom Ollama settings
    - Different device (cpu, cuda, mps)
    - Different language processing
    """
    print("\n" + "=" * 80)
    print("Example 3: Custom Configuration")
    print("=" * 80 + "\n")

    # Get singleton agent instance
    agent = get_image_processing_agent()

    # Sample PDF path
    pdf_path = Path("tests/fixtures/sample.pdf")

    if not pdf_path.exists():
        print(f"❌ Sample PDF not found: {pdf_path}")
        return

    pdf_bytes = pdf_path.read_bytes()

    # Process with custom configuration
    result: ProcessingResult = await agent.process_document(
        file_content=pdf_bytes,
        filename=pdf_path.name,
        progress_callback=progress_callback,
        analyze_images=True,
        # Custom MinerU service (if using HTTP service)
        mineru_service_url=os.getenv("MINERU_SERVICE_URL", None),
        # Custom Ollama settings
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2-vision"),
        # MinerU processing options
        device=os.getenv("MINERU_DEVICE", "mps"),  # mps, cuda, or cpu
        lang=os.getenv("MINERU_LANG", "en"),  # Document language
        extract_charts=True,  # Extract charts/diagrams
        chart_provider="auto",  # auto, mathpix, or paddlex
    )

    print_processing_result(result)


async def example_batch_processing():
    """
    Example 4: Batch process multiple PDFs.

    Demonstrates processing multiple files with progress tracking
    and error handling for each file.
    """
    print("\n" + "=" * 80)
    print("Example 4: Batch Processing Multiple PDFs")
    print("=" * 80 + "\n")

    # Get singleton agent instance
    agent = get_image_processing_agent()

    # Sample PDF directory - replace with your actual directory
    pdf_directory = Path("tests/fixtures")
    pdf_files = list(pdf_directory.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in: {pdf_directory}")
        return

    print(f"📚 Found {len(pdf_files)} PDF files to process\n")

    results = []

    for pdf_path in pdf_files:
        print(f"\n{'─' * 80}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'─' * 80}\n")

        try:
            pdf_bytes = pdf_path.read_bytes()

            result: ProcessingResult = await agent.process_document(
                file_content=pdf_bytes,
                filename=pdf_path.name,
                progress_callback=progress_callback,
                analyze_images=False,  # Faster for batch processing
            )

            results.append({"filename": pdf_path.name, "result": result})

            if result.success:
                print(f"✅ Successfully processed: {pdf_path.name}")
            else:
                print(f"❌ Failed to process: {pdf_path.name} - {result.error}")

        except Exception as e:
            print(f"❌ Exception processing {pdf_path.name}: {str(e)}")
            results.append({"filename": pdf_path.name, "error": str(e)})

    # Summary
    print("\n" + "=" * 80)
    print("Batch Processing Summary")
    print("=" * 80 + "\n")

    successful = sum(1 for r in results if "result" in r and r["result"].success)
    failed = len(results) - successful

    print(f"Total files: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")


async def example_error_handling():
    """
    Example 5: Error handling and recovery.

    Demonstrates how to handle various error scenarios:
    - Invalid PDF files
    - MinerU service failures
    - Ollama analysis failures
    """
    print("\n" + "=" * 80)
    print("Example 5: Error Handling")
    print("=" * 80 + "\n")

    agent = get_image_processing_agent()

    # Test 1: Invalid PDF
    print("Test 1: Processing invalid PDF data")
    print("─" * 80)

    invalid_pdf = b"This is not a valid PDF file"

    result: ProcessingResult = await agent.process_document(
        file_content=invalid_pdf,
        filename="invalid.pdf",
        progress_callback=progress_callback,
        analyze_images=False,
    )

    if not result.success:
        print(f"✅ Expected failure handled correctly: {result.error}")
    else:
        print("❌ Unexpected success with invalid PDF")

    # Test 2: Ollama failure (continues processing)
    print("\n\nTest 2: Ollama failure scenario")
    print("─" * 80)

    pdf_path = Path("tests/fixtures/sample.pdf")
    if pdf_path.exists():
        pdf_bytes = pdf_path.read_bytes()

        result: ProcessingResult = await agent.process_document(
            file_content=pdf_bytes,
            filename=pdf_path.name,
            progress_callback=progress_callback,
            analyze_images=True,
            ollama_base_url="http://invalid-ollama-url:9999",  # Intentional failure
        )

        if result.success:
            print(
                "✅ Processing succeeded despite Ollama failure (graceful degradation)"
            )
            print(f"   Images extracted: {result.image_count}")
            print("   Image analysis: Skipped (Ollama unavailable)")
        else:
            print(f"Processing result: {result.message}")


def print_processing_result(result: ProcessingResult, show_image_details: bool = False):
    """
    Print formatted processing results.

    Args:
        result: ProcessingResult from agent
        show_image_details: Whether to show detailed image analysis
    """
    print("\n" + "═" * 80)
    print("Processing Results")
    print("═" * 80 + "\n")

    # Basic stats
    print(f"Status: {'✅ Success' if result.success else '❌ Failed'}")
    print(f"Filename: {result.filename}")
    print(f"Message: {result.message}")

    if result.error:
        print(f"Error: {result.error}")

    print(f"\nDocument Statistics:")
    print(f"  Pages: {result.page_count}")
    print(f"  Formulas: {result.formula_count}")
    print(f"  Tables: {result.table_count}")
    print(f"  Images: {result.image_count}")

    if result.processing_time_seconds:
        print(f"  Processing time: {result.processing_time_seconds:.2f}s")

    # Markdown preview
    if result.markdown_text:
        print(f"\nMarkdown Preview (first 500 chars):")
        print("─" * 80)
        print(result.markdown_text[:500])
        if len(result.markdown_text) > 500:
            print(f"... ({len(result.markdown_text) - 500} more characters)")

    # Image details
    if result.images and show_image_details:
        print(f"\nImage Analysis Details:")
        print("─" * 80)

        for i, image in enumerate(result.images, 1):
            print(f"\nImage {i}: {image.name}")
            print(f"  Page: {image.page_number}")
            print(f"  Index: {image.image_index}")
            print(f"  MIME Type: {image.mime_type}")
            print(f"  Data size: {len(image.base64_data)} bytes")

            if image.ocr_text:
                print(f"  OCR Text: {image.ocr_text[:100]}...")
            if image.description:
                print(f"  Description: {image.description[:100]}...")
            if image.classification:
                print(f"  Classification: {image.classification}")
            if image.confidence:
                print(f"  Confidence: {image.confidence:.2%}")

    # Metadata
    if result.metadata:
        print(f"\nMetadata:")
        print("─" * 80)
        print(json.dumps(result.metadata, indent=2))

    print("\n" + "═" * 80 + "\n")


async def main():
    """
    Main entry point - runs all examples.
    """
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "ImageProcessingAgent Usage Examples" + " " * 23 + "║")
    print("╚" + "═" * 78 + "╝")

    # Check environment
    print("\nEnvironment Configuration:")
    print("─" * 80)
    print(f"MINERU_SERVICE_URL: {os.getenv('MINERU_SERVICE_URL', 'Not set (will use CLI)')}")
    print(f"OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434 (default)')}")
    print(f"OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL', 'llama3.2-vision (default)')}")
    print(f"MINERU_DEVICE: {os.getenv('MINERU_DEVICE', 'mps (default)')}")
    print(f"MINERU_LANG: {os.getenv('MINERU_LANG', 'en (default)')}")

    # Run examples
    try:
        # Example 1: Basic processing
        await example_basic_processing()

        # Example 2: With Ollama (requires Ollama running)
        # Uncomment to enable:
        # await example_with_ollama()

        # Example 3: Custom configuration
        # await example_custom_configuration()

        # Example 4: Batch processing
        # await example_batch_processing()

        # Example 5: Error handling
        # await example_error_handling()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()

    print("\n✨ Examples complete!\n")


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
