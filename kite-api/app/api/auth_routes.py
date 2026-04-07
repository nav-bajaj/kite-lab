"""
Authentication-related routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, create_access_token
from app.config import get_settings

router = APIRouter()


class TokenRequest(BaseModel):
    """Request for creating an internal token."""
    email: str
    name: str = ""


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
async def create_token(request: TokenRequest):
    """
    Create a JWT token for authenticated users.

    This endpoint is meant to be called from Next.js API routes
    after verifying the NextAuth session server-side.

    SECURITY: In production, this should be protected by:
    - Internal network only (not exposed to internet)
    - OR API key verification
    - OR IP whitelist

    For now, relies on CORS (only frontend can call).
    """
    settings = get_settings()

    # Check if email is in allowed list
    allowed_emails = [e.strip() for e in settings.allowed_emails.split(",") if e.strip()]
    if allowed_emails and request.email not in allowed_emails:
        raise HTTPException(
            status_code=403,
            detail=f"Email {request.email} is not authorized"
        )

    # Create token with 24 hour expiry
    token = create_access_token(
        data={"email": request.email, "name": request.name},
        expires_delta=86400  # 24 hours
    )

    return TokenResponse(
        access_token=token,
        email=request.email
    )
