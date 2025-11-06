# AI-Powered Structured Variable Extraction

## Overview

We've integrated local LLM-based structured data extraction into the MinerU HTML UI, allowing users to extract research paper variables directly from processed PDFs using configurable AI models.

## Features Implemented

### 1. Backend API Endpoints

#### `/models` (GET)
- Lists all available Ollama models
- Returns: `{success: true, models: [...]}`

#### `/extract-structured` (POST)
- Extracts structured variables from text
- Request body:
```json
{
  "text": "paper content...",
  "model": "qwen2.5-coder:7b"
}
```
- Response:
```json
{
  "success": true,
  "data": {
    "dataset": "...",
    "tissue_type": "...",
    // ... 14 fields total
  },
  "model": "qwen2.5-coder:7b",
  "processing_time": 15.3
}
```

### 2. UI Components

#### Model Selection Dropdown
- Automatically loads available Ollama models on page load
- Pre-selects `qwen2.5-coder:7b` if available (best for structured extraction)
- Styled to match MinerU UI theme

#### Extract Variables Button
- Triggers structured extraction using selected model
- Shows loading state during processing
- Displays status messages with processing time

#### Extracted Variables Tab
- New tab in results section: "🎯 Extracted"
- Displays extracted data in a structured table format
- Shows which model was used for extraction
- Download options: JSON and CSV

### 3. Extracted Variables

The system extracts 14 research paper variables:

1. **Dataset(s)** - Datasets used in the research
2. **Tissue Type(s)** - Types of tissue analyzed
3. **Input Format** - Format of input data
4. **Method** - Primary method/model name
5. **Family** - Architecture family (e.g., U-Net, CNN)
6. **Architecture** - Specific architecture name
7. **Innovation** - Key innovation or contribution
8. **Type** - Approach type (supervised, unsupervised, etc.)
9. **Metric(s)** - Evaluation metrics used
10. **Metric Used?** - Primary metric reported
11. **Performance** - Key performance numbers
12. **Limitations** - Mentioned limitations
13. **Future Work** - Suggested future research
14. **Notes** - Additional important information

## Usage Workflow

1. **Upload and Process PDF**
   - Upload research paper via UI
   - Wait for MinerU processing to complete
   - Results display as usual (markdown, images, stats)

2. **Configure Model**
   - Extraction controls appear after processing
   - Select desired Ollama model from dropdown
   - Available models:
     - `qwen2.5-coder:7b` (recommended for structured tasks)
     - `qwen3:8b` (general purpose)
     - `deepseek-r1:7b` (reasoning, may be verbose)
     - `llama3.2-vision:11b` (vision capabilities)

3. **Extract Variables**
   - Click "Extract Variables" button
   - Wait 30-60 seconds for LLM processing
   - System displays progress and model being used

4. **View Results**
   - Automatically switches to "Extracted" tab
   - Shows all 14 variables in table format
   - N/A shown for missing values

5. **Export Data**
   - Download as JSON (structured format)
   - Download as CSV (for spreadsheet analysis)

## Technical Details

### Model Recommendations

**Best for Structured Extraction:**
- `qwen2.5-coder:7b` - Fastest, most reliable for JSON generation
- `qwen3:8b` - Good balance of speed and accuracy

**Alternative:**
- `deepseek-r1:7b` - More detailed but slower, may include reasoning

### Processing Time

- Model loading: ~2-5 seconds (on first call)
- Extraction: 15-60 seconds depending on:
  - Model size
  - Content length (uses first 10,000 chars)
  - System resources

### Error Handling

The system handles:
- Missing models gracefully
- Timeout after 120 seconds
- JSON parsing errors from LLM responses
- Network failures

### UI Integration

- Extraction controls hidden until PDF is processed
- Model dropdown populated dynamically from `/models` endpoint
- Real-time status updates during extraction
- Seamless tab navigation
- Consistent styling with existing UI theme

## File Modifications

### `app.py`
- Added imports: `json`, `re`, `subprocess`
- Added `ExtractRequest` and `ExtractResponse` Pydantic models
- Added `/extract-structured` POST endpoint
- Added `/models` GET endpoint
- Integrated Ollama via subprocess calls

### `mineru_ui.html`
- Added extraction controls section (after stats, before tabs)
- Added "Extracted" tab button and content
- Added JavaScript variables: `availableModels`, `extractedVariables`
- Added functions:
  - `loadModels()` - Fetch and populate model dropdown
  - `extractStructuredData()` - Call extraction API
  - `displayExtractedVariables()` - Render results table
  - `downloadExtractedJSON()` - Export to JSON
  - `downloadExtractedCSV()` - Export to CSV
- Updated `displayResults()` to show extraction controls

## Testing

### Manual Test Steps

1. Open http://localhost:9006/ui
2. Upload a research paper PDF
3. Wait for processing to complete
4. Verify extraction controls appear
5. Check model dropdown has models loaded
6. Select a model and click "Extract Variables"
7. Wait for extraction (check status messages)
8. Verify "Extracted" tab shows results
9. Test JSON and CSV downloads

### API Test

```bash
# List models
curl http://localhost:9006/models

# Extract variables (after processing a PDF)
curl -X POST http://localhost:9006/extract-structured \
  -H "Content-Type: application/json" \
  -d '{"text": "sample text...", "model": "qwen2.5-coder:7b"}'
```

## Future Enhancements

### Potential Improvements

1. **Batch Processing**
   - Extract from multiple PDFs at once
   - Compare extraction results across papers

2. **Model Comparison**
   - Run extraction with multiple models simultaneously
   - Show differences in extracted values
   - Confidence scoring

3. **Custom Fields**
   - Allow users to define custom extraction fields
   - Save field templates for reuse

4. **Archon Integration**
   - Automatically save to Archon knowledge base
   - Link extracted papers to projects
   - Track research paper library

5. **Validation**
   - Cross-reference extracted values
   - Flag inconsistencies or missing data
   - Suggest corrections

6. **History**
   - Save extraction history
   - Compare multiple versions
   - Track which models performed best

## Known Limitations

1. **Context Window**
   - Currently uses first 10,000 characters
   - May miss information from later pages
   - Could be improved with chunking strategy

2. **Model Availability**
   - Requires Ollama models to be pre-installed
   - No automatic model download
   - Must be running locally

3. **Extraction Accuracy**
   - Depends on paper structure and clarity
   - May miss specialized terminology
   - Works best with standard research paper format

4. **Performance**
   - Extraction takes 30-60 seconds
   - No background processing (blocks UI)
   - Could benefit from async/streaming

## Dependencies

- **Backend**: FastAPI, subprocess, Ollama
- **Frontend**: Vanilla JavaScript (no framework)
- **Models**: Any Ollama-compatible LLM

## Service Status

- ✅ MinerU Service: Running on port 9006
- ✅ Backend API: Both endpoints operational
- ✅ HTML UI: Fully integrated with extraction features
- ✅ Ollama: 5 models available locally

## Documentation Files

- `UI_FIX_SUMMARY.md` - Original UI field name fix
- `EXTRACTION_FEATURE_SUMMARY.md` - This document
- `SESSION_REPORT_2025-11-06.md` - Previous session work

---

**Last Updated**: 2025-11-06
**Version**: 2.1.0 (added AI extraction features)
