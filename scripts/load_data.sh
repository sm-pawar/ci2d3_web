#!/bin/bash
#
# CI2D3 Data Loading Script
# Loads Ice Island shapefile into PostGIS database
#

set -e

echo "========================================="
echo "CI2D3 Data Loading Script"
echo "========================================="

# Database connection parameters
DB_HOST="${DB_HOST:-postgis}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ci2d3_db}"
DB_USER="${DB_USER:-geoserver}"
DB_PASSWORD="${DB_PASSWORD:-geoserver123}"

# Shapefile path. Override with the SHAPEFILE env var when the file name or
# mount point differs (e.g. on the backend server the shapefile lives under
# /srv/geoserver/geoserver_data/ci2d3, mounted to /data).
SHAPEFILE="${SHAPEFILE:-/data/240804_ci2d3v1_epsg5937.shp}"
TABLE_NAME="${TABLE_NAME:-iceislands}"

echo ""
echo "Configuration:"
echo "  Database Host: $DB_HOST"
echo "  Database Port: $DB_PORT"
echo "  Database Name: $DB_NAME"
echo "  Database User: $DB_USER"
echo "  Table Name: $TABLE_NAME"
echo "  Shapefile: $SHAPEFILE"
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "  PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"
echo ""

# Check if shapefile exists
if [ ! -f "$SHAPEFILE" ]; then
    echo "ERROR: Shapefile not found at $SHAPEFILE"
    exit 1
fi

echo "Shapefile found: $SHAPEFILE"
echo ""

# Check if table already exists
echo "Checking if table '$TABLE_NAME' already exists..."
TABLE_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='$TABLE_NAME');")

if [ "$TABLE_EXISTS" = "t" ]; then
    echo "WARNING: Table '$TABLE_NAME' already exists!"
    read -p "Do you want to drop and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Dropping existing table..."
        PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE IF EXISTS $TABLE_NAME CASCADE;"
        echo "Table dropped."
    else
        echo "Keeping existing table. Exiting."
        exit 0
    fi
fi

echo ""
echo "Loading shapefile into PostGIS..."
echo ""

# Load shapefile using ogr2ogr
# - Convert from EPSG:5937 (Canada Lambert Conformal Conic) to EPSG:4326 (WGS84) for web compatibility
# - Use lowercase table name
# - Create spatial index
# - Preserve field names

ogr2ogr \
    -f "PostgreSQL" \
    PG:"host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD" \
    "$SHAPEFILE" \
    -nln "$TABLE_NAME" \
    -nlt PROMOTE_TO_MULTI \
    -lco GEOMETRY_NAME=geom \
    -lco FID=gid \
    -lco SPATIAL_INDEX=GIST \
    -t_srs EPSG:4326 \
    -progress

echo ""
echo "Data loaded successfully!"
echo ""

# Create btree indexes on the lineage graph columns.
# ogr2ogr only creates the GIST spatial index on geom. Without these, the
# recursive lineage traversal in /api/lineage sequentially scans the whole
# table on every step and takes seconds-to-minutes instead of milliseconds.
echo "Creating lineage indexes (inst, lineage)..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
    "CREATE INDEX IF NOT EXISTS idx_${TABLE_NAME}_inst ON $TABLE_NAME(inst);
     CREATE INDEX IF NOT EXISTS idx_${TABLE_NAME}_lineage ON $TABLE_NAME(lineage);
     ANALYZE $TABLE_NAME;"
echo "Indexes created."
echo ""

# Get table statistics
echo "Table Statistics:"
RECORD_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT COUNT(*) FROM $TABLE_NAME;")
echo "  Total records: $RECORD_COUNT"

# Get geometry type
GEOM_TYPE=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT DISTINCT GeometryType(geom) FROM $TABLE_NAME LIMIT 1;")
echo "  Geometry type: $GEOM_TYPE"

# Get SRID
SRID=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT DISTINCT ST_SRID(geom) FROM $TABLE_NAME LIMIT 1;")
echo "  SRID: $SRID"

# List columns
echo ""
echo "Table Columns:"
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='$TABLE_NAME' ORDER BY ordinal_position;"

echo ""
echo "========================================="
echo "Data loading completed successfully!"
echo "========================================="