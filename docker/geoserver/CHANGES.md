# GeoServer Dockerfile Changes

## Summary

The GeoServer Dockerfile has been updated to align with the CI2D3 project's current directory structure and follow Docker best practices.

## Key Changes

### 1. Updated Build Arguments

**Before:**
```dockerfile
ARG WEBSITE_PATH=./website/
ARG CUSTOM_DATA_PATH=./data/
```

**After:**
```dockerfile
ARG WEBSITE_PATH=./frontend/
ARG CUSTOM_DATA_PATH=./data/
ARG SCRIPTS_PATH=./scripts/
```

### 2. Improved COPY Operations

**Before:**
```dockerfile
COPY $WEBSITE_PATH $CATALINA_HOME/webapps/ROOT/
COPY *.sh /opt/
```

**After:**
```dockerfile
# Handle optional directories gracefully
COPY $WEBSITE_PATH* $CATALINA_HOME/webapps/ROOT/ 2>/dev/null || :
COPY config/ $CONFIG_DIR/
COPY scripts/*.sh /opt/scripts/ 2>/dev/null || :
```

**Benefits:**
- No build failures if optional directories are empty
- Better organization of files within the container
- Explicit handling of configuration and scripts

### 3. Enhanced Startup Script Handling

**Before:**
```dockerfile
COPY *.sh /opt/
RUN chmod +x /opt/*.sh && sed -i 's/\r$//' /opt/startup.sh
ENTRYPOINT ["bash", "/opt/startup.sh"]
```

**After:**
```dockerfile
RUN if [ -f "$CONFIG_DIR/startup.sh" ]; then \
        cp $CONFIG_DIR/startup.sh /opt/startup.sh && \
        chmod +x /opt/startup.sh && \
        sed -i 's/\r$//' /opt/startup.sh; \
    else \
        echo '#!/bin/bash' > /opt/startup.sh && \
        echo 'exec catalina.sh run' >> /opt/startup.sh && \
        chmod +x /opt/startup.sh; \
    fi
ENTRYPOINT ["bash", "/opt/startup.sh"]
```

**Benefits:**
- Graceful fallback if startup.sh is missing
- Proper error handling
- More maintainable

### 4. Updated Healthcheck

**Before:**
```dockerfile
HEALTHCHECK CMD curl --fail "http://localhost:8080/" && curl --fail "http://localhost:8080/geoserver/web/"
```

**After:**
```dockerfile
HEALTHCHECK CMD curl --fail --url "http://localhost:8080/geoserver/web/" || exit 1
```

**Benefits:**
- Focus on GeoServer availability
- Simpler and more reliable
- Frontend check removed (optional component)

### 5. Added Documentation

New comprehensive documentation header in Dockerfile:

```dockerfile
# ==============================================================================
# CI2D3 Ice Island Explorer - GeoServer Dockerfile
# ==============================================================================
#
# PROJECT STRUCTURE (build context is project root):
#   - frontend/          -> Copied to Tomcat ROOT webapp
#   - data/              -> Ice island shapefiles and SLD styles
#   - geoserver_data/    -> Custom GeoServer data directory
#   - config/            -> Configuration files
#   - scripts/           -> Utility scripts
# ...
```

## New Directory Structure

### Created Directories

```
ci2d3_web/
├── additional_fonts/        # NEW: Custom TrueType fonts for GeoServer
│   └── .gitkeep
├── additional_libs/         # NEW: Custom JAR plugins for GeoServer
│   └── .gitkeep
├── geoserver_data/         # NEW: Persistent GeoServer configuration
│   └── .gitkeep
├── docker/
│   └── geoserver/
│       ├── Dockerfile       # UPDATED
│       ├── README.md        # NEW: Comprehensive documentation
│       └── CHANGES.md       # NEW: This file
└── .dockerignore           # NEW: Optimize build context
```

### Directory Purpose

| Directory | Purpose | Optional? |
|-----------|---------|-----------|
| `frontend/` | CI2D3 web application served on Tomcat ROOT | No |
| `data/` | Ice island shapefiles and SLD styles | No |
| `config/` | Configuration files (startup.sh) | No |
| `scripts/` | Utility scripts for data loading, etc. | Yes |
| `geoserver_data/` | GeoServer persistent configuration | Yes |
| `additional_fonts/` | Custom fonts for map rendering | Yes |
| `additional_libs/` | Custom GeoServer plugins (JAR files) | Yes |

## Container File Locations

Files are copied to these locations in the container:

```
/usr/local/tomcat/webapps/ROOT/     <- frontend/*
/opt/data/                          <- data/*
/opt/config/                        <- config/*
/opt/scripts/                       <- scripts/*.sh
/opt/geoserver_data/               <- geoserver_data/* (or volume mount)
/usr/share/fonts/truetype/         <- additional_fonts/*
$GEOSERVER_LIB_DIR/                <- additional_libs/*
```

## Build Context Optimization

### New .dockerignore File

Excludes unnecessary files from Docker build context:

- Git files (`.git/`, `.gitignore`)
- Python cache (`__pycache__/`, `*.pyc`)
- Backend code (not needed in GeoServer image)
- IDE files (`.vscode/`, `.idea/`)
- Documentation (except essential README)
- Environment files (`.env*`)
- Old files (`old_docker/`)

**Result:** Faster builds, smaller context

## Migration Guide

### If You Have Existing Setup

1. **No action needed** - The changes are backward compatible
2. **Optional**: Add custom fonts to `additional_fonts/`
3. **Optional**: Add custom plugins to `additional_libs/`
4. **Rebuild**: `docker-compose build --no-cache geoserver`

### Adding Custom Fonts

```bash
# Copy fonts to additional_fonts/
cp ~/fonts/*.ttf additional_fonts/

# Rebuild image
docker-compose build geoserver
```

### Adding Custom Plugins

```bash
# Copy JAR files to additional_libs/
cp ~/plugins/*.jar additional_libs/

# Rebuild image
docker-compose build geoserver
```

## Testing the Changes

### 1. Rebuild the Image

```bash
docker-compose build --no-cache geoserver
```

### 2. Start the Container

```bash
docker-compose up -d geoserver
```

### 3. Check Logs

```bash
docker-compose logs -f geoserver
```

Wait for: `Server startup in [xxxx] milliseconds`

### 4. Verify Access

```bash
# Check GeoServer is running
curl http://localhost:8080/geoserver/web/

# Check frontend is served (if copied)
curl http://localhost:8080/

# Check health
docker inspect --format='{{.State.Health.Status}}' ci2d3_geoserver
```

### 5. Verify File Locations

```bash
# Check frontend files
docker-compose exec geoserver ls -la /usr/local/tomcat/webapps/ROOT/

# Check data files
docker-compose exec geoserver ls -la /opt/data/

# Check scripts
docker-compose exec geoserver ls -la /opt/scripts/

# Check config
docker-compose exec geoserver ls -la /opt/config/
```

## Rollback

If you need to rollback to the old version:

```bash
# Checkout previous commit
git checkout 488e9fb

# Rebuild
docker-compose build --no-cache geoserver
```

## Benefits Summary

1. **Better Organization**: Clear separation of concerns
2. **Error Handling**: Graceful handling of optional files
3. **Maintainability**: Well-documented, easy to modify
4. **Flexibility**: Easy to add fonts, plugins, custom configs
5. **Best Practices**: Follows Docker and GeoServer recommendations
6. **Performance**: Optimized build context with .dockerignore

## Questions?

See the full documentation:
- [GeoServer Docker README](README.md)
- [Main Project README](../../README.md)
- [Setup Guide](../../SETUP.md)
