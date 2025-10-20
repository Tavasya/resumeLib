"""
Stripe webhook handlers for subscription management
"""
from fastapi import APIRouter, Request, HTTPException, status, Header
from config import settings
from config.stripe import stripe
from services.stripe_service import stripe_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="stripe-signature")):
    """
    Handle Stripe webhook events for subscription management

    Events handled:
    - checkout.session.completed: User successfully subscribed
    - customer.subscription.updated: Subscription status changed
    - customer.subscription.deleted: Subscription canceled
    """
    # Get raw body for signature verification
    body = await request.body()

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Get event type and data
    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info(f"Received Stripe webhook event: {event_type}")

    try:
        print(f"🔔 WEBHOOK RECEIVED: {event_type}")
        print(f"📦 Data object: {data_object}")

        if event_type == "checkout.session.completed":
            # Payment succeeded, activate subscription
            print("💳 Processing checkout.session.completed")
            stripe_service.handle_checkout_completed(data_object)
            print("✅ Checkout completed handler finished")

        elif event_type == "customer.subscription.updated":
            # Subscription status changed (e.g., renewed, past_due)
            print("🔄 Processing customer.subscription.updated")
            stripe_service.handle_subscription_updated(data_object)
            print("✅ Subscription updated handler finished")

        elif event_type == "customer.subscription.deleted":
            # Subscription canceled or expired
            print("❌ Processing customer.subscription.deleted")
            stripe_service.handle_subscription_deleted(data_object)
            print("✅ Subscription deleted handler finished")

        else:
            logger.warning(f"Unhandled Stripe event type: {event_type}")
            print(f"⚠️ Unhandled event type: {event_type}")

        return {"success": True, "message": f"Processed {event_type}"}

    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )
