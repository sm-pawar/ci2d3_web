"""
Filter routes - Attribute-based filtering endpoints
Handles dynamic querying of ice island features
"""
from flask import Blueprint, jsonify, request
from services.db_service import db_service
from utils.query_builder import QueryBuilder

filter_bp = Blueprint('filter', __name__)


@filter_bp.route('/', methods=['POST'])
def filter_features():
    """
    Filter ice island features based on attribute criteria

    Request body (single filter):
        {
            "field": "calvingloc",
            "operator": "=",
            "value": "PG"
        }

    Request body (multiple filters – AND / OR):
        {
            "filters": [
                {"field": "area", "operator": ">", "value": 100},
                {"field": "calvingloc", "operator": "=", "value": "PG"}
            ],
            "logic": "AND"   # optional, defaults to "AND"
        }

    Returns:
        GeoJSON FeatureCollection of matching features
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # ---------- Normalise to a list of filters ----------
        filters = []
        logic = 'AND'   # default

        if 'field' in data:
            # Single filter format
            filters = [{
                'field': data['field'],
                'operator': data['operator'],
                'value': data['value']
            }]
        elif 'filters' in data:
            # Multi‑filter format
            filters = data.get('filters', [])
            logic = data.get('logic', 'AND').upper()
            if logic not in ('AND', 'OR'):
                return jsonify({'error': 'logic must be AND or OR'}), 400
        else:
            return jsonify({
                'error': 'Invalid request. Provide either field/operator/value or filters array.'
            }), 400

        # Validate all filters
        if not filters:
            return jsonify({'error': 'No filters provided'}), 400

        for f in filters:
            if not all(k in f for k in ('field', 'operator', 'value')):
                return jsonify({
                    'error': 'Each filter must have field, operator, and value'
                }), 400
            # Sanitise field name (whitelist)
            f['field'] = QueryBuilder.sanitize_field_name(f['field'])

        # ---------- Execute combined filter ----------
        result = db_service.filter_features_multi(filters, logic)

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': 'Validation error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to filter features', 'message': str(e)}), 500


@filter_bp.route('/test', methods=['GET'])
def test_filter():
    """Test endpoint – returns sample filtered results."""
    try:
        result = db_service.filter_features('calvingloc', '=', 'PG')
        return jsonify({
            'message': 'Filter test successful',
            'test_query': "calvingloc = 'PG'",
            'result': result
        }), 200
    except Exception as e:
        return jsonify({'error': 'Filter test failed', 'message': str(e)}), 500