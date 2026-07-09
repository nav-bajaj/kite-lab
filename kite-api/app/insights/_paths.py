"""Shared path resolution for insight-engine data folders.

Historically several modules hardcoded the founder's local Documents path
for the long-history indices panel and fell back to the in-repo directory
only when it was absent. That made Railway a second-class citizen and left
the fallback name (`indices_data_historical`) undiscoverable. This module
centralizes the resolution order so local dev and production agree.

Resolution order for the indices directory:
  1. INSIGHTS_INDICES_DIR env override (explicit, wins everywhere).
  2. The local Documents store if it exists (unchanged local-dev behavior).
  3. settings.data_dir / "indices_data_historical" (the production path;
     provisioned on the Railway volume and symlinked by
     scripts/init_persistent_storage.sh).
"""
from __future__ import annotations

import os
from pathlib import Path

from app.config import get_settings

# The founder's local long-history indices store. Kept as the dev default so
# local behavior is identical to before this refactor; production never has
# this path and falls through to the settings-based location.
_LOCAL_INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")

# Production folder name on the Railway volume. Chosen historically as the
# fallback; the upload target and init-script symlink both use this exact name
# so the extract path and the read path coincide.
INDICES_DIR_NAME = "indices_data_historical"


def indices_dir() -> Path:
    override = os.environ.get("INSIGHTS_INDICES_DIR")
    if override:
        return Path(override)
    if _LOCAL_INDICES_DIR.exists():
        return _LOCAL_INDICES_DIR
    return get_settings().data_dir / INDICES_DIR_NAME
