"""
Authentication middleware and utilities.

Handles JWT validation and email whitelist checking.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.models.database import get_db
from app.models.models import AllowedUser

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    """Custom authentication error."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(HTTPException):
    """Custom authorization error."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        AuthError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise AuthError("Invalid or expired token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """
    Validate token and check email whitelist.

    This is a FastAPI dependency that:
    1. Extracts Bearer token from Authorization header
    2. Decodes and validates the JWT
    3. Checks if the email is in the allowed_users table or env whitelist

    Args:
        credentials: Bearer token from request header
        db: Database session

    Returns:
        User info dict with email, name, picture

    Raises:
        AuthError: If no token or invalid token
        ForbiddenError: If user not authorized
    """
    # Dev mode: skip auth entirely
    settings = get_settings()
    if settings.disable_auth and settings.debug:
        return {
            "email": "dev@localhost",
            "name": "Dev User",
            "picture": "",
            "source": "dev_bypass",
        }

    if credentials is None:
        raise AuthError("Missing authentication token")

    # Decode token
    payload = decode_token(credentials.credentials)

    # Extract email from token
    email = payload.get("email")
    if not email:
        raise AuthError("Token missing email claim")

    # Check against allowed_users table first
    user = db.query(AllowedUser).filter(
        AllowedUser.email == email,
        AllowedUser.is_active == True,
    ).first()

    if user:
        return {
            "email": email,
            "name": user.name or payload.get("name", ""),
            "picture": payload.get("picture", ""),
            "source": "database",
        }

    # Fallback: check against environment variable whitelist
    settings = get_settings()
    allowed_emails = [e.strip() for e in settings.allowed_emails.split(",") if e.strip()]

    if email in allowed_emails:
        return {
            "email": email,
            "name": payload.get("name", ""),
            "picture": payload.get("picture", ""),
            "source": "env_whitelist",
        }

    # User not authorized
    raise ForbiddenError("User is not authorized to access this application")


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.

    Use this for endpoints that work with or without auth.
    """
    if credentials is None:
        return None

    try:
        return get_current_user(credentials, db)
    except (AuthError, ForbiddenError):
        return None


# Convenience dependency aliases
require_auth = Depends(get_current_user)
optional_auth = Depends(get_optional_user)


def validate_token_string(token: str) -> dict:
    """
    Validate a raw JWT token string (for SSE endpoints where
    EventSource can't send Authorization headers).

    Returns decoded payload or raises AuthError.
    """
    if not token:
        raise AuthError("Missing authentication token")
    return decode_token(token)


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """
    Create a new JWT access token.

    This is primarily for testing. In production, tokens come from NextAuth.

    Args:
        data: Payload data (must include 'email')
        expires_delta: Expiration in seconds (default: 1 hour)

    Returns:
        Encoded JWT token
    """
    from datetime import timedelta

    settings = get_settings()

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=expires_delta or 3600)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt
