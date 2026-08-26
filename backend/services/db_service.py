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

    # Operators accepted by the filter endpoints.
    VALID_OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'ILIKE', 'IN', 'NOT IN']

    @staticmethod
    def _build_condition(field, operator, value, param_name):
        """
        Build a single parameterised WHERE condition.

        Args:
            field: Column name (must already be sanitised by the caller)
            operator: One of VALID_OPERATORS
            value: Value to compare against
            param_name: Unique bind-parameter name for this condition

        Returns:
            (condition_sql, params_dict)
        """
        op = operator.upper()
        if op not in DatabaseService.VALID_OPERATORS:
            raise ValueError(f"Invalid operator: {operator}")

        if op in ['LIKE', 'ILIKE']:
            return f"{field} {operator} :{param_name}", {param_name: f"%{value}%"}

        if op in ['IN', 'NOT IN']:
            values = tuple(value) if isinstance(value, list) else (value,)
            return f"{field} {operator} :{param_name}", {param_name: values}

        return f"{field} {operator} :{param_name}", {param_name: value}

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
        return self.filter_features_multi(
            [{'field': field, 'operator': operator, 'value': value}]
        )

    def filter_features_multi(self, filters, logic='AND'):
        """
        Filter ice island features on one or more attribute criteria.

        Args:
            filters: List of {'field', 'operator', 'value'} dicts. Field names
                     must already be sanitised by the caller (see
                     QueryBuilder.sanitize_field_name).
            logic: How to combine the conditions - 'AND' or 'OR'.

        Returns:
            GeoJSON FeatureCollection of matching features
        """
        if not filters:
            raise ValueError("At least one filter is required")

        logic = (logic or 'AND').upper()
        if logic not in ('AND', 'OR'):
            raise ValueError(f"Invalid logic: {logic}. Use 'AND' or 'OR'.")

        session = self.get_session()
        try:
            # Build one parameterised condition per filter, giving each its own
            # bind-parameter name so repeated fields don't collide.
            conditions = []
            params = {}
            for i, f in enumerate(filters):
                condition, condition_params = self._build_condition(
                    f['field'], f['operator'], f['value'], f'value_{i}'
                )
                conditions.append(condition)
                params.update(condition_params)

            where_clause = f' {logic} '.join(conditions)

            # Get all column names from the table. 'geometry' is excluded along
            # with geom/gid: it is a leftover text column from the source
            # shapefile DBF, not the real PostGIS geometry.
            columns_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'iceislands'
                    AND column_name NOT IN ('geom', 'gid', 'geometry')
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
