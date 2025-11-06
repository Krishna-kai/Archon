# Docling OCR Service for Archon
# Optimized for Mac M4 with native ARM64 support
FROM python:3.11-slim-bookworm

ENV GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y \
        libgl1 \
        libglib2.0-0 \
        curl \
        wget \
        git \
        procps \
        build-essential \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install PyTorch (ARM64-native)
RUN pip install --no-cache-dir \
    torch torchvision torchaudio

# Install Docling with all dependencies
RUN pip install --no-cache-dir \
    docling \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Set environment variables for model caching
ENV HF_HOME=/models
ENV TORCH_HOME=/models
ENV DOCLING_ARTIFACTS_PATH=/models/docling

# Pre-download Docling models (reduces startup time)
RUN mkdir -p /models/docling && \
    docling-tools models download && \
    mv /root/.cache/docling/models/* /models/docling/ && \
    rm -rf /root/.cache/docling

# Copy FastAPI application
COPY main.py /app/main.py

# Set thread budget
ENV OMP_NUM_THREADS=4

# Expose FastAPI port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
