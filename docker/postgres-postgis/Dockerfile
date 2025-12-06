# ==============================================================================
# CI2D3 Ice Island Explorer - PostGIS with GDAL Dockerfile
# ==============================================================================
#
# Extends the official PostGIS image with GDAL/OGR tools for shapefile loading
#
# ==============================================================================

FROM postgis/postgis:16-3.4

LABEL maintainer="CI2D3 Project"
LABEL description="PostgreSQL 16 + PostGIS 3.4 + GDAL tools"

# Install GDAL and required utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# Verify GDAL installation
RUN ogr2ogr --version && ogrinfo --version

# Set working directory for scripts
WORKDIR /scripts

# Container will use the default postgres entrypoint
