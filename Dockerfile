# Kite-Lab API Dockerfile
# Builds from repo root to include both kite-api/ and scripts/

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY kite-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy API application code
COPY kite-api/app app/
COPY kite-api/alembic alembic/
COPY kite-api/alembic.ini .

# Copy root scripts and supporting modules
COPY scripts/ scripts/
COPY data_pipeline/ data_pipeline/

# Copy static data files needed by scripts
COPY data/static/ data/static/
COPY data/benchmarks/ data/benchmarks/

# Create data directories for runtime
RUN mkdir -p data/nse500_data data/indices_data data/final_portfolio \
    data/nifty100_portfolio data/nifty250_portfolio \
    logs nifty_100_tests nifty_250_tests experiments

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
