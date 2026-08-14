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

            # First, get all column names from the table (except geometry and gid)
            columns_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'iceislands'
                    AND column_name NOT IN ('geom', 'gid')
                ORDER BY ordinal_position
            """)

            column_results = session.execute(columns_query).fetchall()
            column_names = [row[0] for row in column_results]

            # Build the SELECT clause dynamically
            columns_str = ', '.join(column_names)

            # Query to get filtered features with geometry as GeoJSON in WGS84
            query = text(f"""
                SELECT
                    gid,
                    ST_AsGeoJSON(ST_Transform(geom, 4326))::json as geometry,
                    {columns_str}
                FROM iceislands
                WHERE {where_clause}
                ORDER BY gid
                LIMIT 1000
            """)

            results = session.execute(query, params).fetchall()

            # Build GeoJSON FeatureCollection
            features = []
            for row in results:
                # row[0] = gid, row[1] = geometry, row[2:] = all other columns
                properties = {}
                for i, col_name in enumerate(column_names):
                    properties[col_name] = row[i + 2]  # +2 because gid and geometry come first

                features.append({
                    'type': 'Feature',
                    'id': row[0],  # gid
                    'geometry': row[1],  # geometry as GeoJSON
                    'properties': properties
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

    def filter_features_multi(self, filters, logic='AND'):
        """
        Filter features using multiple conditions with AND/OR logic.

        Args:
            filters: List of dicts with keys: field, operator, value
            logic: 'AND' or 'OR' (case-insensitive)

        Returns:
            GeoJSON FeatureCollection of matching features
        """
        if not filters:
            return {'type': 'FeatureCollection', 'features': [], 'count': 0}

        # Validate logic
        logic = logic.upper()
        if logic not in ('AND', 'OR'):
            raise ValueError("logic must be AND or OR")

        # Validate operators
        valid_operators = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE', 'IN', 'NOT IN']
        for f in filters:
            op = f['operator'].upper()
            if op not in valid_operators:
                raise ValueError(f"Invalid operator: {op}")

        # Build WHERE clause parts and parameters
        where_parts = []
        params = {}
        for idx, f in enumerate(filters):
            field = f['field']
            op = f['operator'].upper()
            value = f['value']

            param_name = f"val_{idx}"

            # Handle different operators
            if op in ('LIKE', 'ILIKE'):
                # Add wildcards for LIKE/ILIKE
                where_parts.append(f"{field} {op} :{param_name}")
                params[param_name] = f"%{value}%"
            elif op in ('IN', 'NOT IN'):
                # Expect value to be list/tuple
                if not isinstance(value, (list, tuple)):
                    value = (value,)
                where_parts.append(f"{field} {op} :{param_name}")
                params[param_name] = tuple(value)
            else:
                where_parts.append(f"{field} {op} :{param_name}")
                params[param_name] = value

        where_clause = f" {logic} ".join(where_parts)

        # Get column names
        session = self.get_session()
        try:
            columns_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'iceislands'
                    AND column_name NOT IN ('geom', 'gid')
                ORDER BY ordinal_position
            """)
            column_results = session.execute(columns_query).fetchall()
            column_names = [row[0] for row in column_results]
            columns_str = ', '.join(column_names)

            # Build full query
            query = text(f"""
                SELECT
                    gid,
                    ST_AsGeoJSON(ST_Transform(geom, 4326))::json as geometry,
                    {columns_str}
                FROM iceislands
                WHERE {where_clause}
                ORDER BY gid
                LIMIT 1000
            """)

            results = session.execute(query, params).fetchall()

            # Build GeoJSON
            features = []
            for row in results:
                properties = {}
                for i, col_name in enumerate(column_names):
                    properties[col_name] = row[i + 2]  # +2 for gid, geometry
                features.append({
                    'type': 'Feature',
                    'id': row[0],
                    'geometry': row[1],
                    'properties': properties
                })

            return {
                'type': 'FeatureCollection',
                'features': features,
                'count': len(features)
            }

        except Exception as e:
            print(f"Error filtering features (multi): {e}")
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
