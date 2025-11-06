# MinerU Debug Findings - 2025-01-06

## Root Cause Identified

The MinerU integration is failing because of a **fundamental misunderstanding of the MinerU data structure**.

### Expected vs Actual Structure

**Expected structure (from documentation):**
```python
layout_dets = [
    {
        'category_type': 'text',
        'text': 'Hello World Test',
        'bbox': [x1, y1, x2, y2]
    }
]
```

**Actual structure (confirmed via debug logging):**
```python
layout_dets = [
    {
        'category_id': 2,
        'poly': [136, 226, 389, 226, 389, 263, 136, 263],
        'score': 0.426
    }
]
```

### Key Findings

1. **layout_dets has NO text field**
   - Only contains visual detection metadata: `category_id`, `poly` (coordinates), `score` (confidence)
   - Cannot be used for text extraction as currently implemented

2. **page_result only has 2 keys**
   - `layout_dets`: Visual detections (no text)
   - `page_info`: Page metadata (width, height, page_no)
   - No additional keys with text content

3. **Text is stored elsewhere**
   - The `all_pdf_docs` from `doc_analyze` contains a `pypdfium2.PdfDocument` object
   - This object has the actual PDF text accessible via PyPDFium2 API
   - Current code never uses this object

### Debug Output Samples

```
DEBUG: MinerU Processing Results
================================================================================
Number of PDFs processed: 1
all_pdf_docs type: <class 'list'>, length: 1
First PDF doc type: <class 'pypdfium2._helpers.document.PdfDocument'>
Pages in PDF: 1
Images extracted: 1

Page 1 FULL page_result keys: ['layout_dets', 'page_info']

Page 1 layout_dets structure:
  layout_dets count: 4
  First detection keys: ['category_id', 'poly', 'score']
  First detection type: <class 'dict'>
  First detection sample: {'category_id': 2, 'poly': [136, 226, 389, 226, 389, 263, 136, 263], 'score': 0.426}
Total detections across all pages: 4
================================================================================
```

## The Fix

**Current broken code:**
```python
# python/src/mineru_service/main.py:134-140
for det in layout_dets:
    det_type = det.get('category_type', 'text')  # Returns 'text' (no field exists)
    det_text = det.get('text', '')                # Returns '' (no field exists)

    if det_text:  # Always False!
        text_parts.append(f"{det_text}\n")
```

**Required fix:**
```python
# Extract text from PdfDocument object instead
pdf_doc = all_pdf_docs[0]
for page_idx in range(len(pdf_doc)):
    page = pdf_doc[page_idx]
    textpage = page.get_textpage()
    page_text = textpage.get_text_bounded()  # Or similar PyPDFium2 method
    text_parts.append(page_text)
```

## Impact

- **Current behavior**: Only 172 chars extracted (99.91% loss)
- **Expected behavior**: Full document text extraction (~200,000 chars for test PDF)
- **Formulas**: 0 extracted (should be 93)
- **Tables**: 0 extracted (should be 6)

## Next Steps

1. Replace layout_dets text extraction with PdfDocument text extraction
2. Use layout_dets for structure/formatting hints (category_id values)
3. Correlate visual detections with extracted text for proper markdown formatting
4. Add formula and table extraction from MinerU's specialized processors

## Files Involved

- `/Users/krishna/Projects/archon/python/src/mineru_service/main.py:106-146` - Text extraction loop (BROKEN)
- `/Users/krishna/Projects/archon/python/src/server/services/mineru_http_client.py:71` - Consumes the broken output
