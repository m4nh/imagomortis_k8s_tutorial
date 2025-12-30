FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Create uploads directory
RUN mkdir -p uploads

# Declare environment variables with default values
# This documents what can be configured and provides sensible defaults
ENV UPLOADER_RESIZE_HEIGHT=256 \
    UPLOADER_HOST=0.0.0.0 \
    UPLOADER_PORT=8000

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=1s --retries=2 \
    CMD python -c "import urllib.request, os; port = os.getenv('UPLOADER_PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/docs')" || exit 1

# Start the server
CMD ["python", "server.py"]
