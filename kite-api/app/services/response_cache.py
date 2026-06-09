"""
Short-lived in-process cache for daily client-read responses.

The daily pipeline refreshes portfolio / metrics data at most once per day,
so identical requests within a short window can share one computed payload
instead of each hitting the database. A small TTL collapses bursts (many
users, or one user across tabs/devices) while keeping staleness negligible
and bounded — well within the 1h Cache-Control window these endpoints
already advertise.

Security invariant: cache keys are scoped to the *universe* (and any query
params), NEVER to the user. The payload is universe-scoped data, and
per-request access control (``check_universe_access``) runs in the handler
*before* the cache is consulted — so the cache can never hand a user data
for a universe they aren't allowed to see. Do not add user identity to a
key; do not consult the cache before the access check.
"""

import threading
from typing import Any, Callable, Hashable

from cachetools import TTLCache

# 2 minutes: long enough to collapse request bursts, short enough that a
# late-evening pipeline run is reflected almost immediately.
_DEFAULT_TTL = 120

_cache: TTLCache = TTLCache(maxsize=512, ttl=_DEFAULT_TTL)
_lock = threading.Lock()


def cached_response(key: Hashable, producer: Callable[[], Any]) -> Any:
    """Return a cached value for ``key`` or compute + store it.

    ``producer`` is invoked outside the lock (it may do DB I/O); a brief
    duplicate computation under concurrency is acceptable and preferable to
    holding the lock across a query. Error envelopes (dicts with a truthy
    ``error`` key) are returned but NOT cached, so a transient failure isn't
    pinned for the whole TTL.
    """
    with _lock:
        if key in _cache:
            return _cache[key]

    value = producer()

    if isinstance(value, dict) and value.get("error"):
        return value

    with _lock:
        _cache[key] = value
    return value


def clear_response_cache() -> None:
    """Drop all cached responses (used by tests and after a manual sync)."""
    with _lock:
        _cache.clear()
