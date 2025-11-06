# Parser Service Architecture Design

## Executive Summary

The Parser Service transforms unstructured markdown output from Marker into structured, queryable JSON documents optimized for downstream applications (meta-analysis, knowledge graphs, LLM training data, data pipelines).

**Design Philosophy**: Extract once, query many times. Create a comprehensive structured representation that enables diverse downstream use cases without re-parsing.

## Service Overview

### Purpose
Convert Marker's markdown output (with LaTeX formulas and table structures) into structured JSON documents with:
- Rich metadata extraction (authors, affiliations, keywords, abstract)
- Hierarchical section structure with nested formulas and tables
- Parsed citation graph with relationships
- Extracted figures with captions and references
- Methodology extraction for reproducibility
- Statistical data extraction from tables

### Technology Stack
- **Runtime**: Python 3.12 with FastAPI
- **Parsing**: Custom regex + spaCy NLP + sympy (formula parsing)
- **Port**: 7001
- **Profile**: `advanced-ocr` (same as Marker)
- **Dependencies**: Marker service (port 7000)

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Applications                          │
│  (Frontend UI, CLI, Jupyter, Data Pipelines, LLM Training)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Archon Server (Port 8181)                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │              Document Upload & Orchestration                │    │
│  │  • Receives PDF                                             │    │
│  │  • Routes to Marker for OCR                                 │    │
│  │  • Routes to Parser for structuring                         │    │
│  │  • Stores results in Supabase                               │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────┬───────────────────────────┬───────────────────────────────┘
          │                           │
          │ POST /convert             │ POST /parse
          ▼                           ▼
┌──────────────────────┐    ┌──────────────────────────────────────┐
│   Marker Service     │    │      Parser Service (Port 7001)      │
│    (Port 7000)       │───▶│  ┌────────────────────────────────┐  │
│                      │    │  │  Parsing Pipeline              │  │
│  • PDF → Markdown    │    │  │  1. Metadata Extraction        │  │
│  • LaTeX formulas    │    │  │  2. Section Parsing            │  │
│  • Table structure   │    │  │  3. Citation Extraction        │  │
│  • Image extraction  │    │  │  4. Formula Parsing            │  │
│                      │    │  │  5. Table Data Extraction      │  │
│                      │    │  │  6. Figure Caption Linking     │  │
│                      │    │  │  7. Methods Extraction         │  │
│                      │    │  └────────────────────────────────┘  │
└──────────────────────┘    └──────────┬───────────────────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────────┐
                          │  Supabase PostgreSQL        │
                          │  ┌────────────────────────┐ │
                          │  │  parsed_papers table   │ │
                          │  │  (JSONB + relations)   │ │
                          │  └────────────────────────┘ │
                          │  ┌────────────────────────┐ │
                          │  │  paper_formulas table  │ │
                          │  │  (searchable formulas) │ │
                          │  └────────────────────────┘ │
                          │  ┌────────────────────────┐ │
                          │  │  paper_citations table │ │
                          │  │  (citation graph)      │ │
                          │  └────────────────────────┘ │
                          │  ┌────────────────────────┐ │
                          │  │  paper_tables table    │ │
                          │  │  (structured data)     │ │
                          │  └────────────────────────┘ │
                          └─────────────────────────────┘
```

## API Endpoints

### Core Parsing Endpoint

#### POST `/parse-paper`
**Purpose**: Main entry point - parse complete markdown into structured document

**Request**:
```json
{
  "markdown": "# Title\n\n## Authors...",
  "metadata": {
    "filename": "paper.pdf",
    "source": "marker",
    "page_count": 15
  },
  "options": {
    "extract_formulas": true,
    "extract_tables": true,
    "extract_citations": true,
    "extract_figures": true,
    "extract_methods": true,
    "parse_table_data": true
  }
}
```

**Response**:
```json
{
  "success": true,
  "paper_id": "550e8400-e29b-41d4-a716-446655440000",
  "parsing_stats": {
    "sections_found": 8,
    "formulas_extracted": 42,
    "tables_extracted": 5,
    "citations_found": 78,
    "figures_found": 12,
    "methods_sections": 2
  },
  "structured_document": { /* See JSON Schema below */ },
  "warnings": [
    "Table 3 has irregular column count - manual review recommended"
  ]
}
```

### Specialized Extraction Endpoints

#### POST `/extract-formulas`
**Purpose**: Extract and parse mathematical formulas from markdown

**Request**:
```json
{
  "markdown": "...",
  "options": {
    "parse_latex": true,
    "extract_variables": true,
    "identify_equation_types": true
  }
}
```

**Response**:
```json
{
  "formulas": [
    {
      "formula_id": "eq_1",
      "latex": "\\frac{\\partial u}{\\partial t} = \\alpha \\nabla^2 u",
      "location": {
        "section": "Theory",
        "line_number": 142
      },
      "variables": ["u", "t", "α"],
      "equation_type": "partial_differential",
      "numbered": true,
      "label": "eq:heat_diffusion"
    }
  ]
}
```

#### POST `/extract-tables`
**Purpose**: Extract and parse table structures with data

**Request**:
```json
{
  "markdown": "...",
  "options": {
    "parse_headers": true,
    "detect_data_types": true,
    "extract_statistics": true
  }
}
```

**Response**:
```json
{
  "tables": [
    {
      "table_id": "table_1",
      "caption": "Performance comparison across methods",
      "location": {
        "section": "Results",
        "line_number": 287
      },
      "structure": {
        "rows": 8,
        "columns": 5,
        "headers": ["Method", "Accuracy", "Precision", "Recall", "F1-Score"]
      },
      "data": [
        {"Method": "CNN", "Accuracy": 0.92, "Precision": 0.89, "Recall": 0.91, "F1-Score": 0.90},
        {"Method": "ResNet", "Accuracy": 0.95, "Precision": 0.93, "Recall": 0.94, "F1-Score": 0.93}
      ],
      "statistics": {
        "summary": "ResNet outperforms CNN by 3.3% accuracy",
        "best_performer": "ResNet",
        "metrics": ["accuracy", "precision", "recall", "f1_score"]
      }
    }
  ]
}
```

#### POST `/extract-citations`
**Purpose**: Parse citations and build citation graph

**Request**:
```json
{
  "markdown": "...",
  "options": {
    "detect_inline_citations": true,
    "parse_bibliography": true,
    "build_citation_graph": true
  }
}
```

**Response**:
```json
{
  "citations": [
    {
      "citation_id": "ref_1",
      "authors": ["Smith, J.", "Doe, A."],
      "title": "Deep Learning for Image Segmentation",
      "year": 2020,
      "venue": "CVPR",
      "citation_count_in_paper": 3,
      "locations": ["Introduction:45", "Methods:102", "Discussion:312"]
    }
  ],
  "citation_graph": {
    "nodes": 78,
    "edges": 142,
    "most_cited": ["ref_12", "ref_3", "ref_27"]
  }
}
```

#### POST `/extract-methods`
**Purpose**: Extract methodology sections and experimental setup

**Request**:
```json
{
  "markdown": "...",
  "options": {
    "extract_datasets": true,
    "extract_hyperparameters": true,
    "extract_evaluation_metrics": true
  }
}
```

**Response**:
```json
{
  "methods": {
    "datasets": [
      {
        "name": "ImageNet",
        "size": "1.2M images",
        "split": {"train": 0.8, "val": 0.1, "test": 0.1}
      }
    ],
    "hyperparameters": {
      "learning_rate": 0.001,
      "batch_size": 32,
      "epochs": 100,
      "optimizer": "Adam"
    },
    "evaluation_metrics": ["accuracy", "F1-score", "precision", "recall"],
    "experimental_setup": {
      "hardware": "NVIDIA V100 GPU",
      "framework": "PyTorch 1.9",
      "training_time": "48 hours"
    }
  }
}
```

#### GET `/health`
**Purpose**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "service": "parser",
  "dependencies": {
    "marker_service": "reachable",
    "supabase": "connected"
  }
}
```

## JSON Schema Definition

### Complete Structured Paper Document

```json
{
  "paper_id": "uuid-v4",
  "source_metadata": {
    "filename": "paper.pdf",
    "uploaded_at": "2025-01-06T12:00:00Z",
    "page_count": 15,
    "word_count": 8542,
    "parsing_service": "parser-v1.0",
    "marker_version": "marker-pdf-1.0"
  },

  "metadata": {
    "title": "Cell Nucleus Segmentation in Color Histopathological Imagery Using Convolutional Networks",
    "authors": [
      {
        "name": "John Doe",
        "affiliation": "University of Example",
        "email": "jdoe@example.edu",
        "position": 1
      }
    ],
    "abstract": "Full abstract text...",
    "keywords": ["deep learning", "histopathology", "segmentation", "CNN"],
    "publication_info": {
      "venue": "Medical Image Analysis",
      "year": 2023,
      "volume": 42,
      "issue": 3,
      "pages": "123-145",
      "doi": "10.1234/mia.2023.123"
    },
    "dates": {
      "submitted": "2022-08-15",
      "accepted": "2023-01-10",
      "published": "2023-03-01"
    }
  },

  "structure": {
    "sections": [
      {
        "section_id": "sec_1",
        "title": "Introduction",
        "level": 1,
        "order": 1,
        "content": "Full section text...",
        "word_count": 842,
        "subsections": [],
        "formulas": ["eq_1", "eq_2"],
        "tables": [],
        "figures": ["fig_1"],
        "citations": ["ref_1", "ref_3", "ref_12"]
      },
      {
        "section_id": "sec_2",
        "title": "Related Work",
        "level": 1,
        "order": 2,
        "content": "...",
        "subsections": [
          {
            "section_id": "sec_2_1",
            "title": "Deep Learning Approaches",
            "level": 2,
            "order": 1,
            "content": "...",
            "formulas": [],
            "tables": [],
            "figures": [],
            "citations": ["ref_4", "ref_5", "ref_7"]
          }
        ]
      }
    ]
  },

  "formulas": [
    {
      "formula_id": "eq_1",
      "latex": "\\mathcal{L} = -\\sum_{i=1}^{N} y_i \\log(\\hat{y}_i)",
      "section_id": "sec_3",
      "context": "We minimize the cross-entropy loss:",
      "variables": ["L", "N", "y_i", "ŷ_i"],
      "equation_type": "optimization",
      "numbered": true,
      "label": "eq:loss_function",
      "line_number": 287
    }
  ],

  "tables": [
    {
      "table_id": "table_1",
      "caption": "Performance comparison of segmentation methods",
      "section_id": "sec_4",
      "structure": {
        "rows": 6,
        "columns": 5,
        "headers": ["Method", "Dice Score", "IoU", "Precision", "Recall"]
      },
      "data": [
        {
          "Method": "U-Net",
          "Dice Score": 0.87,
          "IoU": 0.78,
          "Precision": 0.89,
          "Recall": 0.86
        },
        {
          "Method": "Proposed Method",
          "Dice Score": 0.92,
          "IoU": 0.85,
          "Precision": 0.93,
          "Recall": 0.91
        }
      ],
      "statistics": {
        "best_method": "Proposed Method",
        "improvement_over_baseline": "5.7% Dice Score",
        "statistical_significance": "p < 0.001"
      },
      "line_number": 412
    }
  ],

  "figures": [
    {
      "figure_id": "fig_1",
      "caption": "Architecture of the proposed convolutional network",
      "section_id": "sec_3",
      "file_reference": "figure_1.png",
      "mentions": ["sec_1:45", "sec_3:287", "sec_5:512"],
      "description": "Network architecture showing encoder-decoder structure with skip connections",
      "line_number": 298
    }
  ],

  "citations": [
    {
      "citation_id": "ref_1",
      "authors": ["Smith, J.", "Doe, A.", "Brown, K."],
      "title": "Deep Learning for Medical Image Segmentation: A Survey",
      "year": 2020,
      "venue": "Medical Image Analysis",
      "volume": 58,
      "pages": "101-125",
      "doi": "10.1016/j.media.2020.101",
      "citation_type": "journal",
      "inline_citations": 5,
      "locations": ["sec_1:45", "sec_2:102", "sec_2:156", "sec_4:312", "sec_6:789"]
    }
  ],

  "methods": {
    "datasets": [
      {
        "name": "CoNSeP",
        "description": "Colorectal Nuclear Segmentation and Phenotypes",
        "size": "24,319 nuclei annotations",
        "split": {
          "train": 16000,
          "validation": 4000,
          "test": 4319
        },
        "preprocessing": ["normalization", "augmentation", "color standardization"]
      }
    ],
    "model_architecture": {
      "type": "U-Net variant",
      "encoder": "ResNet-50",
      "decoder_layers": 4,
      "skip_connections": true,
      "output_channels": 3
    },
    "training": {
      "optimizer": "Adam",
      "learning_rate": 0.0001,
      "batch_size": 16,
      "epochs": 200,
      "loss_function": "Dice Loss + Cross Entropy",
      "early_stopping": {
        "patience": 20,
        "monitor": "validation_dice"
      }
    },
    "evaluation": {
      "metrics": ["Dice Score", "IoU", "Precision", "Recall", "F1-Score"],
      "cross_validation": "5-fold",
      "statistical_tests": ["paired t-test", "Wilcoxon signed-rank"]
    },
    "implementation": {
      "framework": "PyTorch 1.9",
      "hardware": "NVIDIA RTX 3090 (24GB)",
      "training_time": "36 hours",
      "inference_time": "0.15s per image"
    }
  },

  "key_findings": {
    "contributions": [
      "Novel architecture combining residual connections with attention mechanisms",
      "5.7% improvement in Dice score over state-of-the-art",
      "Real-time inference capability for clinical deployment"
    ],
    "limitations": [
      "Limited to H&E stained images",
      "Requires manual quality control for edge cases"
    ],
    "future_work": [
      "Extension to multi-stain imagery",
      "Integration with clinical diagnosis pipeline"
    ]
  }
}
```

## Integration with Archon

### Database Schema Extensions

#### New Table: `parsed_papers`
```sql
CREATE TABLE parsed_papers (
    paper_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    -- Complete structured document (JSONB for flexibility)
    structured_data JSONB NOT NULL,

    -- Indexed fields for fast queries
    title TEXT,
    authors TEXT[],
    keywords TEXT[],
    publication_year INTEGER,
    venue TEXT,

    -- Counts for quick stats
    formula_count INTEGER DEFAULT 0,
    table_count INTEGER DEFAULT 0,
    citation_count INTEGER DEFAULT 0,
    figure_count INTEGER DEFAULT 0,

    -- Timestamps
    parsed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            COALESCE(title, '') || ' ' ||
            COALESCE(array_to_string(keywords, ' '), '')
        )
    ) STORED,

    CONSTRAINT valid_structured_data CHECK (
        structured_data ? 'paper_id' AND
        structured_data ? 'metadata' AND
        structured_data ? 'structure'
    )
);

-- Indexes
CREATE INDEX idx_parsed_papers_source ON parsed_papers(source_document_id);
CREATE INDEX idx_parsed_papers_title ON parsed_papers USING gin(to_tsvector('english', title));
CREATE INDEX idx_parsed_papers_authors ON parsed_papers USING gin(authors);
CREATE INDEX idx_parsed_papers_keywords ON parsed_papers USING gin(keywords);
CREATE INDEX idx_parsed_papers_year ON parsed_papers(publication_year);
CREATE INDEX idx_parsed_papers_search ON parsed_papers USING gin(search_vector);
CREATE INDEX idx_parsed_papers_structured ON parsed_papers USING gin(structured_data);
```

#### New Table: `paper_formulas`
```sql
CREATE TABLE paper_formulas (
    formula_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES parsed_papers(paper_id) ON DELETE CASCADE,

    latex TEXT NOT NULL,
    variables TEXT[],
    equation_type TEXT,
    section_id TEXT,
    line_number INTEGER,

    -- For searching formulas
    latex_normalized TEXT, -- Normalized LaTeX for matching

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_formulas_paper ON paper_formulas(paper_id);
CREATE INDEX idx_formulas_type ON paper_formulas(equation_type);
CREATE INDEX idx_formulas_variables ON paper_formulas USING gin(variables);
CREATE INDEX idx_formulas_latex ON paper_formulas USING gin(to_tsvector('simple', latex));
```

#### New Table: `paper_citations`
```sql
CREATE TABLE paper_citations (
    citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES parsed_papers(paper_id) ON DELETE CASCADE,

    cited_paper_title TEXT NOT NULL,
    cited_authors TEXT[],
    cited_year INTEGER,
    venue TEXT,
    doi TEXT,

    -- Citation context
    citation_count INTEGER DEFAULT 1, -- Times cited in this paper
    locations TEXT[], -- Section IDs where cited

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_citations_paper ON paper_citations(paper_id);
CREATE INDEX idx_citations_title ON paper_citations(cited_paper_title);
CREATE INDEX idx_citations_authors ON paper_citations USING gin(cited_authors);
CREATE INDEX idx_citations_year ON paper_citations(cited_year);
CREATE INDEX idx_citations_doi ON paper_citations(doi) WHERE doi IS NOT NULL;
```

#### New Table: `paper_tables`
```sql
CREATE TABLE paper_tables (
    table_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES parsed_papers(paper_id) ON DELETE CASCADE,

    caption TEXT,
    section_id TEXT,

    -- Structure metadata
    row_count INTEGER,
    column_count INTEGER,
    headers TEXT[],

    -- Actual table data as JSONB for flexible queries
    data JSONB NOT NULL,

    -- Statistics extracted from table
    statistics JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tables_paper ON paper_tables(paper_id);
CREATE INDEX idx_tables_data ON paper_tables USING gin(data);
CREATE INDEX idx_tables_caption ON paper_tables USING gin(to_tsvector('english', caption));
```

### API Integration Flow

**Workflow**: PDF Upload → Marker → Parser → Supabase

```python
# In python/src/server/api_routes/documents_api.py

@router.post("/upload-research-paper")
async def upload_research_paper(
    file: UploadFile,
    extract_structure: bool = True
):
    """
    Upload research paper with full structure extraction

    Flow:
    1. Save PDF temporarily
    2. Send to Marker for OCR (port 7000)
    3. Send Marker output to Parser (port 7001)
    4. Store structured data in Supabase
    5. Return paper_id and summary
    """

    # Step 1: Send to Marker
    marker_response = await marker_service.convert_pdf(file)

    if not marker_response.success:
        raise HTTPException(500, "OCR failed")

    # Step 2: Send to Parser (if requested)
    if extract_structure:
        parser_response = await parser_service.parse_paper(
            markdown=marker_response.markdown,
            metadata=marker_response.metadata
        )

        if parser_response.success:
            # Step 3: Store in Supabase
            await supabase_service.store_parsed_paper(
                paper_id=parser_response.paper_id,
                structured_data=parser_response.structured_document
            )

            return {
                "success": True,
                "paper_id": parser_response.paper_id,
                "stats": parser_response.parsing_stats,
                "message": "Paper uploaded and fully parsed"
            }

    # Fallback: Just store markdown
    return await store_markdown_only(marker_response)
```

## Parser Service Implementation

### Directory Structure
```text
services/parser/
├── Dockerfile
├── requirements.txt
├── main.py                    # FastAPI application
├── parsers/
│   ├── __init__.py
│   ├── metadata_parser.py     # Extract title, authors, abstract
│   ├── section_parser.py      # Parse hierarchical sections
│   ├── formula_parser.py      # Extract & parse LaTeX formulas
│   ├── table_parser.py        # Parse table structures & data
│   ├── citation_parser.py     # Extract citations & build graph
│   ├── figure_parser.py       # Link figures to captions
│   └── methods_parser.py      # Extract experimental setup
├── models/
│   ├── schemas.py             # Pydantic models for JSON schema
│   └── responses.py           # API response models
├── utils/
│   ├── latex_normalizer.py    # Normalize LaTeX for matching
│   ├── table_detector.py      # Detect table boundaries
│   └── citation_formatter.py  # Parse citation formats
└── tests/
    └── test_parsers.py
```

### Dockerfile (Port 7001)

```dockerfile
# Parser Service for Archon
# Extracts structured data from Marker markdown output
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app

# Expose port
EXPOSE 7001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7001/health || exit 1

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7001"]
```

### requirements.txt
```text
fastapi==0.115.0
uvicorn[standard]==0.34.0
pydantic==2.10.6
python-multipart==0.0.20
spacy==3.8.3
sympy==1.13.1       # Formula parsing
regex==2024.11.6    # Advanced regex
beautifultable==1.1.0  # Table formatting
httpx==0.28.1       # HTTP client for Marker
```

### Main Application (main.py)

```python
"""
Parser Service - Structured Data Extraction from Academic Papers
Port: 7001
Profile: advanced-ocr
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import logging

# Parser modules
from parsers.metadata_parser import MetadataParser
from parsers.section_parser import SectionParser
from parsers.formula_parser import FormulaParser
from parsers.table_parser import TableParser
from parsers.citation_parser import CitationParser
from parsers.figure_parser import FigureParser
from parsers.methods_parser import MethodsParser

app = FastAPI(
    title="Archon Parser Service",
    description="Extract structured data from academic papers",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

# Initialize parsers
metadata_parser = MetadataParser()
section_parser = SectionParser()
formula_parser = FormulaParser()
table_parser = TableParser()
citation_parser = CitationParser()
figure_parser = FigureParser()
methods_parser = MethodsParser()


class ParseRequest(BaseModel):
    markdown: str
    metadata: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, bool]] = {
        "extract_formulas": True,
        "extract_tables": True,
        "extract_citations": True,
        "extract_figures": True,
        "extract_methods": True,
        "parse_table_data": True
    }


class ParseResponse(BaseModel):
    success: bool
    paper_id: str
    parsing_stats: Dict[str, int]
    structured_document: Dict[str, Any]
    warnings: List[str] = []
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "parser",
        "version": "1.0.0"
    }


@app.post("/parse-paper", response_model=ParseResponse)
async def parse_paper(request: ParseRequest):
    """
    Parse complete research paper markdown into structured JSON

    Pipeline:
    1. Extract metadata (title, authors, abstract, keywords)
    2. Parse hierarchical section structure
    3. Extract formulas with LaTeX parsing
    4. Parse tables with data extraction
    5. Extract citations and build graph
    6. Link figures to captions
    7. Extract methods and experimental setup
    """
    try:
        warnings = []

        # Generate paper ID
        import uuid
        paper_id = str(uuid.uuid4())

        # Step 1: Metadata extraction
        metadata = metadata_parser.extract(request.markdown)
        if not metadata.get("title"):
            warnings.append("Could not extract paper title")

        # Step 2: Section parsing
        sections = section_parser.parse(request.markdown)

        # Step 3: Formula extraction
        formulas = []
        if request.options.get("extract_formulas", True):
            formulas = formula_parser.extract(request.markdown, sections)

        # Step 4: Table parsing
        tables = []
        if request.options.get("extract_tables", True):
            tables = table_parser.extract(
                request.markdown,
                sections,
                parse_data=request.options.get("parse_table_data", True)
            )

        # Step 5: Citation extraction
        citations = []
        citation_graph = {}
        if request.options.get("extract_citations", True):
            citations, citation_graph = citation_parser.extract(
                request.markdown,
                sections
            )

        # Step 6: Figure extraction
        figures = []
        if request.options.get("extract_figures", True):
            figures = figure_parser.extract(request.markdown, sections)

        # Step 7: Methods extraction
        methods = {}
        if request.options.get("extract_methods", True):
            methods = methods_parser.extract(request.markdown, sections)

        # Build structured document
        structured_doc = {
            "paper_id": paper_id,
            "source_metadata": request.metadata or {},
            "metadata": metadata,
            "structure": {
                "sections": sections
            },
            "formulas": formulas,
            "tables": tables,
            "figures": figures,
            "citations": citations,
            "citation_graph": citation_graph,
            "methods": methods
        }

        # Generate stats
        stats = {
            "sections_found": len(sections),
            "formulas_extracted": len(formulas),
            "tables_extracted": len(tables),
            "citations_found": len(citations),
            "figures_found": len(figures),
            "methods_sections": 1 if methods else 0
        }

        return ParseResponse(
            success=True,
            paper_id=paper_id,
            parsing_stats=stats,
            structured_document=structured_doc,
            warnings=warnings
        )

    except Exception as e:
        logger.error(f"Parsing failed: {str(e)}", exc_info=True)
        return ParseResponse(
            success=False,
            paper_id="",
            parsing_stats={},
            structured_document={},
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7001)
```

## Docker Compose Integration

### Update docker-compose.yml

Add Parser service after Marker:

```yaml
  # Parser - Extract Structured Data from Markdown (Research Papers)
  parser-service:
    profiles:
      - advanced-ocr
    build:
      context: ./services/parser
      dockerfile: Dockerfile
    container_name: parser-service
    restart: unless-stopped
    ports:
      - "${PARSER_PORT:-7001}:7001"
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - MARKER_SERVICE_URL=http://marker-pdf:7000
    networks:
      - app-network
    depends_on:
      marker-pdf:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Downstream Applications

### 1. Meta-Analysis Pipeline
**Use Case**: Compare methods across multiple papers

```python
# Query all papers with specific methodology
SELECT
    title,
    methods->'model_architecture'->>'type' as architecture,
    methods->'training'->>'optimizer' as optimizer,
    (SELECT AVG((data->>'Dice Score')::float)
     FROM paper_tables t
     WHERE t.paper_id = p.paper_id) as avg_dice_score
FROM parsed_papers p
WHERE methods ? 'model_architecture'
  AND publication_year >= 2020
ORDER BY avg_dice_score DESC;
```

### 2. Formula Search Engine
**Use Case**: Find papers using similar equations

```python
# Search for heat diffusion equations
SELECT DISTINCT p.title, p.authors, f.latex
FROM parsed_papers p
JOIN paper_formulas f ON f.paper_id = p.paper_id
WHERE f.latex_normalized LIKE '%nabla%'
  AND f.equation_type = 'partial_differential'
  AND 'u' = ANY(f.variables);
```

### 3. Citation Graph Analysis
**Use Case**: Build knowledge graph of research lineage

```python
# Find most influential papers (heavily cited)
SELECT
    cited_paper_title,
    COUNT(DISTINCT paper_id) as times_cited,
    ARRAY_AGG(DISTINCT venue) as citing_venues
FROM paper_citations
GROUP BY cited_paper_title
HAVING COUNT(DISTINCT paper_id) >= 5
ORDER BY times_cited DESC;
```

### 4. Table Data Extraction for Training
**Use Case**: Extract numerical results for ML training datasets

```python
# Extract all performance metrics
SELECT
    p.title,
    p.publication_year,
    jsonb_array_elements(t.data) as method_results
FROM parsed_papers p
JOIN paper_tables t ON t.paper_id = p.paper_id
WHERE t.headers @> ARRAY['Method', 'Accuracy']
  AND p.keywords @> ARRAY['deep learning'];
```

## Performance Considerations

### Parsing Pipeline Optimization
- **Parallel Processing**: Run independent parsers (formulas, tables, citations) concurrently
- **Caching**: Cache spaCy NLP models in memory
- **Streaming**: Process large papers in chunks

### Storage Optimization
- **JSONB Indexing**: GIN indexes on structured_data for fast queries
- **Partial Indexes**: Index only parsed papers (not raw documents)
- **Materialized Views**: Pre-compute common aggregations

## Testing Strategy

### Unit Tests
Test each parser independently:
- `test_metadata_parser.py` - Title, authors, abstract extraction
- `test_formula_parser.py` - LaTeX parsing accuracy
- `test_table_parser.py` - Table structure detection

### Integration Tests
Test complete pipeline:
- Upload sample PDF → Marker → Parser → Verify JSON schema
- Test with papers of varying structure complexity

### Validation Tests
Verify data quality:
- Formula LaTeX is valid (compile test)
- Table data types match headers
- Citations reference valid sections

## Monitoring & Observability

### Metrics to Track
- Parsing success rate per paper type
- Average parsing time by component
- Formula extraction accuracy
- Table parsing errors (irregular structures)

### Logging
```python
logger.info(f"Parsed paper {paper_id}: {stats}")
logger.warning(f"Table {table_id} has irregular structure")
logger.error(f"Formula parsing failed: {latex_str}")
```

## Future Enhancements

### Phase 2: Advanced Features
1. **Image OCR Integration**: Extract text from figures using Marker's image output
2. **Cross-Reference Resolution**: Link equation references to actual formulas
3. **Abbreviation Expansion**: Resolve acronyms using context
4. **Author Disambiguation**: Match authors across papers

### Phase 3: ML-Enhanced Parsing
1. **Section Classification**: Train model to classify section types
2. **Entity Recognition**: NER for datasets, methods, metrics
3. **Relation Extraction**: Automatic method-result linking

### Phase 4: Multi-Format Support
1. **LaTeX Source**: Parse .tex files directly
2. **HTML Papers**: Web-based publications
3. **DOCX Support**: Microsoft Word submissions

## Summary

This Parser Service architecture provides:

✅ **Comprehensive Structure Extraction** - All paper components (formulas, tables, citations, figures, methods)
✅ **Queryable Data** - Structured JSON + relational tables for complex queries
✅ **Downstream Ready** - Meta-analysis, knowledge graphs, training data pipelines
✅ **Extensible** - Modular parser design for adding new extractors
✅ **Integration** - Seamless flow: PDF → Marker → Parser → Supabase
✅ **Performance** - Parallel processing, caching, indexed storage

**Next Steps**:
1. Implement basic parsers (metadata, sections, formulas)
2. Test with histopathology paper
3. Iterate on accuracy and coverage
4. Deploy alongside Marker in Docker Compose
