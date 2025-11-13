"""
GeoJSON formatting utilities
Converts database results to GeoJSON format
"""
import json
from datetime import date, datetime
from decimal import Decimal


class GeoJSONFormatter:
    """Helper class for formatting data as GeoJSON"""

    @staticmethod
    def serialize_value(value):
        """
        Serialize Python values to JSON-compatible types

        Args:
            value: Any Python value

        Returns:
            JSON-serializable value
        """
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif value is None:
            return None
        else:
            return value

    @staticmethod
    def feature_to_geojson(feature_id, geometry, properties):
        """
        Convert feature data to GeoJSON Feature

        Args:
            feature_id: Feature identifier
            geometry: Geometry object or GeoJSON geometry dict
            properties: Dictionary of feature properties

        Returns:
            GeoJSON Feature dict
        """
        # Serialize all property values
        serialized_props = {
            k: GeoJSONFormatter.serialize_value(v)
            for k, v in properties.items()
        }

        return {
            'type': 'Feature',
            'id': feature_id,
            'geometry': geometry if isinstance(geometry, dict) else json.loads(geometry),
            'properties': serialized_props
        }

    @staticmethod
    def features_to_collection(features):
        """
        Convert list of features to GeoJSON FeatureCollection

        Args:
            features: List of GeoJSON Feature dicts

        Returns:
            GeoJSON FeatureCollection dict
        """
        return {
            'type': 'FeatureCollection',
            'features': features,
            'count': len(features)
        }

    @staticmethod
    def create_empty_collection():
        """Create an empty GeoJSON FeatureCollection"""
        return {
            'type': 'FeatureCollection',
            'features': [],
            'count': 0
        }

    @staticmethod
    def add_bbox(geojson, bbox):
        """
        Add bounding box to GeoJSON object

        Args:
            geojson: GeoJSON dict
            bbox: Bounding box as [minx, miny, maxx, maxy]

        Returns:
            GeoJSON dict with bbox added
        """
        geojson['bbox'] = bbox
        return geojson

    @staticmethod
    def add_crs(geojson, crs='EPSG:4326'):
        """
        Add CRS to GeoJSON object

        Args:
            geojson: GeoJSON dict
            crs: CRS identifier (default: EPSG:4326)

        Returns:
            GeoJSON dict with CRS added
        """
        geojson['crs'] = {
            'type': 'name',
            'properties': {
                'name': f'urn:ogc:def:crs:{crs}'
            }
        }
        return geojson
