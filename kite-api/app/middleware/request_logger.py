"""
Request logging middleware.

Logs every request with method, path, status code, duration, and audit info.
Skips health check endpoints to reduce noise.
"""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("kite_api.requests")
audit_logger = logging.getLogger("kite_api.audit")

# Paths to skip logging (health checks, favicon)
SKIP_PATHS = {"/api/health", "/health", "/favicon.ico"}

# Paths that warrant audit logging (sensitive operations)
AUDIT_PATHS = {"/api/jobs", "/api/schedule", "/api/sync", "/api/rebalance", "/api/auth/token"}


def _get_client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For for proxied requests."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Log incoming requests with timing and audit information."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noisy endpoints
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        # Generate request ID for tracing
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id

        client_ip = _get_client_ip(request)
        start = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start) * 1000

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            logger.info(
                "%s %s %s %d %.1fms [%s]",
                request.method,
                request.url.path,
                client_ip,
                response.status_code,
                duration_ms,
                request_id,
            )

            # Audit log for sensitive endpoints
            if any(request.url.path.startswith(p) for p in AUDIT_PATHS):
                if request.method in ("POST", "PUT", "DELETE"):
                    audit_logger.info(
                        "action=%s path=%s ip=%s status=%d request_id=%s",
                        request.method,
                        request.url.path,
                        client_ip,
                        response.status_code,
                        request_id,
                    )

            return response
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            logger.error(
                "%s %s %s ERROR %.1fms [%s] %s",
                request.method,
                request.url.path,
                client_ip,
                duration_ms,
                request_id,
                type(exc).__name__,
            )
            raise
