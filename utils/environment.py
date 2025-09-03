"""
Environment Variable Validation for DBI Operations Hub
Validates required environment variables on startup with clear error messages.
"""
import os
import secrets
from typing import Dict, List, Optional, Tuple
from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger(__name__)


class EnvironmentValidator:
    """Validates environment variables and provides clear error messages"""
    
    # Required environment variables for production
    REQUIRED_PRODUCTION_VARS = [
        'SECRET_KEY',
        'FLASK_ENV',
    ]
    
    # Optional but recommended variables
    RECOMMENDED_VARS = [
        'AZURE_STORAGE_CONNECTION_STRING',
        'LOG_LEVEL',
        'PORT'
    ]
    
    # Variables that should not have default values in production
    NO_DEFAULTS_IN_PRODUCTION = [
        'SECRET_KEY'
    ]
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment"""
        env = os.environ.get('FLASK_ENV', 'development').lower()
        return env in ['production', 'prod']
    
    @staticmethod
    def validate_secret_key() -> str:
        """
        Validate and return secret key, generating one if needed
        
        Returns:
            Valid secret key
            
        Raises:
            ConfigurationError: If secret key is invalid in production
        """
        secret_key = os.environ.get('SECRET_KEY')
        
        if EnvironmentValidator.is_production():
            if not secret_key:
                logger.error("SECRET_KEY not set in production environment")
                raise ConfigurationError(
                    "SECRET_KEY environment variable is required in production",
                    missing_vars=['SECRET_KEY']
                )
            
            if secret_key == 'dev-key-change-in-production':
                logger.error("Default development SECRET_KEY detected in production")
                raise ConfigurationError(
                    "Development SECRET_KEY detected in production. Please set a secure SECRET_KEY environment variable.",
                    missing_vars=['SECRET_KEY']
                )
            
            if len(secret_key) < 32:
                logger.error("SECRET_KEY too short in production")
                raise ConfigurationError(
                    "SECRET_KEY must be at least 32 characters long in production",
                    missing_vars=['SECRET_KEY']
                )
        
        # Generate secure key for development if not set
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
            logger.info("Generated secure SECRET_KEY for development environment")
        
        return secret_key
    
    @staticmethod
    def validate_required_vars() -> Dict[str, str]:
        """
        Validate all required environment variables
        
        Returns:
            Dictionary of validated environment variables
            
        Raises:
            ConfigurationError: If required variables are missing
        """
        missing_vars = []
        invalid_vars = []
        validated_vars = {}
        
        # Check required variables
        for var in EnvironmentValidator.REQUIRED_PRODUCTION_VARS:
            value = os.environ.get(var)
            
            if var == 'SECRET_KEY':
                # Special handling for secret key
                try:
                    validated_vars[var] = EnvironmentValidator.validate_secret_key()
                except ConfigurationError:
                    missing_vars.append(var)
                continue
            
            if EnvironmentValidator.is_production() and not value:
                missing_vars.append(var)
            else:
                validated_vars[var] = value
        
        # Check Azure storage connection string if provided
        azure_conn = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if azure_conn:
            if not azure_conn.startswith('DefaultEndpointsProtocol='):
                invalid_vars.append('AZURE_STORAGE_CONNECTION_STRING')
                logger.warning("AZURE_STORAGE_CONNECTION_STRING appears to be invalid format")
        
        # Report errors
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg, missing_vars=missing_vars)
        
        if invalid_vars:
            error_msg = f"Invalid environment variables: {', '.join(invalid_vars)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        return validated_vars
    
    @staticmethod
    def get_environment_info() -> Dict[str, any]:
        """Get comprehensive environment information"""
        env_info = {
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'is_production': EnvironmentValidator.is_production(),
            'port': os.environ.get('PORT', '5000'),
            'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
            'has_azure_storage': bool(os.environ.get('AZURE_STORAGE_CONNECTION_STRING')),
            'python_version': os.sys.version,
            'platform': os.name,
        }
        
        return env_info
    
    @staticmethod
    def log_startup_info():
        """Log environment information on startup"""
        env_info = EnvironmentValidator.get_environment_info()
        
        logger.info("🏢 DBI Operations Hub starting up")
        logger.info(f"Environment: {env_info['environment']}")
        logger.info(f"Production mode: {env_info['is_production']}")
        logger.info(f"Port: {env_info['port']}")
        logger.info(f"Log level: {env_info['log_level']}")
        logger.info(f"Azure Storage: {'configured' if env_info['has_azure_storage'] else 'not configured'}")
        
        # Warn about missing recommended variables
        missing_recommended = []
        for var in EnvironmentValidator.RECOMMENDED_VARS:
            if not os.environ.get(var):
                missing_recommended.append(var)
        
        if missing_recommended:
            logger.warning(f"Recommended environment variables not set: {', '.join(missing_recommended)}")


def validate_environment() -> Dict[str, str]:
    """
    Validate environment variables and return validated configuration
    
    Returns:
        Dictionary of validated environment variables
        
    Raises:
        ConfigurationError: If validation fails
    """
    try:
        validator = EnvironmentValidator()
        validated_vars = validator.validate_required_vars()
        validator.log_startup_info()
        return validated_vars
    except ConfigurationError as e:
        logger.error(f"Environment validation failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during environment validation: {str(e)}")
        raise ConfigurationError(f"Environment validation failed: {str(e)}")


def generate_secure_secret_key() -> str:
    """Generate a secure secret key for development/testing"""
    return secrets.token_urlsafe(32)
