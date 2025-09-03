from flask import render_template, request, jsonify, send_file, url_for
import os
from pathlib import Path
from . import assembly_bp
from .processing import AssemblyProcessor
from utils.file_validation import FileValidator, create_secure_filename
from utils.exceptions import FileOperationError, ValidationError, DataProcessingError
from utils.logging_config import get_logger, LoggerMixin
from utils.alerting import send_error_alert, AlertSeverity

# Get logger for this module
logger = get_logger(__name__)


@assembly_bp.route('/')
def assembly_index():
    """Main assembly generation interface"""
    try:
        logger.info("Assembly interface accessed", extra={'operation': 'assembly_index_access'})
        return render_template('modules/assembly/index.html')
    except Exception as e:
        logger.error(f"Error loading assembly interface: {str(e)}")
        send_error_alert(e, context={'route': 'assembly_index'})
        return render_template('errors/500.html'), 500


@assembly_bp.route('/process', methods=['POST'])
def process_assembly_files():
    """Process uploaded files and generate assembly reports with comprehensive validation"""
    temp_files = []
    
    try:
        logger.info("Assembly processing initiated", extra={'operation': 'process_assembly_files'})
        
        # Get and validate uploaded files
        file_specs = [
            ('availability', 'availability.csv'),
            ('replenishment', 'replenishment.csv'),  
            ('bom', 'bom.xlsx')
        ]
        
        validated_files = {}
        
        for file_key, expected_type in file_specs:
            file_storage = request.files.get(file_key)
            
            if not file_storage or not file_storage.filename:
                raise ValidationError(f"Missing required file: {file_key}", field=file_key)
            
            try:
                # Validate file upload
                validation_result = FileValidator.validate_upload(file_storage)
                
                # Create secure filename
                secure_name = create_secure_filename(file_key, validation_result['original_filename'])
                
                logger.info(f"File validation passed for {file_key}", extra={
                    'operation': 'file_validation',
                    'file_key': file_key,
                    'uploaded_filename': validation_result['secure_filename'],
                    'file_size': validation_result['file_size']
                })
                
                validated_files[file_key] = {
                    'file_storage': file_storage,
                    'secure_name': secure_name,
                    'validation_result': validation_result
                }
                
            except Exception as validation_error:
                logger.warning(f"File validation failed for {file_key}: {str(validation_error)}")
                raise ValidationError(f"File validation failed for {file_key}: {str(validation_error)}")
        
        # Create module-specific upload directory  
        upload_dir = os.path.join('uploads', 'assembly')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save validated files with secure names
        file_paths = {}
        
        for file_key, file_data in validated_files.items():
            file_path = os.path.join(upload_dir, file_data['secure_name'])
            file_data['file_storage'].save(file_path)
            file_paths[file_key] = file_path
            temp_files.append(file_path)
            
            logger.info(f"File saved for processing: {file_key}", extra={
                'operation': 'file_save',
                'file_key': file_key,
                'file_path': file_path
            })
        
        # Process data and generate Excel file
        try:
            processor = AssemblyProcessor()
            results = processor.generate_reports(
                file_paths['availability'],
                file_paths['replenishment'], 
                file_paths['bom'],
                export_excel=True
            )
            
            logger.info("Assembly processing completed successfully", extra={
                'operation': 'assembly_processing_complete',
                'results': results
            })
            
            return jsonify(results)
            
        except Exception as processing_error:
            logger.error(f"Assembly processing failed: {str(processing_error)}")
            raise DataProcessingError(
                f"Assembly processing failed: {str(processing_error)}",
                operation="assembly_processing"
            )
        
    except ValidationError as e:
        logger.warning(f"Validation error in assembly processing: {e.message}")
        return jsonify({
            'error': True,
            'message': f'Validation error: {e.message}',
            'error_code': e.error_code
        }), 400
    
    except DataProcessingError as e:
        logger.error(f"Data processing error: {e.message}")
        send_error_alert(e, context={'operation': 'assembly_processing'})
        return jsonify({
            'error': True,
            'message': f'Processing error: {e.message}',
            'error_code': e.error_code
        }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in assembly processing: {str(e)}", exc_info=True)
        send_error_alert(e, AlertSeverity.HIGH, context={'operation': 'assembly_processing'})
        return jsonify({
            'error': True,
            'message': f'Unexpected error: {str(e)}',
            'error_code': 'UNEXPECTED_ERROR'
        }), 500
        
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {str(cleanup_error)}")


@assembly_bp.route('/download/<filename>')
def download_assembly_file(filename):
    """Download generated Excel report with security validation"""
    try:
        # Validate filename to prevent path traversal
        secure_name = Path(filename).name
        if secure_name != filename:
            logger.warning(f"Potential path traversal attempt: {filename}")
            raise ValidationError("Invalid filename", field="filename", value=filename)
        
        # Check if file exists and is in allowed directory
        file_path = Path(filename)
        if not file_path.exists():
            logger.warning(f"Attempted download of non-existent file: {filename}")
            raise FileOperationError(f"File not found: {filename}")
        
        # Additional security: ensure file is in current directory or subdirectory
        try:
            file_path.resolve().relative_to(Path.cwd())
        except ValueError:
            logger.warning(f"Attempted download of file outside working directory: {filename}")
            raise ValidationError("File access denied", field="filename", value=filename)
        
        logger.info(f"File download initiated: {filename}", extra={
            'operation': 'file_download',
            'download_filename': filename
        })
        
        return send_file(filename, as_attachment=True, download_name=filename)
        
    except ValidationError as e:
        logger.warning(f"Validation error in file download: {e.message}")
        return jsonify({
            'error': True,
            'message': f'Download error: {e.message}',
            'error_code': e.error_code
        }), 400
    
    except FileOperationError as e:
        logger.error(f"File operation error: {e.message}")
        return jsonify({
            'error': True,
            'message': f'File error: {e.message}',
            'error_code': e.error_code
        }), 404
    
    except Exception as e:
        logger.error(f"Unexpected error in file download: {str(e)}")
        send_error_alert(e, context={'operation': 'file_download', 'filename': filename})
        return jsonify({
            'error': True,
            'message': f'Download failed: {str(e)}',
            'error_code': 'DOWNLOAD_ERROR'
        }), 500
