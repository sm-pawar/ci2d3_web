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

    Request body:
        {
            "field": "calvingloc",
            "operator": "=",
            "value": "PG"
        }

    Or for multiple filters:
        {
            "filters": [
                {"field": "carving_year", "operator": ">=", "value": 2010},
                {"field": "calvingloc", "operator": "=", "value": "PG"}
            ],
            "logic": "AND"
        }

    Returns:
        GeoJSON FeatureCollection of matching features
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No JSON data provided'
            }), 400

        # Handle single filter
        if 'field' in data:
            field = data.get('field')
            operator = data.get('operator')
            value = data.get('value')

            if not all([field, operator, value is not None]):
                return jsonify({
                    'error': 'Missing required fields: field, operator, value'
                }), 400

            # Sanitize field name
            safe_field = QueryBuilder.sanitize_field_name(field)

            # Execute filter query
            result = db_service.filter_features(safe_field, operator, value)

            return jsonify(result), 200

        # Handle multiple filters
        elif 'filters' in data:
            filters = data.get('filters', [])
            logic = data.get('logic', 'AND')

            if not filters:
                return jsonify({
                    'error': 'No filters provided'
                }), 400

            # Validate and sanitize all field names
            for f in filters:
                if 'field' not in f or 'operator' not in f or 'value' not in f:
                    return jsonify({
                        'error': 'Each filter must have field, operator, and value'
                    }), 400
                f['field'] = QueryBuilder.sanitize_field_name(f['field'])

            # Build combined query
            # For now, execute first filter (can be extended to support multiple)
            # TODO: Implement multi-filter support in db_service
            first_filter = filters[0]
            result = db_service.filter_features(
                first_filter['field'],
                first_filter['operator'],
                first_filter['value']
            )

            return jsonify(result), 200

        else:
            return jsonify({
                'error': 'Invalid request format. Provide either field/operator/value or filters array'
            }), 400

    except ValueError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Failed to filter features',
            'message': str(e)
        }), 500


@filter_bp.route('/test', methods=['GET'])
def test_filter():
    """
    Test endpoint to verify filter functionality

    Returns:
        Sample filtered results
    """
    try:
        # Test query: get all features from Petermann Glacier (PG)
        result = db_service.filter_features('calvingloc', '=', 'PG')

        return jsonify({
            'message': 'Filter test successful',
            'test_query': "calvingloc = 'PG'",
            'result': result
        }), 200

    except Exception as e:
        return jsonify({
            'error': 'Filter test failed',
            'message': str(e)
        }), 500
