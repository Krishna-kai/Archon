#!/usr/bin/env python3
"""
Simple OCR Service Comparison Script

Compares PyMuPDF, Docling OCR, and OCRmyPDF on a single PDF document.
"""

import asyncio
import os
import time
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import pymupdf  # PyMuPDF


async def test_pymupdf(pdf_path: str) -> dict:
    """Test PyMuPDF extraction."""
    print("Testing PyMuPDF...")
    start = time.time()

    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        page_count = len(doc)

        for page in doc:
            text += page.get_text()

        doc.close()

        elapsed = time.time() - start
        word_count = len(text.split())

        return {
            "service": "PyMuPDF",
            "success": True,
            "time": elapsed,
            "words": word_count,
            "pages": page_count,
            "text_length": len(text),
            "text_preview": text[:500] if text else "(empty)",
            "error": None
        }
    except Exception as e:
        return {
            "service": "PyMuPDF",
            "success": False,
            "time": time.time() - start,
            "words": 0,
            "error": str(e)
        }


async def test_docling(pdf_path: str) -> dict:
    """Test Docling OCR service."""
    print("Testing Docling OCR...")
    start = time.time()

    try:
        with open(pdf_path, "rb") as f:
            file_content = f.read()

        filename = Path(pdf_path).name

        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"file": (filename, file_content, "application/pdf")}
            data = {
                "output_format": "text",
                "do_ocr": "true",
                "include_tables": "true",
            }

            response = await client.post(
                "http://localhost:9000/ocr/pdf",
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()

        elapsed = time.time() - start

        if result.get("success"):
            text = result.get("text", "")
            word_count = len(text.split()) if text else 0
            metadata = result.get("metadata", {})

            return {
                "service": "Docling OCR",
                "success": True,
                "time": elapsed,
                "words": word_count,
                "pages": metadata.get("num_pages", "N/A"),
                "tables": metadata.get("num_tables", 0),
                "text_length": len(text),
                "text_preview": text[:500] if text else "(empty)",
                "conversion_time": metadata.get("conversion_time", "N/A"),
                "error": None
            }
        else:
            return {
                "service": "Docling OCR",
                "success": False,
                "time": elapsed,
                "words": 0,
                "error": result.get("error", "Unknown error")
            }
    except Exception as e:
        return {
            "service": "Docling OCR",
            "success": False,
            "time": time.time() - start,
            "words": 0,
            "error": str(e)
        }


async def test_ocrmypdf(pdf_path: str) -> dict:
    """Test OCRmyPDF service."""
    print("Testing OCRmyPDF...")
    start = time.time()

    try:
        with open(pdf_path, "rb") as f:
            file_content = f.read()

        filename = os.path.basename(pdf_path)

        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"file": (filename, file_content, "application/pdf")}
            data = {"output_format": "text"}

            response = await client.post(
                "http://localhost:9002/ocr/pdf",
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()

        elapsed = time.time() - start

        if result.get("success"):
            text = result.get("text", "")
            word_count = len(text.split()) if text else 0
            metadata = result.get("metadata", {})

            return {
                "service": "OCRmyPDF",
                "success": True,
                "time": elapsed,
                "words": word_count,
                "pages": metadata.get("page_count", "N/A"),
                "text_length": len(text),
                "text_preview": text[:500] if text else "(empty)",
                "error": None
            }
        else:
            return {
                "service": "OCRmyPDF",
                "success": False,
                "time": elapsed,
                "words": 0,
                "error": result.get("error", "Unknown error")
            }

    except Exception as e:
        return {
            "service": "OCRmyPDF",
            "success": False,
            "time": time.time() - start,
            "words": 0,
            "error": str(e)
        }


def print_results(results: list[dict]):
    """Print comparison results in a nice format."""
    print("\n" + "=" * 80)
    print("OCR SERVICE COMPARISON RESULTS")
    print("=" * 80)

    for result in results:
        print(f"\n{'─' * 80}")
        print(f"Service: {result['service']}")
        print(f"{'─' * 80}")

        if result["success"]:
            print(f"✅ Status: SUCCESS")
            print(f"⏱️  Time: {result['time']:.2f}s")
            print(f"📝 Words extracted: {result['words']:,}")
            print(f"📄 Pages: {result.get('pages', 'N/A')}")

            if "tables" in result:
                print(f"📊 Tables detected: {result['tables']}")

            if "conversion_time" in result and result["conversion_time"] != "N/A":
                print(f"🔄 Conversion time: {result['conversion_time']}")

            if result['words'] > 0:
                words_per_sec = result['words'] / result['time']
                print(f"⚡ Speed: {words_per_sec:,.0f} words/second")

                # Quality indicator
                text_len = result.get('text_length', 0)
                if text_len > 1000:
                    print(f"✨ Quality: Good ({text_len:,} chars)")
                elif text_len > 100:
                    print(f"⚠️  Quality: Moderate ({text_len:,} chars)")
                else:
                    print(f"⚠️  Quality: Low ({text_len:,} chars)")
            else:
                print("⚠️  No text extracted")

            # Show preview
            if result.get('text_preview') and result['text_preview'] != "(empty)":
                print(f"\n📖 Preview (first 200 chars):")
                preview = result['text_preview'][:200].replace('\n', ' ')
                print(f"   {preview}...")
        else:
            print(f"❌ Status: FAILED")
            print(f"⏱️  Time: {result['time']:.2f}s")
            print(f"❗ Error: {result['error']}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    # Find best service
    successful = [r for r in results if r["success"] and r["words"] > 0]

    if successful:
        # Sort by speed (time)
        fastest = min(successful, key=lambda r: r["time"])
        # Sort by word count
        most_words = max(successful, key=lambda r: r["words"])

        print(f"\n⚡ Fastest: {fastest['service']} ({fastest['time']:.2f}s)")
        print(f"📝 Most words: {most_words['service']} ({most_words['words']:,} words)")

        # Recommendation logic
        if fastest == most_words:
            print(f"\n🎯 RECOMMENDED: {fastest['service']}")
            print(f"   Reason: Best speed AND quality")
        elif fastest['words'] / most_words['words'] > 0.95:
            print(f"\n🎯 RECOMMENDED: {fastest['service']}")
            print(f"   Reason: Similar quality but {fastest['time'] / most_words['time']:.1f}x faster")
        else:
            print(f"\n🎯 RECOMMENDED: {most_words['service']}")
            print(f"   Reason: Significantly better quality (+{(most_words['words'] / fastest['words'] - 1) * 100:.0f}% more words)")
    else:
        print("\n❌ No services succeeded in extracting text")

    print("=" * 80 + "\n")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_ocr_services.py <pdf_path>")
        print("\nExample:")
        print("  python compare_ocr_services.py document.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    file_size = Path(pdf_path).stat().st_size / (1024 * 1024)  # MB

    print("=" * 80)
    print("OCR SERVICE COMPARISON")
    print("=" * 80)
    print(f"📄 File: {Path(pdf_path).name}")
    print(f"💾 Size: {file_size:.2f} MB")
    print(f"📍 Path: {pdf_path}")
    print("=" * 80)
    print("\nTesting all services (this may take a few minutes)...\n")

    # Run all tests
    results = await asyncio.gather(
        test_pymupdf(pdf_path),
        test_docling(pdf_path),
        test_ocrmypdf(pdf_path),
    )

    # Print results
    print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
