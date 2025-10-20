"""
Clerk authentication and subscription utilities for FastAPI
"""
from fastapi import HTTPException, Depends, status, Request
from typing import Dict, Any, Optional
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
from config import settings, supabase
import logging

logger = logging.getLogger(__name__)

# Initialize Clerk auth config
clerk_config = ClerkConfig(
    jwks_url=settings.CLERK_JWKS_URL,
    auto_error=True
)

clerk_auth_guard = ClerkHTTPBearer(config=clerk_config)


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from Clerk and return user data
    Returns decoded JWT claims or None for missing tokens

    Args:
        request: FastAPI request object

    Returns:
        dict or None: Decoded JWT claims (includes "sub" for user ID)
    """
    try:
        print(f"=== get_current_user called ===")
        print(f"Headers: {dict(request.headers)}")

        credentials = await clerk_auth_guard(request)
        print(f"Credentials: {credentials}")
        print(f"Decoded: {credentials.decoded if credentials else None}")

        if credentials and credentials.decoded:
            return credentials.decoded
    except Exception as e:
        print(f"Auth exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

    return None


def get_user_id(user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> str:
    """
    Extract user ID from validated token payload

    Args:
        user: Decoded JWT from get_current_user

    Returns:
        str: User ID from "sub" claim

    Raises:
        HTTPException: If user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return user["sub"]


async def verify_clerk_token(request: Request) -> dict:
    """
    Verify Clerk JWT token and return formatted user data
    Used by subscription routes that need full user info

    Args:
        request: FastAPI request object

    Returns:
        dict: User data formatted for subscription operations

    Raises:
        HTTPException: If token is invalid or missing
    """
    user = await get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Return formatted for subscription routes
    return {
        "id": user.get("sub"),  # Map sub to id for subscription code
        "email_addresses": [{"email_address": user.get("email", "")}],
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
    }


async def get_user_subscription_info(user_id: str) -> dict:
    """
    Get user's subscription information from Supabase

    Args:
        user_id: Clerk user ID (from "sub" claim)

    Returns:
        dict: Subscription tier and status
    """
    result = supabase.table("users")\
        .select("subscription_tier, subscription_status, subscription_end_date")\
        .eq("clerk_user_id", user_id)\
        .single()\
        .execute()

    if not result.data:
        return {
            "tier": "free",
            "status": "active",
            "is_pro": False
        }

    return {
        "tier": result.data.get("subscription_tier", "free"),
        "status": result.data.get("subscription_status", "active"),
        "end_date": result.data.get("subscription_end_date"),
        "is_pro": result.data.get("subscription_tier") == "pro"
    }
