"""
Inspection routes - Feature inspection endpoints
Handles retrieving individual feature information
"""
from flask import Blueprint, jsonify, request
from services.db_service import db_service

inspect_bp = Blueprint('inspect', __name__)


@inspect_bp.route('/<int:feature_id>', methods=['GET'])
def inspect_feature(feature_id):
    """
    Get detailed information about a specific ice island feature

    Args:
        feature_id: The GID of the feature to inspect

    Returns:
        JSON response with feature data
    """
    try:
        feature = db_service.get_feature_by_id(feature_id)

        if feature:
            return jsonify(feature), 200
        else:
            return jsonify({
                'error': 'Feature not found',
                'feature_id': feature_id
            }), 404

    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve feature',
            'message': str(e)
        }), 500


@inspect_bp.route('/attributes', methods=['GET'])
def get_attributes():
    """
    Get list of available attributes for filtering

    Returns:
        JSON response with attribute metadata
    """
    try:
        attributes = db_service.get_all_attributes()

        return jsonify({
            'attributes': attributes,
            'count': len(attributes)
        }), 200

    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve attributes',
            'message': str(e)
        }), 500


@inspect_bp.route('/count', methods=['GET'])
def get_feature_count():
    """
    Get total count of ice island features

    Returns:
        JSON response with feature count
    """
    try:
        count = db_service.get_feature_count()

        return jsonify({
            'count': count,
            'table': 'iceislands'
        }), 200

    except Exception as e:
        return jsonify({
            'error': 'Failed to get feature count',
            'message': str(e)
        }), 500


@inspect_bp.route('/unique/<field>', methods=['GET'])
def get_unique_values(field):
    """
    Get unique values for a specific field

    Args:
        field: The field name to get unique values for

    Returns:
        JSON response with unique values
    """
    try:
        # Sanitize field name
        from utils.query_builder import QueryBuilder
        safe_field = QueryBuilder.sanitize_field_name(field)

        values = db_service.get_unique_values(safe_field)

        return jsonify({
            'field': safe_field,
            'values': values,
            'count': len(values)
        }), 200

    except ValueError as e:
        return jsonify({
            'error': 'Invalid field name',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Failed to get unique values',
            'message': str(e)
        }), 500
