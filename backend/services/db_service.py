"""
Database service for PostGIS queries
Handles all database interactions for Ice Island data
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from config import Config
from geoalchemy2.functions import ST_AsGeoJSON, ST_Transform
import json


class DatabaseService:
    """Service class for database operations"""

    def __init__(self):
        """Initialize database connection"""
        self.engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            poolclass=NullPool,
            echo=Config.SQLALCHEMY_ECHO
        )
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def get_feature_by_id(self, feature_id):
        """
        Retrieve a single ice island feature by ID

        Args:
            feature_id: The GID or unique identifier of the feature

        Returns:
            Dictionary containing feature properties and geometry
        """
        session = self.get_session()
        try:
            # Query to get feature with geometry as GeoJSON
            query = text("""
                SELECT
                    gid,
                    objectid,
                    ST_AsGeoJSON(ST_Transform(geom, 4326))::json as geometry,
                    *
                FROM iceislands
                WHERE gid = :feature_id
                LIMIT 1
            """)

            result = session.execute(query, {'feature_id': feature_id}).fetchone()

            if result:
                # Convert result to dictionary
                columns = result._mapping.keys()
                feature_dict = dict(zip(columns, result))

                return {
                    'type': 'Feature',
                    'id': feature_dict.get('gid'),
                    'geometry': feature_dict.get('geometry'),
                    'properties': {k: v for k, v in feature_dict.items()
                                   if k not in ['gid', 'geometry', 'geom']}
                }
            return None

        except Exception as e:
            print(f"Error fetching feature: {e}")
            raise
        finally:
            session.close()

    def get_all_attributes(self):
        """
        Get list of all available attribute fields and their data types

        Returns:
            List of dictionaries containing field information
        """
        session = self.get_session()
        try:
            query = text("""
                SELECT
                    column_name,
                    data_type,
                    udt_name
                FROM information_schema.columns
                WHERE table_name = 'iceislands'
                    AND column_name NOT IN ('geom', 'gid')
                ORDER BY ordinal_position
            """)

            results = session.execute(query).fetchall()

            attributes = []
            for row in results:
                attributes.append({
                    'name': row[0],
                    'type': row[1],
                    'udt_name': row[2]
                })

            return attributes

        except Exception as e:
            print(f"Error fetching attributes: {e}")
            raise
        finally:
            session.close()

    def filter_features(self, field, operator, value):
        """
        Filter ice island features based on attribute criteria

        Args:
            field: The attribute field to filter on
            operator: Comparison operator (=, !=, >, <, >=, <=, LIKE, ILIKE)
            value: The value to compare against

        Returns:
            GeoJSON FeatureCollection of matching features
        """
        session = self.get_session()
        try:
            # Validate operator to prevent SQL injection
            valid_operators = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE', 'IN', 'NOT IN']
            if operator.upper() not in valid_operators:
                raise ValueError(f"Invalid operator: {operator}")

            # Build WHERE clause
            if operator.upper() in ['LIKE', 'ILIKE']:
                where_clause = f"{field} {operator} :value"
                params = {'value': f"%{value}%"}
            elif operator.upper() in ['IN', 'NOT IN']:
                # Handle IN operator with list of values
                where_clause = f"{field} {operator} :value"
                params = {'value': tuple(value) if isinstance(value, list) else (value,)}
            else:
                where_clause = f"{field} {operator} :value"
                params = {'value': value}

            # Query to get filtered features with geometry as GeoJSON in WGS84
            query = text(f"""
                SELECT
                    gid,
                    ST_AsGeoJSON(ST_Transform(geom, 4326))::json as geometry,
                    objectid,
                    calvingloc,
                    carving_year,
                    area_km2,
                    perimeter_km,
                    max_length_km,
                    thickness_m,
                    status
                FROM iceislands
                WHERE {where_clause}
                ORDER BY gid
                LIMIT 1000
            """)

            results = session.execute(query, params).fetchall()

            # Build GeoJSON FeatureCollection
            features = []
            for row in results:
                features.append({
                    'type': 'Feature',
                    'id': row[0],  # gid
                    'geometry': row[1],  # geometry as GeoJSON
                    'properties': {
                        'objectid': row[2],
                        'calvingloc': row[3],
                        'carving_year': row[4],
                        'area_km2': row[5],
                        'perimeter_km': row[6],
                        'max_length_km': row[7],
                        'thickness_m': row[8],
                        'status': row[9]
                    }
                })

            return {
                'type': 'FeatureCollection',
                'features': features,
                'count': len(features)
            }

        except Exception as e:
            print(f"Error filtering features: {e}")
            raise
        finally:
            session.close()

    def get_feature_count(self):
        """Get total count of ice island features"""
        session = self.get_session()
        try:
            query = text("SELECT COUNT(*) FROM iceislands")
            result = session.execute(query).scalar()
            return result
        except Exception as e:
            print(f"Error getting feature count: {e}")
            raise
        finally:
            session.close()

    def get_unique_values(self, field):
        """
        Get unique values for a specific field

        Args:
            field: The field name to get unique values for

        Returns:
            List of unique values
        """
        session = self.get_session()
        try:
            query = text(f"""
                SELECT DISTINCT {field}
                FROM iceislands
                WHERE {field} IS NOT NULL
                ORDER BY {field}
                LIMIT 100
            """)

            results = session.execute(query).fetchall()
            return [row[0] for row in results]

        except Exception as e:
            print(f"Error getting unique values: {e}")
            raise
        finally:
            session.close()


# Singleton instance
db_service = DatabaseService()
