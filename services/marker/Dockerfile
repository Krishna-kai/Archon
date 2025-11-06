# Marker PDF to Markdown Service for Archon
# Formula and Table Extraction from Academic Papers (CPU-friendly)
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies for Marker
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    ghostscript \
    tesseract-ocr \
    poppler-utils \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch first (lightweight, no CUDA)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install Marker and its dependencies
RUN pip install --no-cache-dir marker-pdf[full]

# Install FastAPI dependencies and psutil
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    psutil

# Copy FastAPI application
COPY main.py /app/main.py

# Expose port
EXPOSE 7000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7000/health || exit 1

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7000"]
