FROM python:3.11-slim

LABEL maintainer="CI2D3 Project"

# Set working directory
WORKDIR /app

# Install system dependencies including GDAL
RUN apt-get update && apt-get install -y \
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

# Copy requirements file
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
