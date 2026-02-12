# Task 3: Implement Health Endpoint and Auth Middleware

**Status**: `completed`
**Blocked By**: #2 (Database Models)
**Blocks**: #12 (Deploy)

## Objective

Create the health check endpoint and JWT-based authentication middleware with email whitelist validation.

## Tasks

- [ ] Implement `GET /api/health` endpoint (no auth required)
- [ ] Create `app/auth.py` with JWT validation middleware
- [ ] Set up CORS configuration
- [ ] Add Bearer token validation for protected endpoints
- [ ] Create `allowed_users` table check for email whitelist

## app/api/health.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint - no auth required"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

## app/auth.py

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime
from app.config import settings
from app.models.database import get_db
from app.models.models import AllowedUser

security = HTTPBearer()

def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """Validate token and check email whitelist"""
    payload = decode_token(credentials.credentials)

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim",
        )

    # Check against allowed_users table
    user = db.query(AllowedUser).filter(
        AllowedUser.email == email,
        AllowedUser.is_active == True,
    ).first()

    if not user:
        # Fallback: check against environment variable
        allowed_emails = settings.allowed_emails.split(",")
        if email not in allowed_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not authorized",
            )

    return {
        "email": email,
        "name": payload.get("name", ""),
        "picture": payload.get("picture", ""),
    }

# Dependency for protected routes
async def require_auth(user: dict = Depends(get_current_user)):
    return user
```

## Using Auth in Routes

```python
from fastapi import APIRouter, Depends
from app.auth import require_auth

router = APIRouter()

@router.get("/portfolio")
async def get_portfolio(user: dict = Depends(require_auth)):
    """Protected endpoint - requires valid JWT"""
    return {"message": f"Hello {user['email']}"}
```

## CORS Configuration (app/main.py)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## Environment Variables

```bash
# .env
JWT_SECRET=your-32-character-secret-key-here
ALLOWED_EMAILS=your-email@gmail.com
ALLOWED_ORIGINS=http://localhost:3000,https://kite-dashboard.vercel.app
```

## Verification

```bash
# Test health endpoint (no auth)
curl http://localhost:8000/api/health

# Test protected endpoint (should fail without token)
curl http://localhost:8000/api/portfolio
# Expected: 401 Unauthorized

# Test with valid token (after frontend auth is set up)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/portfolio
```

## Notes

- Health endpoint is public (no auth) for monitoring/healthchecks
- JWT tokens come from NextAuth on the frontend
- Email whitelist provides single-user access control
- CORS must allow the frontend domain

---

*Last updated: February 2026*
