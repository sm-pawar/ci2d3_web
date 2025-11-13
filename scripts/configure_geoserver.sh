#!/bin/bash
#
# GeoServer Configuration Script
# Configures workspace, datastore, and layer for CI2D3 Ice Islands
#

set -e

echo "========================================="
echo "GeoServer Configuration Script"
echo "========================================="

# GeoServer configuration
GEOSERVER_URL="${GEOSERVER_URL:-http://localhost:8080/geoserver}"
GEOSERVER_USER="${GEOSERVER_USER:-admin}"
GEOSERVER_PASSWORD="${GEOSERVER_PASSWORD:-geoserver}"

# Workspace configuration
WORKSPACE="ci2d3"
WORKSPACE_URI="http://ci2d3.ca"

# DataStore configuration
DATASTORE="ci2d3_postgis"
DB_HOST="${DB_HOST:-postgis}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ci2d3_db}"
DB_USER="${DB_USER:-geoserver}"
DB_PASSWORD="${DB_PASSWORD:-geoserver123}"

# Layer configuration
LAYER_NAME="iceislands"
NATIVE_NAME="iceislands"

echo ""
echo "Configuration:"
echo "  GeoServer URL: $GEOSERVER_URL"
echo "  Workspace: $WORKSPACE"
echo "  DataStore: $DATASTORE"
echo "  Layer: $LAYER_NAME"
echo ""

# Wait for GeoServer to be ready
echo "Waiting for GeoServer to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" "$GEOSERVER_URL/rest/about/version.json" > /dev/null 2>&1; then
        echo "GeoServer is ready!"
        break
    fi
    echo "  Attempt $((RETRY_COUNT+1))/$MAX_RETRIES: GeoServer is not ready yet..."
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: GeoServer did not become ready in time"
    exit 1
fi

echo ""

# Create workspace
echo "Creating workspace '$WORKSPACE'..."
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" \
  -X POST "$GEOSERVER_URL/rest/workspaces" \
  -H "Content-Type: application/json" \
  -d "{
    \"workspace\": {
      \"name\": \"$WORKSPACE\",
      \"isolated\": false
    }
  }" || echo "Workspace may already exist"

echo ""

# Create PostGIS datastore
echo "Creating PostGIS datastore '$DATASTORE'..."
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" \
  -X POST "$GEOSERVER_URL/rest/workspaces/$WORKSPACE/datastores" \
  -H "Content-Type: application/json" \
  -d "{
    \"dataStore\": {
      \"name\": \"$DATASTORE\",
      \"type\": \"PostGIS\",
      \"enabled\": true,
      \"connectionParameters\": {
        \"entry\": [
          {\"@key\": \"host\", \"$\": \"$DB_HOST\"},
          {\"@key\": \"port\", \"$\": \"$DB_PORT\"},
          {\"@key\": \"database\", \"$\": \"$DB_NAME\"},
          {\"@key\": \"user\", \"$\": \"$DB_USER\"},
          {\"@key\": \"passwd\", \"$\": \"$DB_PASSWORD\"},
          {\"@key\": \"dbtype\", \"$\": \"postgis\"},
          {\"@key\": \"schema\", \"$\": \"public\"},
          {\"@key\": \"Expose primary keys\", \"$\": \"true\"}
        ]
      }
    }
  }" || echo "DataStore may already exist"

echo ""

# Publish layer
echo "Publishing layer '$LAYER_NAME'..."
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" \
  -X POST "$GEOSERVER_URL/rest/workspaces/$WORKSPACE/datastores/$DATASTORE/featuretypes" \
  -H "Content-Type: application/json" \
  -d "{
    \"featureType\": {
      \"name\": \"$LAYER_NAME\",
      \"nativeName\": \"$NATIVE_NAME\",
      \"title\": \"CI2D3 Ice Islands\",
      \"abstract\": \"Canadian Ice Island Drift, Deterioration and Detection Database\",
      \"enabled\": true,
      \"srs\": \"EPSG:4326\",
      \"projectionPolicy\": \"FORCE_DECLARED\"
    }
  }" || echo "Layer may already exist"

echo ""

# Apply SLD style (if exists)
if [ -f "/opt/data/ci2d3_calvingloc_sld.sld" ]; then
    echo "Uploading SLD style..."

    # Create style
    curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" \
      -X POST "$GEOSERVER_URL/rest/workspaces/$WORKSPACE/styles" \
      -H "Content-Type: application/json" \
      -d "{
        \"style\": {
          \"name\": \"ci2d3_calvingloc\",
          \"filename\": \"ci2d3_calvingloc.sld\"
        }
      }" || echo "Style may already exist"

    # Upload SLD file
    curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" \
      -X PUT "$GEOSERVER_URL/rest/workspaces/$WORKSPACE/styles/ci2d3_calvingloc" \
      -H "Content-Type: application/vnd.ogc.sld+xml" \
      -d @"/opt/data/ci2d3_calvingloc_sld.sld"

    # Apply style to layer
    curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" \
      -X PUT "$GEOSERVER_URL/rest/layers/$WORKSPACE:$LAYER_NAME" \
      -H "Content-Type: application/json" \
      -d "{
        \"layer\": {
          \"defaultStyle\": {
            \"name\": \"$WORKSPACE:ci2d3_calvingloc\"
          }
        }
      }"

    echo "SLD style applied!"
else
    echo "SLD file not found, skipping style configuration"
fi

echo ""
echo "========================================="
echo "GeoServer configuration completed!"
echo "========================================="
echo ""
echo "Access GeoServer at: $GEOSERVER_URL"
echo "Layer preview: $GEOSERVER_URL/web/?wicket:bookmarkablePage=:org.geoserver.web.demo.MapPreviewPage"
echo ""
