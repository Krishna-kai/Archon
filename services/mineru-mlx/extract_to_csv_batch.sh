#!/bin/bash
#
# Extract data from PDF research papers using hierarchical template
# and output to 21-column CSV format
#
# Usage:
#   ./extract_to_csv_batch.sh /path/to/papers/ output.csv
#   ./extract_to_csv_batch.sh single_paper.pdf output.csv
#

set -e  # Exit on error

# Check arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <pdf_file_or_directory> <output_csv>"
    echo ""
    echo "Examples:"
    echo "  $0 paper.pdf results.csv              # Single PDF"
    echo "  $0 /path/to/papers/ results.csv       # All PDFs in directory"
    exit 1
fi

INPUT_PATH="$1"
OUTPUT_CSV="$2"
SERVICE_URL="http://localhost:9006"
TEMPLATE_ID="histopathology_research_hierarchical"
MODEL="qwen2.5-coder:7b"
TIMEOUT=180
TEMP_DIR="/tmp/extraction_results_$$"

# Create temp directory for JSON results
mkdir -p "$TEMP_DIR"

echo "=========================================================================="
echo "📊 BATCH PDF EXTRACTION TO CSV"
echo "=========================================================================="
echo "Input: $INPUT_PATH"
echo "Output: $OUTPUT_CSV"
echo "Template: $TEMPLATE_ID (hierarchical - 6 groups, 21 variables)"
echo "Model: $MODEL"
echo ""

# Function to process a single PDF
process_pdf() {
    local pdf_path="$1"
    local pdf_name=$(basename "$pdf_path")
    local json_output="$TEMP_DIR/${pdf_name%.pdf}.json"

    echo "📄 Processing: $pdf_name"

    # Step 1: Convert PDF to markdown
    echo "   [1/3] Converting PDF to markdown..."
    PROCESS_RESPONSE=$(curl -s -X POST "$SERVICE_URL/process" \
        -F "file=@$pdf_path" \
        -F "extract_images=false")

    MARKDOWN=$(echo "$PROCESS_RESPONSE" | jq -r '.text')
    TEXT_LENGTH=$(echo "$MARKDOWN" | wc -c | tr -d ' ')
    echo "   ✅ Extracted $TEXT_LENGTH characters"

    # Step 2: Extract structured data with hierarchical template
    echo "   [2/3] Extracting structured data..."
    EXTRACTION_REQUEST=$(jq -n \
        --arg text "$MARKDOWN" \
        --arg template "$TEMPLATE_ID" \
        --arg model "$MODEL" \
        --argjson timeout "$TIMEOUT" \
        '{text: $text, template_id: $template, model: $model, timeout: $timeout}')

    EXTRACTION_RESPONSE=$(curl -s -X POST "$SERVICE_URL/extract-structured" \
        -H "Content-Type: application/json" \
        -d "$EXTRACTION_REQUEST")

    # Save extraction result
    echo "$EXTRACTION_RESPONSE" | jq '.' > "$json_output"

    SUCCESS=$(echo "$EXTRACTION_RESPONSE" | jq -r '.success')
    PROCESSING_TIME=$(echo "$EXTRACTION_RESPONSE" | jq -r '.processing_time // 0')

    if [ "$SUCCESS" = "true" ]; then
        echo "   ✅ Extraction succeeded in ${PROCESSING_TIME}s"

        # Count non-null values
        NULL_COUNT=$(echo "$EXTRACTION_RESPONSE" | jq '[.data | .. | select(. == null)] | length')
        TOTAL_FIELDS=21
        EXTRACTED=$((TOTAL_FIELDS - NULL_COUNT))
        echo "   📊 Extracted: $EXTRACTED/$TOTAL_FIELDS fields"
    else
        ERROR=$(echo "$EXTRACTION_RESPONSE" | jq -r '.error')
        echo "   ❌ Extraction failed: $ERROR"
        return 1
    fi

    echo ""
}

# Collect PDF files
if [ -f "$INPUT_PATH" ]; then
    # Single PDF file
    PDF_FILES=("$INPUT_PATH")
elif [ -d "$INPUT_PATH" ]; then
    # Directory of PDFs
    mapfile -t PDF_FILES < <(find "$INPUT_PATH" -name "*.pdf" -type f)
else
    echo "❌ Error: $INPUT_PATH is not a file or directory"
    exit 1
fi

if [ ${#PDF_FILES[@]} -eq 0 ]; then
    echo "❌ No PDF files found"
    exit 1
fi

echo "Found ${#PDF_FILES[@]} PDF file(s) to process"
echo ""

# Process all PDFs
SUCCESSFUL=0
FAILED=0

for pdf in "${PDF_FILES[@]}"; do
    if process_pdf "$pdf"; then
        ((SUCCESSFUL++))
    else
        ((FAILED++))
    fi
done

echo "=========================================================================="
echo "📈 EXTRACTION SUMMARY"
echo "=========================================================================="
echo "Total PDFs: ${#PDF_FILES[@]}"
echo "Successful: $SUCCESSFUL"
echo "Failed: $FAILED"
echo ""

if [ $SUCCESSFUL -eq 0 ]; then
    echo "❌ No successful extractions to convert to CSV"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Step 3: Convert all JSON results to single CSV
echo "=========================================================================="
echo "[3/3] Converting hierarchical results to 21-column CSV..."
echo "=========================================================================="

source venv/bin/activate
python flatten_to_csv.py "$TEMP_DIR" -o "$OUTPUT_CSV"

echo ""
echo "✅ BATCH PROCESSING COMPLETE!"
echo "   Output CSV: $OUTPUT_CSV"
echo "   Columns: 21 (Paper_ID, Title, Authors, Year, Venue, DOI, ...)"
echo "   Rows: $SUCCESSFUL"
echo ""

# Cleanup
rm -rf "$TEMP_DIR"

echo "Preview of results:"
head -2 "$OUTPUT_CSV"
