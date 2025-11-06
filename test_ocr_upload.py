#!/usr/bin/env python3
"""
Monitor OCR upload progress for histopathology research paper
"""
import requests
import time
import sys
from datetime import datetime

# Progress ID from upload response
PROGRESS_ID = "6d03a511-93b9-4862-822c-da1cf23787bb"
PROGRESS_URL = f"http://localhost:9181/api/crawl-progress/{PROGRESS_ID}"

print("=" * 80)
print("🔍 Monitoring DeepSeek OCR Progress")
print("=" * 80)
print(f"📄 File: Nuclei Segmentation Research Paper (PDF)")
print(f"🆔 Progress ID: {PROGRESS_ID}")
print(f"⏱️  Started: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 80)
print()

start_time = time.time()
last_log = ""
check_count = 0

while True:
    check_count += 1
    elapsed = int(time.time() - start_time)

    try:
        response = requests.get(PROGRESS_URL, timeout=5)
        progress = response.json()

        status = progress.get('status', 'unknown')
        percent = progress.get('progress', 0)
        log = progress.get('log', '')
        chunks = progress.get('chunksStored', 0)
        source_id = progress.get('sourceId', '')

        # Only print if log changed or every 5th check
        if log != last_log or check_count % 5 == 0:
            print(f"[{elapsed:3d}s] Status: {status:12s} | Progress: {percent:3d}% | Chunks: {chunks:3d}")
            if log and log != last_log:
                print(f"       📝 {log}")
            last_log = log

        # Check for completion
        if status in ['completed', 'failed', 'error']:
            print()
            print("=" * 80)
            if status == 'completed':
                print("✅ OCR EXTRACTION COMPLETE!")
                print(f"📊 Total chunks stored: {chunks}")
                print(f"🔗 Source ID: {source_id}")
                print(f"⏱️  Total time: {elapsed} seconds ({elapsed // 60}m {elapsed % 60}s)")

                # Show final statistics
                if progress.get('metadata'):
                    meta = progress['metadata']
                    print(f"📏 Word count: {meta.get('word_count', 'N/A')}")
                    print(f"📄 Page count: {meta.get('page_count', 'N/A')}")
            else:
                print("❌ UPLOAD FAILED")
                print(f"Error: {log}")
            print("=" * 80)
            sys.exit(0 if status == 'completed' else 1)

        # Wait before next check
        time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring interrupted by user")
        print(f"⏱️  Elapsed time: {elapsed}s")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error checking progress: {e}")
        time.sleep(2)
