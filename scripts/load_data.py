#!/usr/bin/env python3
"""
CI2D3 Data Loading Script (Python version)
Loads Ice Island shapefile into PostGIS database using Python
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'ci2d3_db'),
    'user': os.getenv('DB_USER', 'geoserver'),
    'password': os.getenv('DB_PASSWORD', 'geoserver123')
}

SHAPEFILE = '/data/240804_ci2d3v1_epsg5937.shp'
TABLE_NAME = 'iceislands'


def wait_for_postgres(max_retries=30):
    """Wait for PostgreSQL to be ready"""
    print("Waiting for PostgreSQL to be ready...")

    for i in range(max_retries):
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                dbname=DB_CONFIG['dbname'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password']
            )
            conn.close()
            print("PostgreSQL is ready!")
            return True
        except Exception as e:
            print(f"  Attempt {i+1}/{max_retries}: PostgreSQL is unavailable - {e}")
            time.sleep(2)

    print("ERROR: Could not connect to PostgreSQL")
    return False


def check_table_exists():
    """Check if the table already exists"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name=%s)",
            (TABLE_NAME,)
        )
        exists = cur.fetchone()[0]
        cur.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"ERROR checking table existence: {e}")
        return False


def drop_table():
    """Drop the existing table"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME} CASCADE")
        conn.commit()
        cur.close()
        conn.close()
        print("Table dropped successfully")
        return True
    except Exception as e:
        print(f"ERROR dropping table: {e}")
        return False


def load_shapefile():
    """Load shapefile using ogr2ogr"""
    print("\nLoading shapefile into PostGIS...\n")

    # Build connection string
    pg_conn = (
        f"PG:host={DB_CONFIG['host']} "
        f"port={DB_CONFIG['port']} "
        f"dbname={DB_CONFIG['dbname']} "
        f"user={DB_CONFIG['user']} "
        f"password={DB_CONFIG['password']}"
    )

    # ogr2ogr command
    cmd = [
        'ogr2ogr',
        '-f', 'PostgreSQL',
        pg_conn,
        SHAPEFILE,
        '-nln', TABLE_NAME,
        '-nlt', 'PROMOTE_TO_MULTI',
        '-lco', 'GEOMETRY_NAME=geom',
        '-lco', 'FID=gid',
        '-lco', 'SPATIAL_INDEX=GIST',
        '-t_srs', 'EPSG:4326',
        '-progress'
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print("\nData loaded successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR loading shapefile: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def print_table_stats():
    """Print table statistics"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cur = conn.cursor()

        print("\nTable Statistics:")

        # Record count
        cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        count = cur.fetchone()[0]
        print(f"  Total records: {count}")

        # Geometry type
        cur.execute(f"SELECT DISTINCT GeometryType(geom) FROM {TABLE_NAME} LIMIT 1")
        geom_type = cur.fetchone()[0]
        print(f"  Geometry type: {geom_type}")

        # SRID
        cur.execute(f"SELECT DISTINCT ST_SRID(geom) FROM {TABLE_NAME} LIMIT 1")
        srid = cur.fetchone()[0]
        print(f"  SRID: {srid}")

        # Columns
        print("\nTable Columns:")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name=%s
            ORDER BY ordinal_position
        """, (TABLE_NAME,))

        for row in cur.fetchall():
            print(f"  - {row[0]}: {row[1]}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"ERROR getting table stats: {e}")


def main():
    """Main function"""
    print("=" * 50)
    print("CI2D3 Data Loading Script")
    print("=" * 50)

    print("\nConfiguration:")
    print(f"  Database Host: {DB_CONFIG['host']}")
    print(f"  Database Port: {DB_CONFIG['port']}")
    print(f"  Database Name: {DB_CONFIG['dbname']}")
    print(f"  Database User: {DB_CONFIG['user']}")
    print(f"  Table Name: {TABLE_NAME}")
    print(f"  Shapefile: {SHAPEFILE}")
    print()

    # Check if shapefile exists
    if not Path(SHAPEFILE).exists():
        print(f"ERROR: Shapefile not found at {SHAPEFILE}")
        sys.exit(1)

    print(f"Shapefile found: {SHAPEFILE}\n")

    # Wait for PostgreSQL
    if not wait_for_postgres():
        sys.exit(1)

    # Check if table exists
    if check_table_exists():
        print(f"\nWARNING: Table '{TABLE_NAME}' already exists!")
        response = input("Do you want to drop and recreate it? (y/N): ")
        if response.lower() == 'y':
            if not drop_table():
                sys.exit(1)
        else:
            print("Keeping existing table. Exiting.")
            sys.exit(0)

    # Load shapefile
    if not load_shapefile():
        sys.exit(1)

    # Print statistics
    print_table_stats()

    print("\n" + "=" * 50)
    print("Data loading completed successfully!")
    print("=" * 50)


if __name__ == '__main__':
    main()
