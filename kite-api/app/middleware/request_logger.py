"""
Request logging middleware.

Logs every request with method, path, status code, and duration.
Skips health check endpoints to reduce noise.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("kite_api.requests")

# Paths to skip logging (health checks, favicon)
SKIP_PATHS = {"/api/health", "/health", "/favicon.ico"}


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Log incoming requests with timing information."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noisy endpoints
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        start = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start) * 1000

            logger.info(
                "%s %s %d %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

            return response
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            logger.error(
                "%s %s ERROR %.1fms - %s: %s",
                request.method,
                request.url.path,
                duration_ms,
                type(exc).__name__,
                str(exc),
            )
            raise
