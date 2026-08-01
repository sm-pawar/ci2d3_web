#!/bin/bash
#
# Create the btree indexes required for fast lineage traversal.
#
# ogr2ogr only creates the GIST spatial index on geom when loading the
# shapefile. The recursive lineage query in /api/lineage joins on inst and
# lineage, so without btree indexes on those columns every recursion step
# sequentially scans the whole table -- turning a ~40ms request into one that
# can take minutes.
#
# Safe to run repeatedly (uses IF NOT EXISTS). Run this once against an
# already-loaded database; scripts/load_data.sh now does it automatically.
#
set -e

DB_HOST="${DB_HOST:-postgis}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ci2d3_db}"
DB_USER="${DB_USER:-geoserver}"
DB_PASSWORD="${DB_PASSWORD:-geoserver123}"
TABLE_NAME="${TABLE_NAME:-iceislands}"

echo "Creating lineage indexes on $TABLE_NAME ($DB_HOST:$DB_PORT/$DB_NAME)..."

PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
    "CREATE INDEX IF NOT EXISTS idx_${TABLE_NAME}_inst ON $TABLE_NAME(inst);
     CREATE INDEX IF NOT EXISTS idx_${TABLE_NAME}_lineage ON $TABLE_NAME(lineage);
     ANALYZE $TABLE_NAME;"

echo "Done. Lineage indexes are in place."
