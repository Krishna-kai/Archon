# LaTeX-OCR Service - Native ARM64/AMD64 Build
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pix2tex and API dependencies
# Using latest pix2tex to fix Pydantic v2 compatibility
RUN pip install --no-cache-dir \
    pix2tex[api] \
    fastapi==0.115.5 \
    uvicorn[standard]==0.32.1

# Create simple FastAPI wrapper
COPY main.py .

EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9001/ || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001"]
