"""
GeoServer service for WFS/WMS integration
Handles interactions with GeoServer REST API
"""
import requests
from requests.auth import HTTPBasicAuth
from config import Config
import json


class GeoServerService:
    """Service class for GeoServer operations"""

    def __init__(self):
        """Initialize GeoServer connection"""
        self.base_url = Config.GEOSERVER_URL
        self.workspace = Config.GEOSERVER_WORKSPACE
        self.layer = Config.GEOSERVER_LAYER
        self.auth = HTTPBasicAuth(
            Config.GEOSERVER_USER,
            Config.GEOSERVER_PASSWORD
        )

    def get_wms_capabilities(self):
        """Get WMS GetCapabilities response"""
        url = f"{self.base_url}/wms"
        params = {
            'service': 'WMS',
            'version': '1.3.0',
            'request': 'GetCapabilities'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error getting WMS capabilities: {e}")
            raise

    def get_wfs_feature(self, feature_id):
        """
        Get a specific feature via WFS GetFeature request

        Args:
            feature_id: The feature ID to retrieve

        Returns:
            GeoJSON feature
        """
        url = f"{self.base_url}/wfs"
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeName': f"{self.workspace}:{self.layer}",
            'featureID': feature_id,
            'outputFormat': 'application/json'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting WFS feature: {e}")
            raise

    def query_features_wfs(self, cql_filter):
        """
        Query features using WFS with CQL filter

        Args:
            cql_filter: CQL filter expression

        Returns:
            GeoJSON FeatureCollection
        """
        url = f"{self.base_url}/wfs"
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeName': f"{self.workspace}:{self.layer}",
            'outputFormat': 'application/json',
            'cql_filter': cql_filter,
            'maxFeatures': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error querying WFS features: {e}")
            raise

    def get_layer_info(self):
        """Get layer information from GeoServer REST API"""
        url = f"{self.base_url}/rest/layers/{self.workspace}:{self.layer}.json"

        try:
            response = requests.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting layer info: {e}")
            raise

    def get_layer_bounds(self):
        """Get bounding box of the layer"""
        try:
            layer_info = self.get_layer_info()
            bounds = layer_info.get('layer', {}).get('resource', {}).get('latLonBoundingBox', {})

            return {
                'minx': bounds.get('minx'),
                'miny': bounds.get('miny'),
                'maxx': bounds.get('maxx'),
                'maxy': bounds.get('maxy'),
                'crs': bounds.get('crs')
            }
        except Exception as e:
            print(f"Error getting layer bounds: {e}")
            # Return default Arctic bounds if error
            return {
                'minx': -180,
                'miny': 60,
                'maxx': -40,
                'maxy': 85,
                'crs': 'EPSG:4326'
            }

    def get_wms_url(self):
        """Get WMS URL for the layer"""
        return f"{self.base_url}/wms"

    def get_layer_name(self):
        """Get full layer name"""
        return f"{self.workspace}:{self.layer}"


# Singleton instance
geoserver_service = GeoServerService()
