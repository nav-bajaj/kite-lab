"""
Kite-Lab API - FastAPI Application

Backend API for Kite-Lab Production Dashboard.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.services.market_service import warn_if_holiday_table_stale
from app.api import health, auth_routes, portfolio, sync, metrics, trades, rebalance, jobs, system, schedule, positions, insights, indices, freshness
from app.scheduler import start_scheduler, shutdown_scheduler, register_default_tasks, scheduler
from app.middleware.error_handlers import register_error_handlers
from app.middleware.request_logger import RequestLoggerMiddleware
from app.middleware.rate_limiter import register_rate_limiter
from app.middleware.etag import ETagMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    if settings.debug:
        logging.getLogger(__name__).warning(
            "DEBUG MODE IS ENABLED - disable in production by setting DEBUG=false"
        )
    if settings.jwt_secret == "change-me-in-production":
        logging.getLogger(__name__).warning(
            "JWT_SECRET is using the default value - set a strong secret in production"
        )
    warn_if_holiday_table_stale()
    print(f"Starting Kite-Lab API (debug={settings.debug})")

    # Start scheduler (synchronous)
    start_scheduler()
    register_default_tasks(scheduler)
    print("Scheduler started with default tasks")

    yield

    # Shutdown (synchronous)
    shutdown_scheduler()
    print("Shutting down Kite-Lab API")


# Create FastAPI app
_settings = get_settings()
app = FastAPI(
    title="Kite-Lab API",
    description="Backend API for Kite-Lab Production Dashboard",
    version="1.1.0",
    docs_url="/docs" if _settings.debug else None,
    redoc_url="/redoc" if _settings.debug else None,
    openapi_url="/openapi.json" if _settings.debug else None,
    lifespan=lifespan,
)

# Register error handlers (must be before middleware)
register_error_handlers(app)

# Register rate limiter
register_rate_limiter(app)

# Configure CORS
settings = get_settings()
origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

# Block wildcard origins in production
if not settings.debug and "*" in origins:
    logging.getLogger(__name__).warning(
        "Wildcard CORS origin '*' is not allowed in production. Restricting to localhost."
    )
    origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not _settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

# ETag / 304 handling for JSON GETs. Added before SecurityHeaders so it
# sits *inside* it: SecurityHeaders then runs on the response ETag rebuilds
# (or the 304 it emits), so security headers are never dropped.
app.add_middleware(ETagMiddleware)

app.add_middleware(SecurityHeadersMiddleware)

# Request logging middleware (outermost = runs first)
app.add_middleware(RequestLoggerMiddleware)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, tags=["portfolio"])
app.include_router(sync.router, tags=["sync"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(trades.router, tags=["trades"])
app.include_router(rebalance.router, tags=["rebalance"])
app.include_router(jobs.router, tags=["jobs"])
app.include_router(system.router, tags=["system"])
app.include_router(schedule.router, tags=["schedule"])
app.include_router(positions.router, tags=["positions"])
app.include_router(insights.router, tags=["insights"])  # public, read-only — no auth required
app.include_router(indices.router, tags=["indices"])  # public, read-only — no auth required
app.include_router(freshness.router, tags=["freshness"])  # admin-only ops intel


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Kite-Lab API",
        "version": "1.1.0",
        "health": "/api/health",
        "routes": [
            "/api/portfolio",
            "/api/positions",
            "/api/sync",
            "/api/metrics",
            "/api/trades",
            "/api/rebalance",
            "/api/jobs",
            "/api/system",
            "/api/schedule",
        ],
    }
