FROM python:3.12-slim

WORKDIR /app

# System dependencies for PostgreSQL, Cryptography, and OpenCV
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create staging and data directories with proper ownership for non-root user
RUN mkdir -p /app/staging /app/data

# Create non-root user and give it ownership of app directory
RUN useradd -m appuser && chown -R appuser:appuser /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY common/ ./common/
COPY automation/ ./automation/

# Switch to non-root user
USER appuser

# Health check with start-period to allow for migration time
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=120s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run uvicorn on port 8000
# Run database migrations once before starting the multi-worker server
CMD ["sh", "-c", "python prestart.py && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4"]
