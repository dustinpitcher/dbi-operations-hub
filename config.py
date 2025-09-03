import os
from utils.environment import validate_environment, EnvironmentValidator
from utils.logging_config import setup_logging, get_logger
from utils.file_cleanup import start_file_cleanup_service
from utils.exceptions import ConfigurationError

logger = get_logger(__name__)


class Config:
    """Configuration class for DBI Operations Hub"""
    
    # Environment validation
    _env_validated = False
    _validated_vars = {}
    
    # Flask configuration - will be set after environment validation
    SECRET_KEY = None
    
    # Upload folder configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    STAGING_FOLDER = os.path.join(os.path.dirname(__file__), 'staging')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    
    # Azure configuration
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    
    # Module configuration
    ENABLED_MODULES = [
        'assembly',
        'purchase_orders',
        # 'analytics',
        # 'hr',
        # 'quality_control'
    ]
    
    # Business logic defaults
    TARGET_DAYS_INVENTORY = 30
    ASSEMBLY_SAFETY_BUFFER_DAYS = 3
    PO_LEAD_TIME_BUFFER_DAYS = 3
    
    # File cleanup configuration
    FILE_CLEANUP_ENABLED = True
    FILE_CLEANUP_INTERVAL_HOURS = 24
    
    @classmethod
    def validate_environment(cls):
        """Validate environment variables before app initialization"""
        if not cls._env_validated:
            try:
                cls._validated_vars = validate_environment()
                cls.SECRET_KEY = cls._validated_vars.get('SECRET_KEY')
                cls._env_validated = True
                logger.info("✅ Environment validation completed successfully")
            except ConfigurationError as e:
                logger.critical(f"❌ Environment validation failed: {e.message}")
                raise
    
    @staticmethod
    def init_app(app):
        """Initialize application with validated configuration"""
        try:
            # Validate environment first
            Config.validate_environment()
            
            # Ensure Flask gets the validated SECRET_KEY
            if Config.SECRET_KEY:
                app.config['SECRET_KEY'] = Config.SECRET_KEY
            
            # Setup structured logging
            app_logger = setup_logging()
            app_logger.info("🔧 Initializing DBI Operations Hub")
            
            # Ensure directories exist
            directories_to_create = [
                Config.UPLOAD_FOLDER,
                Config.STAGING_FOLDER,
                'logs'  # For logging and cleanup
            ]
            
            for directory in directories_to_create:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Created directory: {directory}")
            
            # Create module-specific upload folders
            for module in Config.ENABLED_MODULES:
                module_upload_path = os.path.join(Config.UPLOAD_FOLDER, module)
                module_staging_path = os.path.join(Config.STAGING_FOLDER, module)
                os.makedirs(module_upload_path, exist_ok=True)
                os.makedirs(module_staging_path, exist_ok=True)
                logger.debug(f"Created module directories for: {module}")
            
            # Start file cleanup service
            if Config.FILE_CLEANUP_ENABLED:
                start_file_cleanup_service(Config.FILE_CLEANUP_INTERVAL_HOURS)
                logger.info("🧹 File cleanup service started")
            
            logger.info("✅ Application initialization completed successfully")
            
        except Exception as e:
            logger.critical(f"❌ Application initialization failed: {str(e)}")
            raise ConfigurationError(f"Application initialization failed: {str(e)}")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # More restrictive file upload limits for production
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB in production
    
    # More frequent cleanup in production
    FILE_CLEANUP_INTERVAL_HOURS = 12


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    
    # Use in-memory or temporary directories for testing
    import tempfile
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'dbi_test_uploads')
    STAGING_FOLDER = os.path.join(tempfile.gettempdir(), 'dbi_test_staging')
    
    # Disable file cleanup during testing
    FILE_CLEANUP_ENABLED = False


# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration class based on environment"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config_map.get(config_name, config_map['default'])
