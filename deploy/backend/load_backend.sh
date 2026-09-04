#!/usr/bin/env bash
# ==============================================================================
# CI2D3 backend loader - shapefile -> PostGIS -> GeoServer
# ==============================================================================
#
# Runs the repo's existing scripts (scripts/load_data.sh and
# scripts/configure_geoserver.sh) against the BACKEND stack (geo.wirl.carleton.ca)
# without changing them. It uses a one-off container from the flask-api image
# (which already bundles GDAL/ogr2ogr + psql + curl) attached to the backend's
# `geonet`, so it can reach `ci2d3-postgis` and `geoserver` by name.
#
# Loads into the DEDICATED ci2d3-postgis container (which you own), then points
# the existing GeoServer's datastore at it.
#
# PREREQUISITES on the backend server:
#   1. The `ci2d3-postgis` and `flask-api` services are in the backend
#      docker-compose.yml and running (ci2d3-postgis) / built (flask-api image).
#   2. The shapefile (.shp/.dbf/.shx/.prj) has been copied into $SHAPE_DIR
#      (default /srv/geoserver/geoserver_data/ci2d3). The SLD is taken from the
#      repo's data/ dir automatically.
#   3. CI2D3_DB_PASSWORD is set (same value as the backend .env).
#
# USAGE (run from the directory holding the backend docker-compose.yml):
#     export CI2D3_DB_PASSWORD=...          # ci2d3-postgis password
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

# Dedicated CI2D3 PostGIS (the ci2d3-postgis service you added to the backend
# compose). Password comes from CI2D3_DB_PASSWORD in the backend .env.
DB_HOST="${DB_HOST:-ci2d3-postgis}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ci2d3_db}"
DB_USER="${DB_USER:-ci2d3}"
: "${CI2D3_DB_PASSWORD:?Set CI2D3_DB_PASSWORD (the ci2d3-postgis password) first}"

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
    -e DB_NAME="$DB_NAME" -e DB_USER="$DB_USER" -e DB_PASSWORD="$CI2D3_DB_PASSWORD" \
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
