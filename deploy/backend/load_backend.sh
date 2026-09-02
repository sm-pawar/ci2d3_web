#!/usr/bin/env bash
# ==============================================================================
# CI2D3 backend loader - shapefile -> PostGIS -> GeoServer
# ==============================================================================
#
# Runs the repo's existing scripts (scripts/load_data.sh and
# scripts/configure_geoserver.sh) against the BACKEND stack (geo.wirl.carleton.ca)
# without changing them. It uses a one-off container from the flask-api image
# (which already bundles GDAL/ogr2ogr + psql + curl) attached to the backend's
# `geonet`, so it can reach `postgis` and `geoserver` by name.
#
# PREREQUISITES on the backend server:
#   1. The `flask-api` service is defined in the backend docker-compose.yml and
#      its image is built:  docker compose build flask-api
#   2. The shapefile (.shp/.dbf/.shx/.prj) AND the style ci2d3_calvingloc_sld.sld
#      have been copied into  $SHAPE_DIR  (default /srv/geoserver/geoserver_data/ci2d3).
#   3. POSTGRES_PASSWD is set (same value as the backend .env).
#
# USAGE (run from the directory holding the backend docker-compose.yml):
#     export POSTGRES_PASSWD=...            # backend postgis password
#     SHAPE_DIR=/srv/geoserver/geoserver_data/ci2d3 \
#     SHAPEFILE_NAME=240804_ci2d3v1_epsg5937.shp \
#       bash load_backend.sh
# ==============================================================================
set -euo pipefail

# ---- Config (override via env) -----------------------------------------------
COMPOSE="${COMPOSE:-docker compose}"                 # or "docker-compose"
SERVICE="${SERVICE:-flask-api}"                       # tool container (has GDAL)

SHAPE_DIR="${SHAPE_DIR:-/srv/geoserver/geoserver_data/ci2d3}"
SHAPEFILE_NAME="${SHAPEFILE_NAME:-240804_ci2d3v1_epsg5937.shp}"

# Backend PostGIS (from the backend compose).
DB_HOST="${DB_HOST:-postgis}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-geodb}"
DB_USER="${DB_USER:-geouser}"
: "${POSTGRES_PASSWD:?Set POSTGRES_PASSWD (backend postgis password) first}"

# Backend GeoServer (internal address on geonet) + admin creds.
GEOSERVER_URL="${GEOSERVER_URL:-http://geoserver:8080/geoserver}"
GEOSERVER_ADMIN_USER="${GEOSERVER_ADMIN_USER:-admin}"
GEOSERVER_ADMIN_PASSWORD="${GEOSERVER_ADMIN_PASSWORD:-geoserver}"

# Repo root (this script lives in deploy/backend/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== CI2D3 backend loader ==="
echo "  Shapefile dir : $SHAPE_DIR"
echo "  Shapefile     : $SHAPEFILE_NAME"
echo "  Database      : $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  GeoServer     : $GEOSERVER_URL"
echo ""

# Common bits for `compose run`: mount the repo scripts, the SLD, and the
# shapefile dir; hand the scripts the backend credentials via -e.
run_tool() {
  $COMPOSE run --rm --no-deps \
    -v "$REPO_ROOT/scripts:/scripts:ro" \
    -v "$SHAPE_DIR:/data:ro" \
    -v "$REPO_ROOT/data:/opt/data:ro" \
    `# /data -> shapefile (host copy); /opt/data -> repo data dir for the SLD` \
    -e DB_HOST="$DB_HOST" -e DB_PORT="$DB_PORT" \
    -e DB_NAME="$DB_NAME" -e DB_USER="$DB_USER" -e DB_PASSWORD="$POSTGRES_PASSWD" \
    -e SHAPEFILE="/data/$SHAPEFILE_NAME" \
    -e GEOSERVER_URL="$GEOSERVER_URL" \
    -e GEOSERVER_ADMIN_USER="$GEOSERVER_ADMIN_USER" \
    -e GEOSERVER_ADMIN_PASSWORD="$GEOSERVER_ADMIN_PASSWORD" \
    "$SERVICE" bash "$@"
}

echo ">>> Step 1/2: load shapefile into PostGIS (+ lineage indexes)"
run_tool /scripts/load_data.sh

echo ""
echo ">>> Step 2/2: configure GeoServer workspace / datastore / layer / style"
run_tool /scripts/configure_geoserver.sh

echo ""
echo "=== Done. Verify the layer preview at $GEOSERVER_URL/web/ ==="
