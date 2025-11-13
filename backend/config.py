"""
Configuration settings for the CI2D3 Flask API
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'ci2d3_db')
    DB_USER = os.getenv('DB_USER', 'geoserver')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'geoserver123')

    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # GeoServer configuration
    GEOSERVER_URL = os.getenv('GEOSERVER_URL', 'http://localhost:8080/geoserver')
    GEOSERVER_WORKSPACE = os.getenv('GEOSERVER_WORKSPACE', 'ci2d3')
    GEOSERVER_LAYER = os.getenv('GEOSERVER_LAYER', 'iceislands')
    GEOSERVER_USER = os.getenv('GEOSERVER_USER', 'admin')
    GEOSERVER_PASSWORD = os.getenv('GEOSERVER_PASSWORD', 'geoserver')

    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # Application settings
    ITEMS_PER_PAGE = 100
    MAX_ITEMS = 1000


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
