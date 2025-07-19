# ===============================================
# Python API Service for CoachNTT.ai
# ===============================================
# Lightweight Python 3.11 with security hardening
# Optimized for 8GB VPS deployment
# ===============================================

FROM python:3.11-slim

# ===============================================
# Labels
# ===============================================
LABEL org.opencontainers.image.title="CoachNTT.ai API"
LABEL org.opencontainers.image.description="Safety-first API service"
LABEL org.opencontainers.image.version="1.0.0"

# ===============================================
# Security Setup
# ===============================================
# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# ===============================================
# Install System Dependencies
# ===============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client for database connections
    postgresql-client \
    # Build dependencies for Python packages
    gcc \
    python3-dev \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ===============================================
# Copy Requirements First (for layer caching)
# ===============================================
COPY requirements.txt .

# ===============================================
# Install Python Dependencies
# ===============================================
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===============================================
# Copy Application Code
# ===============================================
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser scripts/ ./scripts/

# ===============================================
# Security Hardening
# ===============================================
# Remove unnecessary files
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -type d -exec rm -rf {} + || true && \
    # Set secure permissions
    chmod -R 755 /app && \
    # Create directories for runtime
    mkdir -p /app/logs /app/temp && \
    chown -R appuser:appuser /app/logs /app/temp

# ===============================================
# Environment Variables
# ===============================================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # API configuration
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    # Security
    API_WORKERS=2 \
    API_MAX_REQUESTS=1000 \
    API_MAX_REQUESTS_JITTER=50

# ===============================================
# Switch to non-root user
# ===============================================
USER appuser

# ===============================================
# Expose Port
# ===============================================
EXPOSE 8000

# ===============================================
# Health Check
# ===============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# ===============================================
# Start Command
# ===============================================
CMD ["python", "-m", "uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--access-log", \
     "--log-level", "info"]