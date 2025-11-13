# ==============================================================================
# CI2D3 Ice Island Explorer - Flask API Dockerfile
# ==============================================================================
#
# Build context: Project root (specified in docker-compose.yml)
# Backend code location: ./backend/
# Target directory: /app (application code served from here)
#
# NOTE: In development, ./backend is volume-mounted to /app, so the COPY
#       operations are mainly for production builds. The volume mount
#       overrides the copied files during development.
#
# ==============================================================================

FROM python:3.11-slim

LABEL maintainer="CI2D3 Project"
LABEL description="Flask REST API for CI2D3 Ice Island Explorer"

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies including GDAL and PostGIS client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy only requirements first to leverage Docker cache
# If requirements don't change, this layer is reused
COPY ./backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
# NOTE: In development mode, this is overridden by volume mount in docker-compose.yml
COPY ./backend/ /app/

# Create necessary directories
RUN mkdir -p /app/logs

# Expose Flask port
EXPOSE 5000

# Health check - verify Flask API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run Flask application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
