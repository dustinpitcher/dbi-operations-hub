from flask import Flask, render_template, request, jsonify
import os
import sys
import atexit
from config import get_config
from utils.logging_config import get_logger
from utils.alerting import send_error_alert, send_critical_alert, AlertSeverity
from utils.exceptions import ConfigurationError, DBIOperationsError
from utils.file_cleanup import stop_file_cleanup_service

# Get logger for this module
logger = get_logger(__name__)


def create_app(config_name=None):
    """
    Application factory for the DBI Operations Hub
    
    Args:
        config_name: Configuration to use (development, production, testing)
        
    Returns:
        Flask application instance
    """
    try:
        # Get appropriate configuration
        config_class = get_config(config_name)
        
        # Create Flask app
        app = Flask(__name__)
        app.config.from_object(config_class)
        
        # Initialize configuration (includes environment validation)
        config_class.init_app(app)
        
        logger.info(f"🚀 Creating DBI Operations Hub app with {config_class.__name__}")
        
        # Register cleanup on app shutdown
        atexit.register(stop_file_cleanup_service)
        
        # Register Blueprints
        from modules.assembly import assembly_bp
        from modules.purchase_orders import po_bp
        
        app.register_blueprint(assembly_bp)
        app.register_blueprint(po_bp)
        
        # Register error handlers
        register_error_handlers(app)
        
        # Register main routes
        register_main_routes(app)
        
        logger.info("✅ DBI Operations Hub application created successfully")
        return app
        
    except ConfigurationError as e:
        logger.critical(f"Configuration error during app creation: {e.message}")
        send_critical_alert(e, context={'phase': 'app_creation'})
        raise
    except Exception as e:
        logger.critical(f"Unexpected error during app creation: {str(e)}")
        send_critical_alert(e, context={'phase': 'app_creation'})
        raise


def register_main_routes(app):
    """Register main application routes"""
    
    @app.route('/')
    def index():
        """Main dashboard - choose between modules"""
        try:
            logger.info("Dashboard accessed", extra={'operation': 'dashboard_access'})
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering dashboard: {str(e)}")
            send_error_alert(e, context={'route': 'dashboard'})
            return render_template('errors/500.html'), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for Azure and monitoring"""
        try:
            from utils.file_cleanup import cleanup_manager
            
            health_data = {
                'status': 'healthy',
                'modules': app.config.get('ENABLED_MODULES', []),
                'environment': os.environ.get('FLASK_ENV', 'development'),
                'cleanup_service_running': cleanup_manager.running,
                'timestamp': import_datetime().datetime.now(import_datetime().timezone.utc).isoformat()
            }
            
            logger.debug("Health check accessed", extra={'operation': 'health_check'})
            return jsonify(health_data)
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            send_error_alert(e, AlertSeverity.HIGH, context={'route': 'health_check'})
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': import_datetime().datetime.now(import_datetime().timezone.utc).isoformat()
            }), 500
    
    @app.route('/system/cleanup')
    def manual_cleanup():
        """Manual cleanup endpoint for administrative use"""
        try:
            from utils.file_cleanup import run_manual_cleanup
            
            stats = run_manual_cleanup()
            logger.info(f"Manual cleanup completed", extra={
                'operation': 'manual_cleanup',
                'files_deleted': stats['files_deleted'],
                'bytes_freed': stats['bytes_freed']
            })
            
            return jsonify({
                'status': 'success',
                'message': f"Cleanup completed: deleted {stats['files_deleted']} files, freed {stats['bytes_freed']} bytes",
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Manual cleanup failed: {str(e)}")
            send_error_alert(e, context={'route': 'manual_cleanup'})
            return jsonify({
                'status': 'error',
                'message': f"Cleanup failed: {str(e)}"
            }), 500


def register_error_handlers(app):
    """Register error handlers with alerting"""
    
    @app.errorhandler(ConfigurationError)
    def handle_configuration_error(error):
        """Handle configuration errors"""
        logger.error(f"Configuration error: {error.message}")
        send_critical_alert(error)
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(DBIOperationsError)
    def handle_dbi_operations_error(error):
        """Handle custom DBI operations errors"""
        logger.error(f"DBI Operations error: {error.message}")
        send_error_alert(error, context={'error_code': error.error_code})
        
        if request.is_json:
            return jsonify(error.to_dict()), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        logger.warning(f"404 error: {request.url}")
        
        if request.is_json:
            return jsonify({
                'error': True,
                'message': 'Resource not found',
                'status_code': 404
            }), 404
            
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors with alerting"""
        logger.error(f"500 error: {str(error)}", exc_info=True)
        
        # Send alert for 500 errors
        send_error_alert(
            Exception(f"Internal server error: {str(error)}"),
            AlertSeverity.HIGH,
            context={
                'route': request.endpoint,
                'method': request.method,
                'url': request.url
            }
        )
        
        if request.is_json:
            return jsonify({
                'error': True,
                'message': 'Internal server error',
                'status_code': 500
            }), 500
            
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def file_too_large_error(error):
        """Handle file upload size errors"""
        logger.warning(f"File upload too large: {request.url}")
        
        if request.is_json:
            return jsonify({
                'error': True,
                'message': 'File too large. Maximum size allowed is 50MB.',
                'error_code': 'FILE_TOO_LARGE',
                'status_code': 413
            }), 413
        
        return render_template('errors/500.html'), 413


def import_datetime():
    """Helper function to import datetime module"""
    import datetime
    return datetime


if __name__ == '__main__':
    try:
        # For direct execution, use the module-level app or create a new one
        if 'app' not in globals():
            app = create_app()
        
        # Use PORT environment variable for Azure, default to 5000 for local development
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') == 'development'
        
        logger.info(f"🏢 Starting DBI Operations Hub on port {port}")
        logger.info(f"📊 Modules enabled: {', '.join(app.config.get('ENABLED_MODULES', []))}")
        logger.info(f"🔧 Debug mode: {debug}")
        
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        sys.exit(1)
