#!/bin/sh
# Docker entrypoint: runs storage init as root, then drops to appuser for the server.

set -e

# Step 1: Initialize persistent storage as root (needs write access to /data volume)
/app/scripts/init_persistent_storage.sh

# Step 2: Fix ownership so appuser can write to volume symlink targets
if [ -d "/data" ]; then
    chown -R appuser:appuser /data
fi

# Ensure /app symlinks are owned by appuser
chown -R appuser:appuser /app

# Step 3: Start the requested service as appuser.
# SERVICE_ROLE=options-worker runs the options data worker (no migrations —
# the web service owns the Alembic chain; the worker's kite_session table
# is created idempotently in code). Default: migrations + API server.
if [ "$SERVICE_ROLE" = "options-worker" ]; then
    exec gosu appuser python -m app.workers.options.worker
fi

exec gosu appuser sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
