# GeoServer Docker Image for CI2D3

This directory contains the Dockerfile for building a custom GeoServer image optimized for the CI2D3 Ice Island Explorer project.

## Overview

This is a multi-stage Docker build that creates a GeoServer 2.27.0 instance with:

- **GDAL/OGR support** for advanced geospatial data processing
- **PostGIS connectivity** for spatial database integration
- **CI2D3 frontend** served on the ROOT webapp
- **Ice island data** accessible within the container
- **Custom configuration** scripts and utilities

## Build Context

The Dockerfile expects to be built from the **project root directory** (not from this directory). The docker-compose.yml file handles this correctly.

### Directory Mapping

When building, the following directories are copied into the image:

```
Project Root (build context)
├── frontend/           → /usr/local/tomcat/webapps/ROOT/
├── data/               → /opt/data/
├── geoserver_data/     → /opt/geoserver_data/ (optional)
├── config/             → /opt/config/
├── scripts/            → /opt/scripts/
├── additional_libs/    → GeoServer lib/ (optional)
└── additional_fonts/   → /usr/share/fonts/truetype/ (optional)
```

## Build Arguments

Key build arguments (set in docker-compose.yml):

- `GS_VERSION`: GeoServer version (default: 2.27.0)
- `BUILD_GDAL`: Enable GDAL build (default: true for CI2D3)
- `GDAL_VERSION`: GDAL version (default: 3.10.2)
- `PROJ_VERSION`: PROJ version (default: 9.5.1)
- `WEBSITE_PATH`: Frontend files path (default: ./frontend/)
- `CUSTOM_DATA_PATH`: Data files path (default: ./data/)

## Container Structure

### Key Directories in Container

- `/usr/local/tomcat/` - Tomcat installation
  - `webapps/ROOT/` - CI2D3 frontend application
  - `webapps/geoserver/` - GeoServer web application
- `/opt/geoserver_data/` - GeoServer data directory (can be volume-mounted)
- `/opt/data/` - Ice island shapefiles and SLD styles
- `/opt/config/` - Configuration files
- `/opt/scripts/` - Utility scripts
- `/opt/startup.sh` - Container entrypoint script

### Ports

- **8080**: GeoServer web interface and CI2D3 frontend

### Environment Variables

Set via docker-compose.yml:

```yaml
# Database connection
POSTGRES_HOST=postgis
POSTGRES_PORT=5432
POSTGRES_DB=ci2d3_db
POSTGRES_USERNAME=geoserver
POSTGRES_PASSWORD=geoserver123

# GeoServer admin
GEOSERVER_ADMIN_USER=admin
GEOSERVER_ADMIN_PASSWORD=geoserver

# JVM settings
EXTRA_JAVA_OPTS=-Xms512m -Xmx2g

# CORS settings
CORS_ENABLED=true
CORS_ALLOWED_ORIGINS=*
```

## Building the Image

### Via Docker Compose (Recommended)

```bash
# From project root
docker-compose build geoserver
```

### Manually

```bash
# From project root
docker build -f docker/geoserver/Dockerfile \
  --build-arg BUILD_GDAL=true \
  --build-arg GS_VERSION=2.27.0 \
  -t ci2d3_geoserver:latest .
```

## Running the Container

### Via Docker Compose (Recommended)

```bash
docker-compose up -d geoserver
```

### Manually

```bash
docker run -d \
  --name ci2d3_geoserver \
  -p 8080:8080 \
  -e POSTGRES_HOST=postgis \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=ci2d3_db \
  -e POSTGRES_USERNAME=geoserver \
  -e POSTGRES_PASSWORD=geoserver123 \
  -v geoserver_data:/opt/geoserver_data \
  ci2d3_geoserver:latest
```

## Accessing GeoServer

Once the container is running:

- **GeoServer Admin**: http://localhost:8080/geoserver
  - Username: `admin`
  - Password: `geoserver` (or as configured)

- **CI2D3 Frontend**: http://localhost:8080/

- **WMS Endpoint**: http://localhost:8080/geoserver/ci2d3/wms

- **WFS Endpoint**: http://localhost:8080/geoserver/ci2d3/wfs

## Configuration

### Startup Script

The container uses `/opt/startup.sh` as its entrypoint. This script:

1. Waits for PostgreSQL to be ready
2. Starts Tomcat/GeoServer

You can customize startup behavior by modifying `config/startup.sh` in the project.

### Adding Custom Fonts

Place TrueType fonts in `additional_fonts/` directory before building:

```
additional_fonts/
├── CustomFont.ttf
└── AnotherFont.ttf
```

### Adding Custom Libraries

Place JAR files in `additional_libs/` directory before building:

```
additional_libs/
├── custom-plugin.jar
└── additional-dependency.jar
```

## Volumes

### Persistent GeoServer Data

To persist GeoServer configuration:

```yaml
volumes:
  - geoserver_data:/opt/geoserver_data
```

### Custom Data Access

To update ice island data without rebuilding:

```yaml
volumes:
  - ./data:/opt/data:ro
```

## Health Check

The container includes a health check that verifies GeoServer is responding:

```dockerfile
HEALTHCHECK --interval=1m --timeout=20s --retries=3 \
  CMD curl --fail --url "http://localhost:8080/geoserver/web/"
```

Check health status:

```bash
docker inspect --format='{{.State.Health.Status}}' ci2d3_geoserver
```

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs geoserver
```

**Check startup script:**
```bash
docker-compose exec geoserver cat /opt/startup.sh
```

### GeoServer Takes Long to Start

This is normal. GeoServer can take 2-5 minutes to fully initialize, especially on first run with GDAL enabled.

Monitor startup:
```bash
docker-compose logs -f geoserver | grep "Server startup"
```

### Out of Memory

Increase JVM memory in docker-compose.yml:

```yaml
environment:
  EXTRA_JAVA_OPTS: "-Xms1g -Xmx4g"
```

### CORS Issues

Verify CORS settings:

```bash
docker-compose exec geoserver env | grep CORS
```

## Development

### Modifying the Dockerfile

1. Make changes to `docker/geoserver/Dockerfile`
2. Rebuild the image:
   ```bash
   docker-compose build --no-cache geoserver
   ```
3. Restart the container:
   ```bash
   docker-compose up -d geoserver
   ```

### Testing Changes

```bash
# Build and start
docker-compose up -d --build geoserver

# Check logs
docker-compose logs -f geoserver

# Verify GeoServer is running
curl http://localhost:8080/geoserver/web/

# Test WMS
curl "http://localhost:8080/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities"
```

## Security Notes

1. **Change default passwords** in production
2. The Dockerfile follows CIS Docker benchmarks:
   - Removes setuid/setgid permissions
   - Obscures server version information
3. Consider running as non-root user for production
4. Use secrets management for credentials

## References

- [GeoServer Documentation](https://docs.geoserver.org/)
- [GeoServer Docker](https://github.com/geoserver/docker)
- [GDAL Documentation](https://gdal.org/)
- [PostGIS Documentation](https://postgis.net/)
