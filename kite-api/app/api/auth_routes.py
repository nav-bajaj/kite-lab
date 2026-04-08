"""
Authentication-related routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, create_access_token
from app.config import get_settings
from app.middleware.rate_limiter import limiter

router = APIRouter()


class TokenRequest(BaseModel):
    """Request for creating an internal token."""
    email: str = Field(..., max_length=255)
    name: str = Field(default="", max_length=255)


class TokenResponse(BaseModel):
    """Response containing the JWT token."""
    access_token: str
    token_type: str = "bearer"
    email: str


@router.get("/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user info.

    Requires valid JWT token in Authorization header.
    """
    return {
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture", ""),
        "auth_source": user.get("source", "unknown"),
    }


@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """
    Verify that the token is valid.

    Returns success if token is valid and user is authorized.
    """
    return {
        "valid": True,
        "email": user["email"],
    }


@router.post("/token", response_model=TokenResponse)
@limiter.limit("5/minute")
async def create_token(request: Request, body: TokenRequest):
    """
    Create a JWT token for authenticated users.

    Called from Next.js API routes after verifying the NextAuth session.
    Rate limited to 5 requests/minute per IP.
    """
    settings = get_settings()

    # Check if email is in allowed list
    allowed_emails = [e.strip() for e in settings.allowed_emails.split(",") if e.strip()]
    if not allowed_emails and not settings.debug:
        raise HTTPException(
            status_code=500,
            detail="ALLOWED_EMAILS not configured"
        )
    if allowed_emails and body.email not in allowed_emails:
        raise HTTPException(
            status_code=403,
            detail="Email is not authorized"
        )

    # Create token with 24 hour expiry
    token = create_access_token(
        data={"email": body.email, "name": body.name},
        expires_delta=86400  # 24 hours
    )

    return TokenResponse(
        access_token=token,
        email=body.email
    )
