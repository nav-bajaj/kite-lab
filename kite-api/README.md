# Kite-Lab API

Backend API for Kite-Lab Production Dashboard.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL

### Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Create database:
   ```bash
   createdb kitelab  # or use psql
   ```

5. Run migrations:
   ```bash
   alembic upgrade head
   ```

6. Start development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

7. Open http://localhost:8000/docs for API documentation.

## Project Structure

```
kite-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance
│   ├── config.py            # Settings and universe config
│   ├── auth.py              # JWT authentication
│   ├── api/                 # Route handlers
│   │   ├── health.py
│   │   ├── portfolio.py
│   │   ├── metrics.py
│   │   └── ...
│   ├── models/              # SQLAlchemy models
│   │   ├── database.py
│   │   └── models.py
│   ├── services/            # Business logic
│   │   ├── portfolio_service.py
│   │   └── ...
│   └── engine/              # Migrated kite-lab scripts
│       ├── data_pipeline/
│       └── scripts/
├── alembic/                 # Database migrations
├── data/                    # Static data files
│   ├── static/
│   └── benchmarks/
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .env
```

## API Endpoints

- `GET /api/health` - Health check (no auth)
- `GET /api/portfolio?universe=nse500` - Portfolio overview
- `GET /api/portfolio/holdings?universe=nse500` - Current holdings
- `GET /api/metrics?universe=nse500` - Performance metrics
- `GET /api/trades?universe=nse500` - Trade history
- `POST /api/admin/run` - Execute pipeline commands

## Universes

All endpoints accept a `universe` query parameter:
- `nse500` - NSE 500 (default)
- `nifty250` - Nifty 250
- `nifty100` - Nifty 100

## Deployment

See `docs/tasks/phase1/12-deploy.md` for Railway deployment instructions.
