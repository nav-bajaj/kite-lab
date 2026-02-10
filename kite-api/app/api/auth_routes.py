"""
Authentication-related routes.
"""
from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter()


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
