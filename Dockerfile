# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for pandas and openpyxl
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Create necessary directories
RUN mkdir -p uploads staging uploads/assembly uploads/purchase_orders staging/purchase_orders

# Expose port (Azure will set PORT env variable)
EXPOSE 8000

# Use gunicorn for production with optimized settings for combined app
# Extended timeout for comprehensive reporting and PO generation
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 600 --max-requests 100 --max-requests-jitter 10 --preload app:app"]
