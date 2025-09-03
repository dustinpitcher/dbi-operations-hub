# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for pandas, openpyxl, and our security utilities
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Create all necessary directories with proper permissions
RUN mkdir -p \
    uploads \
    staging \
    logs \
    uploads/assembly \
    uploads/purchase_orders \
    staging/assembly \
    staging/purchase_orders \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set production environment variables
ENV FLASK_ENV=production
ENV LOG_LEVEL=INFO
ENV PYTHONPATH=/app

# Expose port (Azure will set PORT env variable)
EXPOSE 8000

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use gunicorn with our WSGI entry point
# Optimized settings for the enhanced DBI Operations Hub
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 300 --max-requests 1000 --max-requests-jitter 50 --preload --access-logfile - --error-logfile - wsgi:app"]
