FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY pusher.py .

# Create uploads directory
RUN mkdir -p uploads


# Declare environment variables with default values
# This documents what can be configured and provides sensible defaults
ENV PUSHER_POLL_INTERVAL=5 \
    PUSHER_DB_HOST=host.docker.internal \
    PUSHER_DB_PORT=5432 \
    PUSHER_DB_NAME=imagomortis \
    PUSHER_DB_USER=postgres \
    PUSHER_DB_PASSWORD=postgres

# Start the service
CMD ["python", "pusher.py"]
