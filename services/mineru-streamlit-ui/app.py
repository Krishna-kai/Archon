"""
MinerU Document Processing Streamlit UI

A Streamlit interface for processing documents with MinerU MLX service.
Features:
- File upload (PDF, DOCX, etc.)
- Markdown content extraction and display
- Image extraction and gallery view
- Variable extraction from markdown
- CSV export of extracted variables
"""

import base64
import io
import re
from typing import Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
from PIL import Image

# Configuration
MINERU_SERVICE_URL = "http://localhost:9006"
BACKEND_API_URL = "http://localhost:9181"

# Page config
st.set_page_config(
    page_title="MinerU Document Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .markdown-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        max-height: 600px;
        overflow-y: auto;
    }
    .image-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    .image-card {
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 0.5rem;
        background-color: white;
    }
    .stats-container {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def check_service_health(service_url: str, service_name: str) -> bool:
    """Check if a service is healthy."""
    try:
        response = requests.get(f"{service_url}/health", timeout=3)
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"{service_name} is not reachable: {str(e)}")
        return False


def process_document_with_mineru(file_bytes: bytes, filename: str) -> Optional[Dict]:
    """Process document using MinerU service."""
    try:
        # Prepare multipart form data
        files = {"file": (filename, file_bytes, "application/octet-stream")}

        with st.spinner(f"Processing {filename} with MinerU MLX..."):
            response = requests.post(
                f"{MINERU_SERVICE_URL}/process",
                files=files,
                timeout=120
            )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Processing failed: {response.text}")
            return None

    except Exception as e:
        st.error(f"Error processing document: {str(e)}")
        return None


def extract_variables_from_markdown(markdown_text: str) -> pd.DataFrame:
    """
    Extract variables from markdown content.

    Looks for patterns like:
    - **Variable Name**: value
    - Variable Name: value
    - Tables with variable/value columns
    """
    variables = []

    # Pattern 1: Bold label with value
    bold_pattern = r'\*\*([^*]+)\*\*[:\s]+([^\n]+)'
    for match in re.finditer(bold_pattern, markdown_text):
        variables.append({
            "Variable": match.group(1).strip(),
            "Value": match.group(2).strip(),
            "Source": "Bold Label"
        })

    # Pattern 2: Key: Value pairs
    key_value_pattern = r'^([A-Z][A-Za-z\s]+):\s*([^\n]+)$'
    for match in re.finditer(key_value_pattern, markdown_text, re.MULTILINE):
        key = match.group(1).strip()
        value = match.group(2).strip()
        # Avoid duplicates from bold pattern
        if not any(v["Variable"] == key for v in variables):
            variables.append({
                "Variable": key,
                "Value": value,
                "Source": "Key-Value Pair"
            })

    # Pattern 3: Markdown tables
    table_pattern = r'\|([^\n]+)\|'
    table_matches = list(re.finditer(table_pattern, markdown_text))

    if len(table_matches) > 2:  # Need at least header, separator, and one row
        # Try to extract table data
        for i in range(2, len(table_matches)):  # Skip header and separator
            cells = [cell.strip() for cell in table_matches[i].group(1).split('|')]
            if len(cells) >= 2:
                variables.append({
                    "Variable": cells[0],
                    "Value": cells[1] if len(cells) > 1 else "",
                    "Source": "Markdown Table"
                })

    return pd.DataFrame(variables) if variables else pd.DataFrame(columns=["Variable", "Value", "Source"])


def display_images(images_data: List[Dict]):
    """Display extracted images in a gallery."""
    if not images_data:
        st.info("No images were extracted from this document.")
        return

    st.markdown(f'<div class="section-header">📸 Extracted Images ({len(images_data)})</div>', unsafe_allow_html=True)

    # Display images in columns
    cols = st.columns(3)

    for idx, img_data in enumerate(images_data):
        col_idx = idx % 3
        with cols[col_idx]:
            try:
                # Decode base64 image
                img_bytes = base64.b64decode(img_data.get("base64", ""))
                img = Image.open(io.BytesIO(img_bytes))

                # Display image
                st.image(img, caption=img_data.get("name", f"Image {idx + 1}"), use_container_width=True)

                # Show image metadata
                with st.expander("Image Details"):
                    st.write(f"**Type:** {img_data.get('mime_type', 'Unknown')}")
                    st.write(f"**Page:** {img_data.get('page_number', 'N/A')}")
                    st.write(f"**Index:** {img_data.get('image_index', idx)}")
                    if img_data.get("ocr_text"):
                        st.write(f"**OCR Text:** {img_data['ocr_text']}")

            except Exception as e:
                st.error(f"Error displaying image {idx + 1}: {str(e)}")


def main():
    """Main Streamlit application."""

    # Header
    st.markdown('<div class="main-header">📄 MinerU Document Processor</div>', unsafe_allow_html=True)
    st.markdown("Upload documents to extract markdown content, images, and variables using MinerU MLX")

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        # Service status
        st.markdown("### 🔌 Service Status")
        mineru_status = check_service_health(MINERU_SERVICE_URL, "MinerU MLX")
        st.write(f"MinerU MLX: {'🟢 Online' if mineru_status else '🔴 Offline'}")

        # Processing options
        st.markdown("### 🎛️ Processing Options")
        extract_images = st.checkbox("Extract Images", value=True)
        extract_variables = st.checkbox("Extract Variables", value=True)
        show_raw_json = st.checkbox("Show Raw JSON", value=False)

        st.markdown("---")
        st.markdown("### 📚 About")
        st.markdown("""
        This UI processes documents using:
        - **MinerU MLX** for document parsing
        - **Image Extraction** from PDFs and documents
        - **Variable Detection** from structured content
        - **CSV Export** for extracted data
        """)

    # Main content area
    if not mineru_status:
        st.error("⚠️ MinerU MLX service is not available. Please start the service on port 9006.")
        st.code("cd /Users/krishna/Projects/archon/services/mineru-mlx && ./start_service.sh", language="bash")
        return

    # File upload
    st.markdown('<div class="section-header">📤 Upload Document</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a document file",
        type=["pdf", "docx", "doc", "txt", "md"],
        help="Upload PDF, Word, or text documents for processing"
    )

    if uploaded_file is not None:
        # Display file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filename", uploaded_file.name)
        with col2:
            st.metric("Size", f"{uploaded_file.size / 1024:.2f} KB")
        with col3:
            st.metric("Type", uploaded_file.type)

        # Process button
        if st.button("🚀 Process Document", type="primary"):
            # Read file bytes
            file_bytes = uploaded_file.read()

            # Process with MinerU
            result = process_document_with_mineru(file_bytes, uploaded_file.name)

            if result:
                # Store in session state
                st.session_state["processing_result"] = result
                st.session_state["filename"] = uploaded_file.name
                st.success("✅ Document processed successfully!")

    # Display results if available
    if "processing_result" in st.session_state:
        result = st.session_state["processing_result"]
        filename = st.session_state.get("filename", "document")

        # Display statistics
        st.markdown('<div class="section-header">📊 Processing Results</div>', unsafe_allow_html=True)

        markdown_content = result.get("markdown", "")
        images_data = result.get("images", [])

        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        with stats_col1:
            st.metric("Characters", len(markdown_content))
        with stats_col2:
            st.metric("Words", len(markdown_content.split()))
        with stats_col3:
            st.metric("Images", len(images_data))
        with stats_col4:
            st.metric("Pages", result.get("num_pages", "N/A"))

        # Tabs for different views
        tabs = st.tabs(["📝 Markdown", "🖼️ Images", "📊 Variables", "💾 Export", "🔍 Raw Data"])

        # Tab 1: Markdown Content
        with tabs[0]:
            st.markdown('<div class="section-header">📝 Extracted Markdown</div>', unsafe_allow_html=True)

            if markdown_content:
                # Display formatted markdown
                st.markdown('<div class="markdown-container">', unsafe_allow_html=True)
                st.markdown(markdown_content)
                st.markdown('</div>', unsafe_allow_html=True)

                # Download button
                st.download_button(
                    label="⬇️ Download Markdown",
                    data=markdown_content,
                    file_name=f"{filename.rsplit('.', 1)[0]}_extracted.md",
                    mime="text/markdown"
                )
            else:
                st.warning("No markdown content was extracted.")

        # Tab 2: Images
        with tabs[1]:
            if extract_images:
                display_images(images_data)
            else:
                st.info("Image extraction was disabled in settings.")

        # Tab 3: Variables
        with tabs[2]:
            st.markdown('<div class="section-header">📊 Extracted Variables</div>', unsafe_allow_html=True)

            if extract_variables and markdown_content:
                variables_df = extract_variables_from_markdown(markdown_content)

                if not variables_df.empty:
                    st.dataframe(
                        variables_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    # Statistics
                    st.info(f"Found {len(variables_df)} variables")
                else:
                    st.warning("No variables were detected in the markdown content.")
                    st.info("Variables are detected from patterns like '**Label**: Value' or 'Key: Value'")
            else:
                st.info("Variable extraction was disabled in settings.")

        # Tab 4: Export
        with tabs[3]:
            st.markdown('<div class="section-header">💾 Export Options</div>', unsafe_allow_html=True)

            export_col1, export_col2 = st.columns(2)

            with export_col1:
                st.markdown("#### 📄 Markdown")
                if markdown_content:
                    st.download_button(
                        label="Download Markdown (.md)",
                        data=markdown_content,
                        file_name=f"{filename.rsplit('.', 1)[0]}_content.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

            with export_col2:
                st.markdown("#### 📊 Variables CSV")
                if extract_variables and markdown_content:
                    variables_df = extract_variables_from_markdown(markdown_content)
                    if not variables_df.empty:
                        csv = variables_df.to_csv(index=False)
                        st.download_button(
                            label="Download Variables (.csv)",
                            data=csv,
                            file_name=f"{filename.rsplit('.', 1)[0]}_variables.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

            # Full JSON export
            st.markdown("#### 🗂️ Complete Data")
            import json
            json_data = json.dumps(result, indent=2)
            st.download_button(
                label="Download Full JSON",
                data=json_data,
                file_name=f"{filename.rsplit('.', 1)[0]}_full_data.json",
                mime="application/json",
                use_container_width=True
            )

        # Tab 5: Raw Data
        with tabs[4]:
            if show_raw_json:
                st.markdown('<div class="section-header">🔍 Raw JSON Response</div>', unsafe_allow_html=True)
                st.json(result)
            else:
                st.info("Enable 'Show Raw JSON' in the sidebar to view the complete API response.")


if __name__ == "__main__":
    main()
