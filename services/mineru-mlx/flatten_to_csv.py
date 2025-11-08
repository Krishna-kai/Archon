"""
Flatten hierarchical extraction results to 21-column CSV format.

This script takes hierarchical extraction results and converts them back to
the original 21-column CSV format used in mahinda_papers_extracted_data.csv
"""
import json
import csv
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def flatten_hierarchical_result(hierarchical_data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Flatten hierarchical extraction result to match original 21-column CSV.

    Args:
        hierarchical_data: Extraction result with nested groups

    Returns:
        Flat dictionary with 21 CSV column names as keys
    """
    # Extract nested data with safe fallbacks
    publication = hierarchical_data.get("publication", {}) or {}
    methodology = hierarchical_data.get("methodology", {}) or {}
    architecture = hierarchical_data.get("architecture", {}) or {}
    evaluation = hierarchical_data.get("evaluation", {}) or {}
    discussion = hierarchical_data.get("discussion", {}) or {}

    # Map to original 21 CSV columns (exact column names)
    flat_data = {
        "Paper_ID": publication.get("paper_id"),
        "Title": publication.get("title"),
        "Authors": publication.get("authors"),
        "Year": publication.get("year"),
        "Venue": publication.get("venue"),
        "DOI": publication.get("doi"),
        "Dataset": methodology.get("dataset"),
        "Tissue_Type": methodology.get("tissue_type"),
        "Stain_Normalization": methodology.get("stain_normalization"),
        "Supervision_Type": methodology.get("supervision_type"),
        "Architecture_Family": architecture.get("architecture_family"),
        "Core_Architecture": architecture.get("core_architecture"),
        "Key_Innovation": architecture.get("key_innovation"),
        "Primary_Metrics": evaluation.get("primary_metrics"),
        "Object_Level_Metric": evaluation.get("object_level_metric"),
        "Performance": evaluation.get("performance"),
        "Cross_Dataset_Tested": evaluation.get("cross_dataset_tested"),
        "Limitations": discussion.get("limitations"),
        "Future_Work": discussion.get("future_work"),
        "Clinical_Application": discussion.get("clinical_application"),
        "Notes": hierarchical_data.get("notes")
    }

    return flat_data


def process_json_file(json_path: Path, output_csv: Path, append: bool = False):
    """
    Process a single JSON extraction result and write to CSV.

    Args:
        json_path: Path to hierarchical extraction JSON result
        output_csv: Path to output CSV file
        append: If True, append to existing CSV. If False, create new.
    """
    # Read hierarchical result
    with open(json_path, 'r') as f:
        result = json.load(f)

    if not result.get("success"):
        print(f"❌ Extraction failed: {result.get('error')}")
        return

    # Flatten to 21 columns
    flat_data = flatten_hierarchical_result(result["data"])

    # CSV column order (matches original)
    columns = [
        "Paper_ID", "Title", "Authors", "Year", "Venue", "DOI",
        "Dataset", "Tissue_Type", "Stain_Normalization", "Supervision_Type",
        "Architecture_Family", "Core_Architecture", "Key_Innovation",
        "Primary_Metrics", "Object_Level_Metric", "Performance", "Cross_Dataset_Tested",
        "Limitations", "Future_Work", "Clinical_Application", "Notes"
    ]

    # Write to CSV
    mode = 'a' if append else 'w'
    file_exists = output_csv.exists()

    with open(output_csv, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)

        # Write header only if new file or not appending to existing
        if not append or not file_exists:
            writer.writeheader()

        writer.writerow(flat_data)

    print(f"✅ Flattened result written to: {output_csv}")


def batch_process_directory(json_dir: Path, output_csv: Path):
    """
    Process all JSON files in a directory and append to single CSV.

    Args:
        json_dir: Directory containing JSON extraction results
        output_csv: Path to output CSV file
    """
    json_files = list(json_dir.glob("*.json"))

    if not json_files:
        print(f"⚠️ No JSON files found in {json_dir}")
        return

    print(f"📊 Processing {len(json_files)} JSON files...")

    for i, json_path in enumerate(json_files):
        print(f"\n[{i+1}/{len(json_files)}] Processing: {json_path.name}")
        try:
            process_json_file(json_path, output_csv, append=(i > 0))
        except Exception as e:
            print(f"❌ Error processing {json_path.name}: {e}")

    print(f"\n✅ Batch processing complete!")
    print(f"📄 Output CSV: {output_csv}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Flatten hierarchical extraction results to 21-column CSV"
    )
    parser.add_argument(
        "input",
        help="Path to JSON file or directory containing JSON files"
    )
    parser.add_argument(
        "-o", "--output",
        default="extracted_data.csv",
        help="Output CSV file path (default: extracted_data.csv)"
    )
    parser.add_argument(
        "-a", "--append",
        action="store_true",
        help="Append to existing CSV file"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_csv = Path(args.output)

    if not input_path.exists():
        print(f"❌ Input path not found: {input_path}")
        sys.exit(1)

    if input_path.is_file():
        # Process single file
        process_json_file(input_path, output_csv, append=args.append)
    elif input_path.is_dir():
        # Batch process directory
        batch_process_directory(input_path, output_csv)
    else:
        print(f"❌ Invalid input path: {input_path}")
        sys.exit(1)
