"""
Kite-Lab API - FastAPI Application

Backend API for Kite-Lab Production Dashboard.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api import health, auth_routes, portfolio, sync, metrics, trades, rebalance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    print(f"Starting Kite-Lab API (debug={settings.debug})")
    yield
    # Shutdown
    print("Shutting down Kite-Lab API")


# Create FastAPI app
app = FastAPI(
    title="Kite-Lab API",
    description="Backend API for Kite-Lab Production Dashboard",
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
origins = [origin.strip() for origin in settings.allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio.router, tags=["portfolio"])
app.include_router(sync.router, tags=["sync"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(trades.router, tags=["trades"])
app.include_router(rebalance.router, tags=["rebalance"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Kite-Lab API",
        "version": "1.0.1",
        "docs": "/docs",
        "health": "/api/health",
        "routes": ["/api/portfolio", "/api/sync", "/api/metrics", "/api/trades", "/api/rebalance"],
    }
