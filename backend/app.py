"""
CI2D3 Ice Island Explorer - Flask API Application
Main entry point for the backend API server
"""
from flask import Flask, jsonify
from flask_cors import CORS
from config import config
import os

# Import blueprints
from routes.filter_routes import filter_bp
from routes.inspect_routes import inspect_bp


def create_app(config_name=None):
    """Application factory pattern"""

    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Enable CORS for all routes
    CORS(app, resources={
        r"/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Register blueprints
    app.register_blueprint(inspect_bp, url_prefix='/api/inspect')
    app.register_blueprint(filter_bp, url_prefix='/api/filter')

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for container orchestration"""
        return jsonify({
            'status': 'healthy',
            'service': 'ci2d3-api',
            'version': '1.0.0'
        }), 200

    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """API root endpoint with available routes"""
        return jsonify({
            'message': 'CI2D3 Ice Island Explorer API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'inspect': '/api/inspect/<feature_id>',
                'filter': '/api/filter',
                'attributes': '/api/inspect/attributes'
            }
        }), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
