"""
Subscription API routes
Handles all Stripe subscription-related endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from api.auth import verify_clerk_token
from services.stripe_service import stripe_service

router = APIRouter()


class CheckoutSessionResponse(BaseModel):
    """Response containing checkout session URL"""
    checkout_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    """Response containing customer portal URL"""
    portal_url: str


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(request: Request):
    """
    Create a Stripe checkout session for Pro subscription

    Requires authentication via Clerk JWT token

    Returns:
        CheckoutSessionResponse: URL to redirect user to Stripe checkout
    """
    try:
        user = await verify_clerk_token(request)
        user_id = user.get("id")
        email = user.get("email_addresses", [{}])[0].get("email_address")

        result = stripe_service.create_checkout_session(user_id, email)

        return CheckoutSessionResponse(
            checkout_url=result["checkout_url"],
            session_id=result["session_id"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(request: Request):
    """
    Create a Stripe customer portal session for managing subscription

    Requires authentication and existing subscription

    Returns:
        PortalSessionResponse: URL to redirect user to Stripe portal
    """
    try:
        user = await verify_clerk_token(request)
        user_id = user.get("id")
        portal_url = stripe_service.create_portal_session(user_id)

        return PortalSessionResponse(portal_url=portal_url)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portal session: {str(e)}"
        )


@router.get("/status")
async def get_subscription_status(request: Request):
    """
    Get current user's subscription status

    Requires authentication

    Returns:
        dict: Subscription tier, status, and expiration details
    """
    try:
        print("=== GET /status called ===")
        user = await verify_clerk_token(request)
        print(f"User authenticated: {user}")

        user_id = user.get("id")
        print(f"User ID: {user_id}")

        result = stripe_service.get_subscription_status(user_id)
        print(f"Subscription status result: {result}")

        return result

    except ValueError as e:
        print(f"ValueError in /status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"Exception in /status: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription status: {str(e)}"
        )
