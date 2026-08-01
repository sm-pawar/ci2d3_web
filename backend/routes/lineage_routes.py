"""
Lineage routes - Ice island lineage tracking endpoints.

Exposes the lineage-tree traversal (ported from ref/python/ci2d3.py) so the
website's "Track Lineage" button can retrieve every ice island polygon that
belongs to the same rooted lineage tree as a selected feature.
"""
from flask import Blueprint, jsonify, request
from services.lineage_service import lineage_service

lineage_bp = Blueprint('lineage', __name__)


@lineage_bp.route('/', methods=['POST'])
def track_lineage():
    """
    Track the lineage tree for a selected ice island.

    Request body:
        {
            "inst": "20080713_235233_es_0_JWC",
            "mode": "chain"   # optional, default "chain".
                              # "chain"  = ancestors + descendants of this obs
                              # "after"  = descendants only
                              # "before" = ancestors only
                              # "all"    = whole connected component (large)
        }

    Returns:
        GeoJSON FeatureCollection of the ice island polygons in the lineage.
    """
    try:
        data = request.get_json()

        if not data or 'inst' not in data:
            return jsonify({
                'error': "Missing required field: 'inst'"
            }), 400

        inst = data.get('inst')
        mode = data.get('mode', 'chain')

        result = lineage_service.get_lineage(inst, mode=mode)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Failed to track lineage',
            'message': str(e)
        }), 500


@lineage_bp.route('/<path:inst>', methods=['GET'])
def track_lineage_get(inst):
    """
    Convenience GET endpoint for lineage tracking.

    Note: `inst` values can contain characters that are awkward in URLs; the
    POST endpoint is preferred for the web client. This is provided mainly for
    quick testing.

    Query params:
        mode: "all" (default) | "after" | "before"

    Returns:
        GeoJSON FeatureCollection of all ice island polygons in the lineage.
    """
    try:
        mode = request.args.get('mode', 'chain')
        result = lineage_service.get_lineage(inst, mode=mode)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Failed to track lineage',
            'message': str(e)
        }), 500
