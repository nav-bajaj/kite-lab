# Task 4: Create Docker and Railway Deployment Config

**Status**: `completed`
**Blocked By**: #1 (Backend Setup)
**Blocks**: #12 (Deploy)

## Objective

Set up deployment configuration for Railway with Docker.

## Tasks

- [x] Create `Dockerfile` (Python 3.11-slim)
- [x] Create `railway.toml` with build and deploy config
- [x] Set up healthcheck path `/api/health`
- [x] Configure start command with Alembic migrations
- [x] Create `.env.example` documenting required variables

## Dockerfile

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/nse500_data data/indices_data data/final_portfolio data/static data/benchmarks

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## railway.toml

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "sh -c 'alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT'"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[service]
internalPort = 8000
```

## .env.example

```bash
# Database (provided by Railway PostgreSQL addon)
DATABASE_URL=postgresql://user:password@host:5432/database

# CORS - Frontend URLs
ALLOWED_ORIGINS=http://localhost:3000,https://kite-dashboard.vercel.app

# Authentication
JWT_SECRET=generate-a-32-character-random-string
ALLOWED_EMAILS=your-email@gmail.com

# Zerodha Kite API (optional - for live data fetch)
KITE_API_KEY=your-kite-api-key
KITE_API_SECRET=your-kite-api-secret
```

## .dockerignore

```
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv
.venv
.env

# IDE
.idea
.vscode
*.swp
*.swo

# Tests
tests/
pytest.ini

# Docs
docs/
*.md
!README.md

# Local data (will be synced separately)
nse500_data/
nse500_data_hourly/
indices_data/
experiments/
reports/
```

## Railway Setup Steps

1. **Create Railway Project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login
   railway login

   # Create new project
   railway init
   ```

2. **Add PostgreSQL**
   - Go to Railway dashboard
   - Click "New" → "Database" → "PostgreSQL"
   - Note: DATABASE_URL is auto-injected

3. **Configure Environment Variables**
   - Go to project settings → Variables
   - Add: JWT_SECRET, ALLOWED_EMAILS, ALLOWED_ORIGINS
   - Add: KITE_API_KEY, KITE_API_SECRET (if needed)

4. **Deploy**
   ```bash
   railway up
   ```

5. **Verify**
   ```bash
   curl https://your-app.railway.app/api/health
   ```

## Local Development

```bash
# Build and run locally
docker build -t kite-api .
docker run -p 8000:8000 --env-file .env kite-api

# Or without Docker
uvicorn app.main:app --reload --port 8000
```

## Notes

- Railway automatically provides PORT environment variable
- DATABASE_URL is auto-injected when PostgreSQL addon is added
- Healthcheck ensures Railway restarts unhealthy containers
- Alembic migrations run on every deploy (idempotent)

---

*Last updated: February 2026*
