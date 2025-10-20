"""
Clerk webhook handlers to sync user data with Supabase
"""
from fastapi import APIRouter, Request, HTTPException, status
from svix.webhooks import Webhook, WebhookVerificationError
from config import settings, supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/clerk")
async def clerk_webhook(request: Request):
    """
    Handle Clerk webhook events to sync user data with Supabase

    Events handled:
    - user.created: Create user in Supabase
    - user.updated: Update user in Supabase
    - user.deleted: Mark user as deleted in Supabase
    """
    # Get headers for webhook verification
    headers = {
        "svix-id": request.headers.get("svix-id"),
        "svix-timestamp": request.headers.get("svix-timestamp"),
        "svix-signature": request.headers.get("svix-signature"),
    }

    # Get raw body
    body = await request.body()

    # Verify webhook signature
    wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
    try:
        payload = wh.verify(body, headers)
    except WebhookVerificationError as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature"
        )

    # Get event type and data
    event_type = payload.get("type")
    data = payload.get("data")

    logger.info(f"Received Clerk webhook event: {event_type}")

    try:
        if event_type == "user.created":
            await handle_user_created(data)
        elif event_type == "user.updated":
            await handle_user_updated(data)
        elif event_type == "user.deleted":
            await handle_user_deleted(data)
        else:
            logger.warning(f"Unhandled event type: {event_type}")

        return {"success": True, "message": f"Processed {event_type}"}

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


async def handle_user_created(data: dict):
    """
    Handle user.created event - create user in Supabase
    """
    user_id = data.get("id")
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")

    # Find primary email by matching ID
    primary_email = None
    if primary_email_id:
        primary_email = next(
            (email["email_address"] for email in email_addresses if email.get("id") == primary_email_id),
            None
        )

    # Fallback to first email if no primary found
    if not primary_email and email_addresses:
        primary_email = email_addresses[0].get("email_address")

    if not primary_email:
        logger.error(f"No email found for user {user_id}")
        return

    user_data = {
        "clerk_user_id": user_id,
        "email": primary_email,
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "profile_image_url": data.get("image_url"),
        "username": data.get("username"),
        "last_sign_in_at": data.get("last_sign_in_at"),
        "metadata": {
            "clerk_created_at": data.get("created_at"),
            "clerk_updated_at": data.get("updated_at"),
        }
    }

    # Insert user into Supabase
    result = supabase.table("users").insert(user_data).execute()
    logger.info(f"Created user in Supabase: {user_id}")
    return result


async def handle_user_updated(data: dict):
    """
    Handle user.updated event - update user in Supabase
    """
    user_id = data.get("id")
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")

    # Find primary email by matching ID
    primary_email = None
    if primary_email_id:
        primary_email = next(
            (email["email_address"] for email in email_addresses if email.get("id") == primary_email_id),
            None
        )

    # Fallback to first email if no primary found
    if not primary_email and email_addresses:
        primary_email = email_addresses[0].get("email_address")

    if not primary_email:
        logger.error(f"No email found for user {user_id}")
        return

    user_data = {
        "email": primary_email,
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "profile_image_url": data.get("image_url"),
        "username": data.get("username"),
        "last_sign_in_at": data.get("last_sign_in_at"),
        "metadata": {
            "clerk_created_at": data.get("created_at"),
            "clerk_updated_at": data.get("updated_at"),
        }
    }

    # Update user in Supabase
    result = supabase.table("users")\
        .update(user_data)\
        .eq("clerk_user_id", user_id)\
        .execute()

    logger.info(f"Updated user in Supabase: {user_id}")
    return result


async def handle_user_deleted(data: dict):
    """
    Handle user.deleted event - mark user as deleted in Supabase
    """
    user_id = data.get("id")

    # Option 1: Soft delete - add a deleted_at timestamp
    # result = supabase.table("users")\
    #     .update({"deleted_at": "now()"})\
    #     .eq("clerk_user_id", user_id)\
    #     .execute()

    # Option 2: Hard delete - remove user from database
    result = supabase.table("users")\
        .delete()\
        .eq("clerk_user_id", user_id)\
        .execute()

    logger.info(f"Deleted user from Supabase: {user_id}")
    return result
