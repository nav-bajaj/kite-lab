# Kite-Lab API Dockerfile
# Builds from repo root to include both kite-api/ and scripts/

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
# TZ=Asia/Kolkata: this is an India-only market system. Without it the
# container runs in UTC, which (a) made APScheduler cron triggers fire 5h30m
# late, (b) printed job-log timestamps in UTC, and (c) broke the "token expires
# 6 AM IST" check in system_service. DB timestamps are unaffected (they use
# func.now() server-side / explicit utcnow()).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    TZ=Asia/Kolkata

# Install system dependencies (tzdata so $TZ resolves to a real zone)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    gosu \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
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
COPY data/corporate_actions.json data/corporate_actions.json

# Create data directories for runtime (benchmarks fetched at runtime)
RUN mkdir -p data/nse500_data data/indices_data data/final_portfolio \
    data/nifty100_portfolio data/nifty250_portfolio data/benchmarks \
    logs/jobs nifty_100_tests nifty_250_tests experiments

# Make persistent storage init script executable
RUN chmod +x scripts/init_persistent_storage.sh

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Copy entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Start as root (entrypoint inits storage, then drops to appuser for server).
# Use explicit sh invocation rather than relying on Railway's catatonit init
# to honor the shebang — that path broke for us on 2026-05-20 with a
# "failed to exec pid1: No such file or directory" loop.
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
