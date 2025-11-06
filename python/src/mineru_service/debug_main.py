"""
Debug version of MinerU service to inspect actual data structures
"""

import asyncio
import json
from pathlib import Path

from mineru.backend.pipeline.pipeline_analyze import doc_analyze


async def test_mineru_structure():
    """Test MinerU with a small PDF to see actual data structure"""

    # Use a simple test - just create minimal test PDF bytes
    # For now, let's just print what we can infer from the source code

    print("=" * 80)
    print("MinerU Data Structure Analysis")
    print("=" * 80)

    print("\nFrom source code analysis:")
    print("\n1. doc_analyze() returns a tuple:")
    print("   (infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list)")

    print("\n2. infer_results structure:")
    print("   - List of lists (one per PDF)")
    print("   - Each inner list contains page dictionaries")
    print("   - Page dict structure:")
    print("     {")
    print("       'layout_dets': <results from batch_image_analyze>,")
    print("       'page_info': {")
    print("         'page_no': int,")
    print("         'width': int,")
    print("         'height': int")
    print("       }")
    print("     }")

    print("\n3. layout_dets contains:")
    print("   - Results from BatchAnalyze model")
    print("   - Each detection has fields like:")
    print("     - category_type: str (e.g., 'text', 'title', 'formula', 'table')")
    print("     - text: str (the actual content)")
    print("     - bbox: coordinates")
    print("     - possibly other fields")

    print("\n4. KEY INSIGHT:")
    print("   The main.py code iterates:")
    print("   ```python")
    print("   for det in layout_dets:")
    print("       det_type = det.get('category_type', 'text')")
    print("       det_text = det.get('text', '')")
    print("   ```")

    print("\n5. PROBLEM:")
    print("   - If layout_dets is empty or malformed, no text is extracted")
    print("   - Need to check if batch_image_analyze is returning proper data")
    print("   - Or if the structure has changed in newer MinerU versions")

    print("\n6. SOLUTION:")
    print("   - Add debug logging to print actual layout_dets structure")
    print("   - Check MinerU version compatibility")
    print("   - May need to use different fields or iterate differently")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_mineru_structure())
