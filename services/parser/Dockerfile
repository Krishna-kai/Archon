# Parser Service - Slim Production Container
FROM python:3.11-slim

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

# Expose port 9004
EXPOSE 9004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:9004/health', timeout=5.0)"

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9004"]
