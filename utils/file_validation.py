"""
File Upload Validation Utilities
Provides secure file upload validation with extension checking, MIME type verification, 
and filename sanitization for the DBI Operations Hub.
"""
import os
import re
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class UnsupportedFileTypeError(FileValidationError):
    """Exception for unsupported file types"""
    def __init__(self, filename: str, allowed_extensions: List[str]):
        message = f"File '{filename}' has unsupported type. Allowed: {', '.join(allowed_extensions)}"
        super().__init__(message, "UNSUPPORTED_FILE_TYPE")


class FileSizeError(FileValidationError):
    """Exception for file size violations"""
    def __init__(self, filename: str, size: int, max_size: int):
        message = f"File '{filename}' ({size} bytes) exceeds maximum size ({max_size} bytes)"
        super().__init__(message, "FILE_SIZE_EXCEEDED")


class FileValidator:
    """
    Comprehensive file validation for secure uploads
    """
    
    # Allowed file extensions and their corresponding MIME types
    ALLOWED_EXTENSIONS = {
        '.csv': ['text/csv', 'application/csv', 'text/plain'],
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        '.xls': ['application/vnd.ms-excel']
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        '.csv': 50 * 1024 * 1024,    # 50MB for CSV files
        '.xlsx': 100 * 1024 * 1024,  # 100MB for Excel files
        '.xls': 100 * 1024 * 1024    # 100MB for legacy Excel files
    }
    
    # Dangerous filename patterns to reject
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'\.\.\\', # Windows path traversal
        r'^\./',   # Hidden files
        r'^\.\\',  # Windows hidden files
        r'[<>:"|?*]',  # Invalid filename characters
        r'^\s+|\s+$',  # Leading/trailing whitespace
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)',  # Windows reserved names
    ]
    
    @staticmethod
    def validate_filename(filename: str) -> str:
        """
        Validate and sanitize filename
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
            
        Raises:
            FileValidationError: If filename is invalid
        """
        if not filename or not filename.strip():
            raise FileValidationError("Filename cannot be empty", "EMPTY_FILENAME")
        
        # Check for dangerous patterns
        for pattern in FileValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                raise FileValidationError(
                    f"Filename contains invalid characters or patterns: {filename}",
                    "INVALID_FILENAME"
                )
        
        # Sanitize filename using werkzeug's secure_filename
        secure_name = secure_filename(filename)
        if not secure_name:
            raise FileValidationError(
                f"Filename could not be sanitized: {filename}",
                "FILENAME_SANITIZATION_FAILED"
            )
        
        return secure_name
    
    @staticmethod
    def validate_extension(filename: str) -> str:
        """
        Validate file extension
        
        Args:
            filename: Filename to validate
            
        Returns:
            Normalized extension (lowercase with dot)
            
        Raises:
            UnsupportedFileTypeError: If extension not allowed
        """
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        if extension not in FileValidator.ALLOWED_EXTENSIONS:
            allowed_exts = list(FileValidator.ALLOWED_EXTENSIONS.keys())
            raise UnsupportedFileTypeError(filename, allowed_exts)
        
        return extension
    
    @staticmethod
    def validate_mime_type(file_storage: FileStorage, expected_extension: str) -> bool:
        """
        Validate MIME type matches expected extension
        
        Args:
            file_storage: Flask file storage object
            expected_extension: Expected file extension
            
        Returns:
            True if MIME type is valid
            
        Raises:
            FileValidationError: If MIME type doesn't match
        """
        # Get MIME type from file
        mime_type = file_storage.content_type
        
        # Also check with mimetypes module as backup
        guessed_mime, _ = mimetypes.guess_type(file_storage.filename or '')
        
        allowed_mimes = FileValidator.ALLOWED_EXTENSIONS.get(expected_extension, [])
        
        # Check if either the provided or guessed MIME type is allowed
        if mime_type in allowed_mimes or guessed_mime in allowed_mimes:
            return True
        
        raise FileValidationError(
            f"MIME type '{mime_type}' doesn't match expected type for {expected_extension} files. "
            f"Expected: {', '.join(allowed_mimes)}",
            "INVALID_MIME_TYPE"
        )
    
    @staticmethod
    def validate_file_size(file_storage: FileStorage, extension: str) -> int:
        """
        Validate file size
        
        Args:
            file_storage: Flask file storage object
            extension: File extension
            
        Returns:
            File size in bytes
            
        Raises:
            FileSizeError: If file exceeds size limit
        """
        # Seek to end to get file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)  # Reset to beginning
        
        max_size = FileValidator.MAX_FILE_SIZES.get(extension, 50 * 1024 * 1024)  # Default 50MB
        
        if file_size > max_size:
            raise FileSizeError(file_storage.filename or 'unknown', file_size, max_size)
        
        return file_size
    
    @classmethod
    def validate_upload(cls, file_storage: FileStorage) -> Dict[str, any]:
        """
        Comprehensive file validation
        
        Args:
            file_storage: Flask file storage object from request.files
            
        Returns:
            Dictionary with validation results
            
        Raises:
            FileValidationError: If validation fails
        """
        if not file_storage or not file_storage.filename:
            raise FileValidationError("No file provided", "NO_FILE")
        
        # Step 1: Validate and sanitize filename
        original_filename = file_storage.filename
        secure_name = cls.validate_filename(original_filename)
        
        # Step 2: Validate extension
        extension = cls.validate_extension(secure_name)
        
        # Step 3: Validate MIME type
        cls.validate_mime_type(file_storage, extension)
        
        # Step 4: Validate file size
        file_size = cls.validate_file_size(file_storage, extension)
        
        return {
            'original_filename': original_filename,
            'secure_filename': secure_name,
            'extension': extension,
            'file_size': file_size,
            'mime_type': file_storage.content_type,
            'validation_passed': True
        }


def create_secure_filename(file_type: str, original_filename: str) -> str:
    """
    Create a secure filename with type prefix for staging
    
    Args:
        file_type: Type of file (sales, inventory, etc.)
        original_filename: Original filename
        
    Returns:
        Secure filename with prefix
    """
    import time
    import hashlib
    
    # Get secure base filename
    secure_name = FileValidator.validate_filename(original_filename)
    
    # Create timestamp-based hash for uniqueness
    timestamp = str(int(time.time()))
    name_hash = hashlib.md5(secure_name.encode()).hexdigest()[:8]
    
    # Combine type, timestamp, hash, and original name
    file_path = Path(secure_name)
    stem = file_path.stem
    extension = file_path.suffix
    
    secure_filename = f"{file_type}_{timestamp}_{name_hash}_{stem}{extension}"
    
    return secure_filename
