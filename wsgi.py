"""
WSGI Entry Point for DBI Operations Hub
Provides proper WSGI interface for production deployment with Gunicorn
"""
import os


def create_wsgi_app():
    """Create the Flask application instance for WSGI"""
    from app import create_app
    
    # Determine config based on environment
    config_name = os.environ.get('FLASK_ENV', 'production')
    return create_app(config_name)


# Create the Flask application instance for Gunicorn
app = create_wsgi_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
