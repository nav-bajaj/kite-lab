# Task 1: Set up FastAPI Backend Project Structure

**Status**: `completed`
**Blocked By**: None
**Blocks**: #2, #4, #5

## Objective

Initialize the FastAPI backend project with proper directory structure and dependencies.

## Tasks

- [x] Create `kite-api/` directory at repo root
- [x] Set up `app/main.py` with FastAPI app instance
- [x] Create `requirements.txt` with all dependencies
- [x] Set up `app/config.py` for environment variables and universe configuration
- [x] Create directory structure

## Directory Structure

```
kite-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance
│   ├── config.py            # Environment variables, universe config
│   ├── api/                  # API route handlers
│   │   ├── __init__.py
│   │   └── health.py
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── database.py
│   ├── services/             # Business logic
│   │   └── __init__.py
│   ├── engine/               # Migrated kite-lab scripts
│   │   ├── __init__.py
│   │   ├── data_pipeline/
│   │   └── scripts/
│   └── auth.py              # JWT validation
├── alembic/                  # Database migrations
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
└── README.md
```

## requirements.txt

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
apscheduler>=3.10.0
httpx>=0.26.0
pandas>=2.0.0
kiteconnect>=5.0.0
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.0
```

## app/config.py (Template)

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Database
    database_url: str

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Auth
    jwt_secret: str
    allowed_emails: str  # Comma-separated

    # Kite API
    kite_api_key: str = ""
    kite_api_secret: str = ""

    class Config:
        env_file = ".env"

settings = Settings()

# Universe configuration
UNIVERSES = {
    "nse500": {
        "name": "NSE 500",
        "description": "Full mid+large cap universe",
        "stocks": 499,
        "risk_profile": "Growth-focused",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nse500_universe.csv",
    },
    "nifty250": {
        "name": "Nifty 250",
        "description": "Large + mid-cap blend",
        "stocks": 250,
        "risk_profile": "Balanced",
        "data_dir": "nse500_data",  # Uses same price data
        "universe_file": "data/static/nifty250_universe.csv",
    },
    "nifty100": {
        "name": "Nifty 100",
        "description": "Large-cap only",
        "stocks": 100,
        "risk_profile": "Conservative",
        "data_dir": "nse500_data",  # Uses same price data
        "universe_file": "data/static/nifty100_universe.csv",
    },
}

UniverseId = Literal["nse500", "nifty250", "nifty100"]
```

## app/main.py (Template)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title="Kite-Lab API",
    description="Backend API for Kite-Lab Production Dashboard",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api import health
app.include_router(health.router, prefix="/api", tags=["health"])

@app.get("/")
async def root():
    return {"message": "Kite-Lab API", "docs": "/docs"}
```

## Verification

```bash
cd kite-api
pip install -r requirements.txt
uvicorn app.main:app --reload
# Visit http://localhost:8000/docs
```

## Notes

- Use Python 3.11 for compatibility with Railway
- Keep kiteconnect optional (may not be needed on Railway if data is synced)

---

*Last updated: February 2026*
