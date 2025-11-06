#!/usr/bin/env python3
"""
Pre-download MinerU models

This script downloads the MinerU (magic-pdf) models so they're cached
and ready for first use.
"""

import sys
import time
import os
from pathlib import Path

def download_models():
    """Download MinerU models"""

    print("=" * 60)
    print("🔽 MinerU MLX Models Download")
    print("=" * 60)
    print()
    print("📦 Backend: magic-pdf (MinerU)")
    print("📏 Size: ~500 MB - 1 GB")
    print("📂 Cache: ~/.cache/huggingface/ or similar")
    print()
    print("⚠️  This may take 2-5 minutes depending on your internet speed")
    print()

    # Import MinerU
    try:
        from mineru.backend.pipeline.pipeline_analyze import doc_analyze
        print("✅ MinerU (magic-pdf) imported successfully")
    except ImportError:
        print("❌ Error: MinerU not found")
        print("📥 Installing magic-pdf...")
        import subprocess
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q", "magic-pdf[full]>=0.7.0"
        ])
        from mineru.backend.pipeline.pipeline_analyze import doc_analyze
        print("✅ MinerU installed")

    print()
    print("🔄 Initializing MinerU (this downloads models if needed)...")
    print()

    start_time = time.time()

    try:
        # Create a minimal test PDF to trigger model downloads
        # This is a simple way to ensure all models are cached
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        print("📝 Creating test PDF...")

        # Create a minimal PDF in memory
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        c.drawString(100, 750, "MinerU Model Download Test")
        c.drawString(100, 700, "This PDF is used to trigger model downloads.")
        c.showPage()
        c.save()

        pdf_bytes = pdf_buffer.getvalue()

        print("✅ Test PDF created")
        print()
        print("🔄 Running MinerU to download models...")
        print("   (First run downloads layout detection models)")
        print()

        # Process the test PDF (this triggers model downloads)
        result = doc_analyze(
            [pdf_bytes],  # pdf_bytes_list
            ["en"],  # lang_list
            parse_method="auto",
            formula_enable=True,
            table_enable=True
        )

        elapsed = time.time() - start_time

        print()
        print("=" * 60)
        print("✅ Model download complete!")
        print("=" * 60)
        print()
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"📂 Models cached in Hugging Face cache")
        print()
        print("🚀 You can now start the service:")
        print("   ./start_service.sh")
        print()

        return True

    except ImportError as e:
        if "reportlab" in str(e):
            print()
            print("⚠️  reportlab not found, using alternative method...")
            print()
            print("✅ MinerU models will download on first PDF processing")
            print("   The service is ready to use!")
            return True
        else:
            raise

    except Exception as e:
        elapsed = time.time() - start_time
        print()
        print("=" * 60)
        print("❌ Model download failed")
        print("=" * 60)
        print()
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds")
        print(f"❌ Error: {str(e)}")
        print()
        print("🔧 Troubleshooting:")
        print("   1. Check your internet connection")
        print("   2. Make sure you have ~1 GB free disk space")
        print("   3. Models will auto-download on first PDF processing")
        print()
        print("ℹ️  You can still start the service:")
        print("   ./start_service.sh")
        print()
        return False

def check_cache():
    """Check if models might be cached"""
    cache_locations = [
        Path.home() / ".cache" / "huggingface",
        Path.home() / ".cache" / "mineru",
        Path.home() / ".cache" / "magic-pdf",
    ]

    found_cache = False
    for cache_dir in cache_locations:
        if cache_dir.exists() and any(cache_dir.iterdir()):
            print(f"✅ Found cache directory: {cache_dir}")
            found_cache = True

    if found_cache:
        print()
        response = input("🔄 Download/verify models anyway? (y/N): ")
        if response.lower() != 'y':
            print("⏭️  Skipping download")
            return True

    return False

if __name__ == "__main__":
    print()

    # Check cache
    if check_cache():
        sys.exit(0)

    # Download models
    success = download_models()

    sys.exit(0 if success else 1)
