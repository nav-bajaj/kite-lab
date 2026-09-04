"""
Authentication-related routes.

The JWT-minting endpoint (``POST /token``) is gone — Supabase issues
session tokens directly to the frontend. The remaining two endpoints
expose the verified identity to clients.
"""
from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter()


@router.get("/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current authenticated user info (Supabase-verified)."""
    return {
        "sub": user["sub"],
        "role": user.get("role", "client"),
        "metadata": user.get("metadata", {}),
        "auth_source": user.get("source", "unknown"),
    }


@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """Verify that the token is valid (Supabase-verified)."""
    return {
        "valid": True,
        "sub": user["sub"],
        "role": user.get("role", "client"),
    }
