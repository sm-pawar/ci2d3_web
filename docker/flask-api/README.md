# Flask API Docker Image for CI2D3

This directory contains the Dockerfile for building the Flask REST API backend for the CI2D3 Ice Island Explorer project.

## Overview

This Dockerfile creates a Python 3.11 Flask application with:

- **Flask** web framework for REST API
- **SQLAlchemy** + **GeoAlchemy2** for PostGIS database access
- **GDAL/OGR** for geospatial data processing
- **PostgreSQL client** for database connectivity
- **Development mode** with volume mounting for live code updates

## Build Context

The Dockerfile expects to be built from the **project root directory**, as configured in docker-compose.yml:

```yaml
build:
  context: .                            # Project root
  dockerfile: docker/flask-api/Dockerfile
```

### Directory Mapping

```
Project Root (build context)
└── backend/                → /app/ (in container)
    ├── app.py
    ├── config.py
    ├── requirements.txt
    ├── routes/
    ├── services/
    ├── models/
    └── utils/
```

## Container Structure

### Working Directory

- `/app/` - Flask application code (from backend/)

### Key Files in Container

```
/app/
├── app.py                  # Flask application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── routes/                 # API endpoints
│   ├── inspect_routes.py
│   └── filter_routes.py
├── services/               # Business logic
│   ├── db_service.py
│   └── geoserver_service.py
├── models/                 # Database models
│   └── iceisland_model.py
├── utils/                  # Utilities
│   ├── query_builder.py
│   └── geojson_formatter.py
└── logs/                   # Application logs (created at runtime)
```

### Ports

- **5000**: Flask API HTTP server

### Environment Variables

Set via docker-compose.yml:

```yaml
FLASK_APP=app.py
FLASK_ENV=development        # or 'production'
DB_HOST=postgis
DB_PORT=5432
DB_NAME=ci2d3_db
DB_USER=geoserver
DB_PASSWORD=geoserver123
GEOSERVER_URL=http://geoserver:8080/geoserver
```

## Python Dependencies

Main dependencies (see `backend/requirements.txt`):

- **Flask** 3.0.0 - Web framework
- **Flask-CORS** 4.0.0 - CORS support
- **SQLAlchemy** 2.0.23 - ORM
- **GeoAlchemy2** 0.14.2 - PostGIS extensions
- **psycopg2-binary** 2.9.9 - PostgreSQL driver
- **Shapely** 2.0.2 - Geometry operations
- **requests** 2.31.0 - HTTP client for GeoServer

## Building the Image

### Via Docker Compose (Recommended)

```bash
# From project root
docker-compose build flask-api
```

### Manually

```bash
# From project root
docker build -f docker/flask-api/Dockerfile -t ci2d3_flask_api:latest .
```

## Running the Container

### Via Docker Compose (Recommended)

```bash
docker-compose up -d flask-api
```

### Manually

```bash
docker run -d \
  --name ci2d3_flask_api \
  -p 5000:5000 \
  -e DB_HOST=postgis \
  -e DB_PORT=5432 \
  -e DB_NAME=ci2d3_db \
  -e DB_USER=geoserver \
  -e DB_PASSWORD=geoserver123 \
  -v $(pwd)/backend:/app \
  ci2d3_flask_api:latest
```

## Development Mode

### Live Code Reloading

In development, the `backend/` directory is volume-mounted to `/app/` in the container. This means:

✅ **Code changes are reflected immediately** (Flask auto-reloads)
✅ **No need to rebuild the image** for code changes
✅ **Fast development iteration**

```yaml
# In docker-compose.yml
volumes:
  - ./backend:/app          # Live reload
```

### Watching Logs

```bash
# View Flask logs
docker-compose logs -f flask-api

# Stream new logs only
docker-compose logs --tail=100 -f flask-api
```

## API Endpoints

Once running, the API is available at `http://localhost:5000/`

### Health Check

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "ci2d3-api",
  "version": "1.0.0"
}
```

### Inspection Endpoints

```bash
# Get feature by ID
curl http://localhost:5000/api/inspect/1

# Get available attributes
curl http://localhost:5000/api/inspect/attributes

# Get feature count
curl http://localhost:5000/api/inspect/count

# Get unique values for a field
curl http://localhost:5000/api/inspect/unique/calvingloc
```

### Filter Endpoint

```bash
# Filter by calving location
curl -X POST http://localhost:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'

# Filter by year
curl -X POST http://localhost:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "carving_year", "operator": ">=", "value": 2010}'
```

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs flask-api
```

**Common issues:**
- Database not ready: Wait for PostGIS to be healthy
- Port already in use: Change port in docker-compose.yml
- Import errors: Rebuild image if requirements.txt changed

### Database Connection Errors

**Test database connectivity:**
```bash
docker-compose exec flask-api psql -h postgis -U geoserver -d ci2d3_db
```

**Check environment variables:**
```bash
docker-compose exec flask-api env | grep DB_
```

### Import Errors

If you get `ModuleNotFoundError`:

1. Check that volume mount is correct
2. Verify all `__init__.py` files exist
3. Rebuild the image:
   ```bash
   docker-compose build --no-cache flask-api
   ```

### GDAL Errors

**Verify GDAL installation:**
```bash
docker-compose exec flask-api ogrinfo --version
docker-compose exec flask-api python -c "from osgeo import gdal; print(gdal.__version__)"
```

## Production Deployment

For production, consider:

### 1. Use Production WSGI Server

Replace Flask's development server with Gunicorn:

```dockerfile
# Add to requirements.txt
gunicorn==21.2.0

# Change CMD in Dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

### 2. Remove Volume Mounts

Don't use volume mounts in production - rely on the COPY in the Dockerfile:

```yaml
# Remove this in production
# volumes:
#   - ./backend:/app
```

### 3. Set Production Environment

```yaml
environment:
  FLASK_ENV: production
  SECRET_KEY: ${SECRET_KEY}  # Use secrets management
```

### 4. Enable Logging

```yaml
volumes:
  - flask_logs:/app/logs
```

### 5. Use Reverse Proxy

Put API behind NGINX or similar:

```
Client -> NGINX (443) -> Flask API (5000)
```

## Testing

### Unit Tests

```bash
# Enter container
docker-compose exec flask-api bash

# Run tests (if you add them)
pytest tests/
```

### API Tests

```bash
# Test all endpoints
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/api/inspect/1
curl -X POST http://localhost:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'
```

## Performance Tuning

### Increase Workers

For production with Gunicorn:

```python
# Rule of thumb: (2 × CPU cores) + 1
workers = 4
threads = 2
```

### Connection Pooling

SQLAlchemy connection pooling is configured in `backend/config.py`

### Caching

Consider adding Redis for caching frequent queries:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Security Notes

1. **Change default passwords** in production
2. **Use environment variables** for sensitive data
3. **Enable HTTPS** in production (via reverse proxy)
4. **Validate all inputs** (already implemented in query_builder.py)
5. **Rate limiting** - consider adding Flask-Limiter
6. **SQL injection protection** - using parameterized queries

## References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [GeoAlchemy2 Documentation](https://geoalchemy-2.readthedocs.io/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
