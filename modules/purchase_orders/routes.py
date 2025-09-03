from flask import render_template, request, jsonify, send_from_directory, redirect, url_for, session
import os
import shutil
from . import po_bp
from .processing import validate_sales_report, validate_replenishment_report, validate_inventory_list, validate_availability_report, run_po_generation
from utils.file_validation import FileValidator, create_secure_filename
from utils.exceptions import FileOperationError, ValidationError, DataProcessingError
from utils.logging_config import get_logger, LoggerMixin
from utils.alerting import send_error_alert, AlertSeverity

# Get logger for this module
logger = get_logger(__name__)


class PurchaseOrderRoutes(LoggerMixin):
    """Purchase Order routes with logging capabilities"""
    pass


# Create routes instance for logging
routes_logger = PurchaseOrderRoutes()


@po_bp.route('/')
def po_index():
    """Main purchase order generation interface"""
    try:
        # Clear any previous session data
        session.clear()
        logger.info("Purchase order interface accessed", extra={'operation': 'po_index_access'})
        return render_template('modules/purchase_orders/index.html')
    except Exception as e:
        logger.error(f"Error loading purchase order interface: {str(e)}")
        send_error_alert(e, context={'route': 'po_index'})
        return render_template('modules/purchase_orders/error.html', 
                             message="Failed to load purchase order interface"), 500


@po_bp.route('/upload-file', methods=['POST'])
def upload_single_file():
    """Handle individual file uploads with comprehensive validation."""
    file_storage = None
    temp_path = None
    
    try:
        file_storage = request.files.get('file')
        file_type = request.form.get('file_type')
        
        logger.info(f"File upload initiated", extra={
            'operation': 'file_upload',
            'file_type': file_type,
            'uploaded_filename': file_storage.filename if file_storage else None
        })
        
        # Basic validation
        if not file_storage or not file_storage.filename:
            return jsonify({'valid': False, 'message': '❌ No file selected'})
        
        if not file_type:
            return jsonify({'valid': False, 'message': '❌ File type not specified'})
        
        # Comprehensive file validation
        try:
            validation_result = FileValidator.validate_upload(file_storage)
            logger.info(f"File validation passed", extra={
                'operation': 'file_validation',
                'file_type': file_type,
                'secure_filename': validation_result['secure_filename'],
                'file_size': validation_result['file_size']
            })
        except Exception as validation_error:
            logger.warning(f"File validation failed: {str(validation_error)}")
            return jsonify({
                'valid': False, 
                'message': f'❌ File validation failed: {str(validation_error)}'
            })
        
        # Create secure filename
        secure_name = create_secure_filename(file_type, validation_result['original_filename'])
        
        # Create module-specific staging directory
        staging_dir = os.path.join('staging', 'purchase_orders')
        os.makedirs(staging_dir, exist_ok=True)
        
        # Save file to staging area with secure filename
        temp_path = os.path.join(staging_dir, secure_name)
        file_storage.save(temp_path)
        
        logger.info(f"File saved to staging", extra={
            'operation': 'file_save',
            'file_type': file_type,
            'staging_path': temp_path
        })
        
        # Validate file content based on type
        try:
            if file_type == 'sales':
                content_result = validate_sales_report(temp_path)
            elif file_type == 'replenishment':
                content_result = validate_replenishment_report(temp_path)
            elif file_type == 'inventory':
                content_result = validate_inventory_list(temp_path)
            elif file_type == 'availability':
                content_result = validate_availability_report(temp_path)
            else:
                raise ValidationError(f"Unknown file type: {file_type}", field="file_type", value=file_type)
            
            logger.info(f"Content validation completed", extra={
                'operation': 'content_validation',
                'file_type': file_type,
                'validation_result': content_result.get('valid', False)
            })
            
        except Exception as content_error:
            logger.error(f"Content validation failed: {str(content_error)}")
            # Clean up file on content validation failure
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify({
                'valid': False,
                'message': f'❌ Content validation failed: {str(content_error)}'
            })
        
        # Store validation result in session
        if 'validated_files' not in session:
            session['validated_files'] = {}
        
        if content_result.get('valid', False):
            session['validated_files'][file_type] = {
                'filename': validation_result['original_filename'],
                'secure_filename': secure_name,
                'path': temp_path,
                'message': content_result['message'],
                'file_size': validation_result['file_size'],
                'upload_timestamp': _import_datetime().datetime.now(_import_datetime().timezone.utc).isoformat()
            }
            
            logger.info(f"File upload completed successfully", extra={
                'operation': 'file_upload_success',
                'file_type': file_type,
                'original_filename': validation_result['original_filename']
            })
        
        return jsonify(content_result)
        
    except ValidationError as e:
        logger.warning(f"Validation error during file upload: {e.message}")
        return jsonify({'valid': False, 'message': f'❌ {e.message}'})
    
    except FileOperationError as e:
        logger.error(f"File operation error: {e.message}")
        send_error_alert(e, context={'file_type': file_type, 'operation': 'file_upload'})
        return jsonify({'valid': False, 'message': f'❌ File operation failed: {e.message}'})
    
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}", exc_info=True)
        send_error_alert(e, AlertSeverity.HIGH, context={
            'file_type': file_type, 
            'operation': 'file_upload',
            'uploaded_filename': file_storage.filename if file_storage else None
        })
        
        # Clean up on error
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        
        return jsonify({'valid': False, 'message': f'❌ Unexpected error: {str(e)}'})


@po_bp.route('/generate-po')
def generate_po():
    """Generate PO after all files are validated."""
    try:
        location = request.args.get('location', 'nc')
        
        # Create module-specific staging and upload directories
        staging_dir = os.path.join('staging', 'purchase_orders')
        upload_dir = os.path.join('uploads', 'purchase_orders')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Check staging folder directly instead of relying on session
        if not os.path.exists(staging_dir):
            return render_template('modules/purchase_orders/error.html', 
                                 message='No files uploaded yet. Please upload files first.')
        
        staging_files = os.listdir(staging_dir)
        available_types = []
        for f in staging_files:
            if f.startswith('sales_'):
                available_types.append('sales')
            elif f.startswith('replenishment_'):
                available_types.append('replenishment')
            elif f.startswith('inventory_'):
                available_types.append('inventory')
            elif f.startswith('availability_'):
                available_types.append('availability')
        
        required_files = ['sales', 'replenishment', 'inventory', 'availability']
        missing_files = [f for f in required_files if f not in available_types]
        
        if missing_files:
            return render_template('modules/purchase_orders/error.html',
                                 message=f'Missing files: {", ".join(missing_files)}')
        
        # Clear upload folder and copy validated files with standardized names
        for f in os.listdir(upload_dir):
            os.remove(os.path.join(upload_dir, f))
        
        # Copy files with standardized names for processing
        file_mapping = {
            'sales': 'Sales by Product Details Report.xlsx',
            'replenishment': f'replenishment-Combined {location.upper()} Warehouses-variants-temp.csv',
            'inventory': 'InventoryList_temp.csv', 
            'availability': 'AvailabilityReport_temp.csv'
        }
        
        for file_type, standard_name in file_mapping.items():
            if file_type in available_types:
                # Find the most recent staging file for this type
                staging_file = None
                latest_time = 0
                for f in staging_files:
                    if f.startswith(f'{file_type}_'):
                        file_path = os.path.join(staging_dir, f)
                        file_time = os.path.getmtime(file_path)
                        if file_time > latest_time:
                            latest_time = file_time
                            staging_file = f
                
                if staging_file:
                    staging_path = os.path.join(staging_dir, staging_file)
                    upload_path = os.path.join(upload_dir, standard_name)
                    shutil.copy2(staging_path, upload_path)
        
        # Generate PO
        output_filename = run_po_generation(upload_dir, location)
        
        if output_filename:
            return render_template('modules/purchase_orders/success.html',
                                 location=location.upper(),
                                 download_url=url_for('purchase_orders.download_po_file', filename=output_filename))
        else:
            return render_template('modules/purchase_orders/error.html',
                                 message=f'Could not generate PO for {location.upper()} warehouse.')
            
    except Exception as e:
        return render_template('modules/purchase_orders/error.html',
                             message=f'An error occurred: {str(e)}')


@po_bp.route('/download/<filename>')
def download_po_file(filename):
    """Download generated PO file"""
    return send_from_directory('.', filename, as_attachment=True)


@po_bp.route('/manage-suppliers', methods=['GET', 'POST'])
def manage_suppliers():
    """Supplier exclusion management interface"""
    if request.method == 'POST':
        # Save the updated supplier list
        suppliers_text = request.form.get('suppliers', '')
        suppliers_list = [line.strip() for line in suppliers_text.split('\n') if line.strip()]
        
        try:
            with open('excluded_suppliers.txt', 'w') as f:
                f.write('\n'.join(suppliers_list))
            return render_template('modules/purchase_orders/manage_suppliers.html',
                                 suppliers_text='\n'.join(suppliers_list),
                                 supplier_count=len(suppliers_list),
                                 message="✅ Excluded suppliers list updated successfully!")
        except Exception as e:
            return render_template('modules/purchase_orders/manage_suppliers.html',
                                 suppliers_text=suppliers_text,
                                 supplier_count=len(suppliers_list),
                                 message=f"❌ Error saving suppliers: {str(e)}")
    
    # Load current suppliers for display
    try:
        if os.path.exists('excluded_suppliers.txt'):
            with open('excluded_suppliers.txt', 'r') as f:
                suppliers_text = f.read().strip()
                supplier_count = len([line for line in suppliers_text.split('\n') if line.strip()])
        else:
            suppliers_text = ''
            supplier_count = 0
    except Exception as e:
        suppliers_text = f'Error loading suppliers: {str(e)}'
        supplier_count = 0
    
    return render_template('modules/purchase_orders/manage_suppliers.html',
                         suppliers_text=suppliers_text,
                         supplier_count=supplier_count)


def _import_datetime():
    """Helper function to import datetime module"""
    import datetime
    return datetime
