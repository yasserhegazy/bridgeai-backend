# Backend Dockerfile for FastAPI
FROM python:3.12-slim

# Avoid debconf warnings
ENV DEBIAN_FRONTEND=noninteractive

# Build argument to control dependency caching
# Set to "false" for local dev (uses cache), "true" for VPS (rebuilds)
ARG REBUILD_DEPS=false

# Set working directory
WORKDIR /app

# Install system dependencies including cairo for PDF generation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with conditional caching
# When REBUILD_DEPS=true, --no-cache-dir forces fresh install
# When REBUILD_DEPS=false, uses Docker layer cache
RUN if [ "$REBUILD_DEPS" = "true" ]; then \
        pip install --no-cache-dir --force-reinstall -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy application code
COPY . .

# Create directory for ChromaDB data
RUN mkdir -p /app/chroma_data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
