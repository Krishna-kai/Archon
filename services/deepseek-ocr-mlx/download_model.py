#!/usr/bin/env python3
"""
Pre-download DeepSeek-OCR model for MLX

This script downloads the DeepSeek-OCR-8bit model from Hugging Face
so it's cached and ready for first use.
"""

import sys
import time
from pathlib import Path

def download_model():
    """Download DeepSeek-OCR model using MLX-VLM"""

    print("=" * 60)
    print("🔽 DeepSeek-OCR MLX Model Download")
    print("=" * 60)
    print()
    print("📦 Model: mlx-community/DeepSeek-OCR-8bit")
    print("📏 Size: ~4-6 GB")
    print("📂 Cache: ~/.cache/mlx/")
    print()
    print("⚠️  This may take 5-10 minutes depending on your internet speed")
    print()

    # Import MLX-VLM
    try:
        import mlx_vlm
        print("✅ MLX-VLM imported successfully")
    except ImportError:
        print("❌ Error: mlx_vlm not found")
        print("📥 Installing mlx_vlm...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "mlx-vlm>=0.1.0"])
        import mlx_vlm
        print("✅ MLX-VLM installed")

    print()
    print("🔄 Starting model download...")
    print()

    start_time = time.time()

    try:
        # Load the model (this triggers download if not cached)
        model_name = "mlx-community/DeepSeek-OCR-8bit"

        print(f"📥 Downloading {model_name}...")
        print("   (This will be cached for future use)")
        print()

        # Load model and processor
        model, processor = mlx_vlm.load(model_name)

        elapsed = time.time() - start_time

        print()
        print("=" * 60)
        print("✅ Model download complete!")
        print("=" * 60)
        print()
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"📂 Model cached in: ~/.cache/mlx/")
        print()
        print("🚀 You can now start the service:")
        print("   ./start_service.sh")
        print()

        return True

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
        print("   2. Make sure you have ~6 GB free disk space")
        print("   3. Try running again (downloads can resume)")
        print()
        return False

def check_if_cached():
    """Check if model is already cached"""
    cache_dir = Path.home() / ".cache" / "mlx"

    if cache_dir.exists():
        # Look for DeepSeek-OCR model files
        model_files = list(cache_dir.glob("**/DeepSeek*"))
        if model_files:
            print("✅ Model appears to be already cached!")
            print(f"📂 Found in: {cache_dir}")
            print()
            response = input("🔄 Re-download anyway? (y/N): ")
            if response.lower() != 'y':
                print("⏭️  Skipping download")
                return True

    return False

if __name__ == "__main__":
    print()

    # Check if already cached
    if check_if_cached():
        sys.exit(0)

    # Download model
    success = download_model()

    sys.exit(0 if success else 1)
