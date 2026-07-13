"""Cheap mtime-based data signatures for self-invalidating in-memory caches.

Insight loaders wrap their expensive build behind ``@lru_cache``. Keying that
cache on a *static* flag (e.g. ``force_rebuild=False``) froze the in-memory
copy for the worker's lifetime: the on-disk freshness check inside the loader
never ran again once the panel was in memory, so the API kept serving stale
panels after the daily pipeline rewrote the source files — until a redeploy.

Keying the cache on one of these signatures instead makes the worker reload on
the next request after the sources change: the file mtime moves, the signature
changes, the ``lru_cache`` misses, and the loader rebuilds. When nothing
changed the signature is identical, the cache hits, and the hot path stays
fast.

Signatures are intentionally coarse and cheap — one or two ``os.stat`` calls,
never a walk of all ~500 panel files. The daily pipeline writes each source
directory as a batch, so a single representative sentinel file's mtime is a
reliable proxy for "this directory changed".

A missing file/dir returns a stable sentinel (``0.0``) so that a file which
arrives later (mtime > 0) produces a different signature and still busts the
cache.
"""
from __future__ import annotations

from pathlib import Path

# Returned when the target does not exist yet. Any real mtime is > 0, so a
# later-arriving file changes the signature away from this value.
_MISSING = 0.0


def file_signature(path: Path) -> float:
    """Return ``path``'s mtime, or ``0.0`` if it does not exist."""
    try:
        return path.stat().st_mtime
    except OSError:
        return _MISSING


def dir_signature(path: Path, sentinel: str | None = None) -> float:
    """Return a cheap change-token for a data directory.

    With ``sentinel``, use that one file's mtime — the pipeline writes a
    directory as a batch, so one representative file tracks the whole set
    without stat-ing hundreds of files. Without it, fall back to the
    directory's own mtime, which the filesystem bumps when entries are added
    or removed. Returns ``0.0`` when nothing exists yet.
    """
    if sentinel is not None:
        return file_signature(path / sentinel)
    try:
        return path.stat().st_mtime
    except OSError:
        return _MISSING
