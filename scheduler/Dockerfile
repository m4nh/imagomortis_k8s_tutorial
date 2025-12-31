FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY python.py .

# Create shared volume directory
RUN mkdir -p /app/shared

CMD ["python", "python.py"]
