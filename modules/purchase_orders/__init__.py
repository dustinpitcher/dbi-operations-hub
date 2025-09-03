from flask import Blueprint

# Create Blueprint for Purchase Order module
po_bp = Blueprint('purchase_orders', __name__, url_prefix='/po')

# Import routes to register them with the blueprint
from . import routes
