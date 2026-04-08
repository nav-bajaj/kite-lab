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

# Step 3: Run migrations and start server as appuser
exec gosu appuser sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
