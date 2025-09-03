from flask import Blueprint

# Create Blueprint for Assembly Management module
assembly_bp = Blueprint('assembly', __name__, url_prefix='/assembly')

# Import routes to register them with the blueprint
from . import routes
