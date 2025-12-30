FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api.py .

# Declare environment variables with default values
# This documents what can be configured and provides sensible defaults
ENV API_DB_HOST=host.docker.internal \
    API_DB_PORT=5432 \
    API_DB_NAME=imagomortis \
    API_DB_USER=postgres \
    API_DB_PASSWORD=postgres \
    API_HOST=0.0.0.0 \
    API_PORT=8000

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=1s --retries=2 \
    CMD python -c "import urllib.request, os; port = os.getenv('API_PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/docs')" || exit 1

# Start the service
CMD ["python", "api.py"]
