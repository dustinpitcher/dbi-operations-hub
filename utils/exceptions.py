"""
Custom Exception Types for DBI Operations Hub
Provides specific exception classes for better error handling and debugging.
"""


class DBIOperationsError(Exception):
    """Base exception class for DBI Operations Hub"""
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        """Convert exception to dictionary for JSON responses"""
        return {
            'error': True,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class ConfigurationError(DBIOperationsError):
    """Exception for configuration-related errors"""
    def __init__(self, message: str, missing_vars: list = None):
        details = {'missing_variables': missing_vars} if missing_vars else {}
        super().__init__(message, "CONFIGURATION_ERROR", details)


class DataProcessingError(DBIOperationsError):
    """Exception for data processing errors"""
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if operation:
            details['operation'] = operation
        super().__init__(message, "DATA_PROCESSING_ERROR", details)


class FileOperationError(DBIOperationsError):
    """Exception for file operation errors"""
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if operation:
            details['operation'] = operation
        super().__init__(message, "FILE_OPERATION_ERROR", details)


class ValidationError(DBIOperationsError):
    """Exception for validation errors"""
    def __init__(self, message: str, field: str = None, value: str = None):
        details = {}
        if field:
            details['field'] = field
        if value:
            details['value'] = str(value)
        super().__init__(message, "VALIDATION_ERROR", details)


class BusinessLogicError(DBIOperationsError):
    """Exception for business logic errors"""
    def __init__(self, message: str, module: str = None, operation: str = None):
        details = {}
        if module:
            details['module'] = module
        if operation:
            details['operation'] = operation
        super().__init__(message, "BUSINESS_LOGIC_ERROR", details)


class ExternalServiceError(DBIOperationsError):
    """Exception for external service errors"""
    def __init__(self, message: str, service: str = None, status_code: int = None):
        details = {}
        if service:
            details['service'] = service
        if status_code:
            details['status_code'] = status_code
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)
