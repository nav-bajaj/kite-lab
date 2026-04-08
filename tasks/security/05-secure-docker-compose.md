# Task 5: Secure Docker Compose Credentials

**Severity:** CRITICAL
**Status:** `completed`
**User Action Required:** No

## Problem

Weak default credentials in docker-compose.yml:

```yaml
POSTGRES_PASSWORD: kitelab
DATABASE_URL: postgresql://kitelab:kitelab@db:5432/kitelab
JWT_SECRET: dev-secret-local
DEBUG: "true"
```

## Risk

- Easy to guess database password
- Debug mode exposes sensitive information
- Weak JWT allows token forgery

## Fix Steps

### Step 1: Use environment variables (Claude)
- Replace hardcoded values with `${VAR:-default}`
- Create `.env.docker` template

### Step 2: Generate strong defaults (Claude)
- Use stronger default password
- Or require env file for docker-compose

### Step 3: Disable debug by default (Claude)
- Set `DEBUG: "false"` as default

### Step 4: Add docker .env.example (Claude)
- Document required variables
- Provide generation commands

## Breaking Changes

- **Local docker setup** may need `.env.docker` file
- **Existing containers** need rebuild with new credentials

## Verification

```bash
# After changes, test docker setup
docker-compose down -v
docker-compose up --build

# Verify connection works
curl http://localhost:8000/api/health
```
