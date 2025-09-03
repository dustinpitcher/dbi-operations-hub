"""
WSGI Entry Point for DBI Operations Hub
Provides proper WSGI interface for production deployment with Gunicorn
"""
import os
from app import create_app

# Create the Flask application instance
app = create_app('production')

if __name__ == "__main__":
    app.run()
