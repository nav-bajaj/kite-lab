"""
Rate limiting middleware using slowapi.

Applies per-IP rate limits:
- Default: 60 requests/minute
- Job creation: 10 requests/minute
"""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create limiter instance with in-memory storage
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    storage_uri="memory://",
)


def register_rate_limiter(app: FastAPI) -> None:
    """Register rate limiter on the FastAPI app."""
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        """Return structured JSON for rate limit violations."""
        logger.warning(
            "Rate limit exceeded: %s %s from %s",
            request.method,
            request.url.path,
            get_remote_address(request),
        )

        retry_after = exc.detail.split("per")[0].strip() if exc.detail else "60"

        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "type": "rate_limit_exceeded",
                "status_code": 429,
            },
            headers={"Retry-After": retry_after},
        )
