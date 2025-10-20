"""
Clerk authentication utilities for FastAPI
"""
from fastapi import HTTPException, Header, status
from typing import Optional
import httpx
from config import settings


async def verify_clerk_token(authorization: str = Header(...)) -> dict:
    """
    Verify Clerk JWT token from Authorization header

    Args:
        authorization: Bearer token from request header

    Returns:
        dict: User data from Clerk

    Raises:
        HTTPException: If token is invalid or verification fails
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")

    # Verify token with Clerk
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.clerk.com/v1/sessions/verify",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json"
                },
                params={"token": token}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )

            session_data = response.json()

            # Get user details
            user_id = session_data.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session data"
                )

            # Fetch full user data
            user_response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json"
                }
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to fetch user data"
                )

            return user_response.json()

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to verify token: {str(e)}"
            )


async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Optional authentication - returns user if token is valid, None otherwise

    Args:
        authorization: Optional Bearer token from request header

    Returns:
        dict or None: User data if authenticated, None otherwise
    """
    if not authorization:
        return None

    try:
        return await verify_clerk_token(authorization)
    except HTTPException:
        return None
