# Image Extraction Bug Fix Summary

## Issue Reported
PDF files with images showed "0 images extracted" in the UI, even though images were clearly present in the document.

Test PDF: `Copy of Dual U-Net for the Segmentation of Overlapping Glioma Nuclei.pdf`

## Root Causes Identified

### 1. Embedded Images (FIXED ✅)
**Problem**: MinerU returns embedded images as dictionaries with key `'img_pil'`, not direct PIL Image objects.

**Original Code**:
```python
if isinstance(img_obj, Image.Image):
    # This check always failed for dict-based images
```

**Fix Applied**:
```python
# Handle dict format from MinerU
if isinstance(img_obj, dict):
    # Try common key names in priority order
    for key in ['img_pil', 'image', 'img']:
        if key in img_obj:
            if isinstance(img_obj[key], Image.Image):
                pil_img = img_obj[key]
                break
```

**Result**: ✅ All 13 embedded images now extract successfully

### 2. Detected Image Regions (UPSTREAM ISSUE ⚠️)
**Problem**: MinerU's layout detection identifies 35 image regions but returns empty bounding boxes.

**Evidence**:
```
Skipping region on page 1: invalid bbox length 0, bbox=[]
Skipping region on page 2: invalid bbox length 0, bbox=[]
... (35 total regions with empty bboxes)
```

**Analysis**:
- MinerU's `doc_analyze` correctly identifies image regions (category_id 0 or 3)
- BUT the `bbox` field in `layout_dets` is empty: `[]`
- Cannot extract regions without coordinates: `[x0, y0, x1, y1]`
- This is a data quality issue from MinerU, not a service bug

**Result**: ⚠️ Detected regions cannot be extracted (MinerU data issue)

## Test Results

### Before Fix
```
Images Extracted: 0
  - Embedded images: 0
  - Detected regions: 0
```

### After Fix
```
Images Extracted: 13
  - Embedded images: 13  ✅
  - Detected regions: 0  ⚠️ (empty bboxes from MinerU)
```

## Service Behavior

The service now correctly:
1. ✅ Extracts all embedded images with valid data
2. ✅ Logs detailed warnings for invalid bboxes
3. ✅ Doesn't crash or return corrupted data
4. ✅ Provides clear diagnostic information

## Logging Added

Debug logging to track the issue:
- PDF processing stats
- Image type detection
- Dictionary key inspection
- Region extraction counters
- Bbox validation failures

## Recommendations

### For Detected Regions
1. **Check MinerU Configuration**: Verify if `doc_analyze` needs additional parameters to populate bboxes
2. **MinerU Version**: Check if this is a known issue in the current version
3. **Alternative Approaches**:
   - Use a different PDF parsing library for layout detection
   - Pre-process PDFs with a layout detection model
   - Extract full pages as images and crop using ML models

### For Production
1. Consider removing debug logging once stable
2. Add metrics for tracking extraction success rates
3. Implement fallback strategies for empty bboxes

## Files Modified

- `/Users/krishna/Projects/archon/services/mineru-mlx/app.py` (lines 290-412)
  - Added dict format handling for embedded images
  - Added comprehensive debug logging
  - Added bbox validation logging

## Commit

```
commit 68a27ff
Fix embedded image extraction - handle dict format with img_pil key
```

## Testing Command

```bash
source venv/bin/activate && python /tmp/test_image_extraction.py
```

## Service Status

- Service running on port 9006 with `--reload` flag
- Auto-reloads on code changes
- Health check: `http://localhost:9006/health`
- UI available: `http://localhost:9006/ui`
