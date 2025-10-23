"""
Stripe subscription service
Handles all Stripe-related business logic
"""
from config.stripe import stripe
from config import settings, supabase
from typing import Dict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class StripeService:
    """Service for managing Stripe subscriptions"""

    def create_checkout_session(self, clerk_user_id: str, email: str) -> Dict[str, str]:
        """
        Create a Stripe checkout session for Pro subscription

        Args:
            clerk_user_id: Clerk user ID
            email: User email

        Returns:
            dict: Contains checkout_url and session_id
        """
        try:
            # Get or create Stripe customer
            customer_id = self.get_or_create_customer(clerk_user_id, email)

            # Create checkout session with 3-day free trial
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": settings.STRIPE_PRICE_ID_PRO,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                subscription_data={
                    "trial_period_days": 3,
                },
                success_url=f"{settings.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/dashboard",
                metadata={
                    "clerk_user_id": clerk_user_id,
                },
                allow_promotion_codes=True,
            )

            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            }

        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise

    def create_portal_session(self, clerk_user_id: str) -> str:
        """
        Create a Stripe customer portal session

        Args:
            clerk_user_id: Clerk user ID

        Returns:
            str: Portal URL
        """
        try:
            # Get customer ID from Supabase
            result = supabase.table("users")\
                .select("stripe_customer_id")\
                .eq("clerk_user_id", clerk_user_id)\
                .single()\
                .execute()

            if not result.data or not result.data.get("stripe_customer_id"):
                raise ValueError("No Stripe customer found")

            customer_id = result.data["stripe_customer_id"]

            # Create portal session
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{settings.FRONTEND_URL}/dashboard",
            )

            return portal_session.url

        except Exception as e:
            logger.error(f"Error creating portal session: {str(e)}")
            raise

    def get_subscription_status(self, clerk_user_id: str) -> Dict:
        """
        Get user's subscription status

        Args:
            clerk_user_id: Clerk user ID

        Returns:
            dict: Subscription status details including trial information
        """
        try:
            result = supabase.table("users")\
                .select("subscription_tier, subscription_status, subscription_end_date, user_resume_url")\
                .eq("clerk_user_id", clerk_user_id)\
                .single()\
                .execute()

            if not result.data:
                raise ValueError("User not found")

            status = result.data.get("subscription_status", "active")
            is_trialing = status == "trialing"

            return {
                "tier": result.data.get("subscription_tier", "free"),
                "status": status,
                "end_date": result.data.get("subscription_end_date"),
                "is_pro": result.data.get("subscription_tier") == "pro",
                "is_trialing": is_trialing,
                "trial_end_date": result.data.get("subscription_end_date") if is_trialing else None,
                "user_resume_url": result.data.get("user_resume_url")
            }

        except Exception as e:
            logger.error(f"Error getting subscription status: {str(e)}")
            raise

    def get_or_create_customer(self, clerk_user_id: str, email: str) -> str:
        """
        Get existing Stripe customer or create a new one

        Args:
            clerk_user_id: Clerk user ID
            email: User email

        Returns:
            str: Stripe customer ID
        """
        try:
            # Check if user already has a Stripe customer ID
            result = supabase.table("users")\
                .select("stripe_customer_id")\
                .eq("clerk_user_id", clerk_user_id)\
                .single()\
                .execute()

            if result.data and result.data.get("stripe_customer_id"):
                return result.data["stripe_customer_id"]

            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=email,
                metadata={"clerk_user_id": clerk_user_id}
            )

            # Save customer ID to Supabase
            supabase.table("users")\
                .update({"stripe_customer_id": customer.id})\
                .eq("clerk_user_id", clerk_user_id)\
                .execute()

            logger.info(f"Created Stripe customer for user {clerk_user_id}")
            return customer.id

        except Exception as e:
            logger.error(f"Error getting/creating customer: {str(e)}")
            raise

    def handle_checkout_completed(self, session: Dict) -> None:
        """
        Handle successful checkout session completion

        Args:
            session: Stripe checkout session object
        """
        try:
            print(f"📝 Session data: {session}")
            clerk_user_id = session["metadata"]["clerk_user_id"]
            print(f"👤 Clerk User ID: {clerk_user_id}")

            customer_id = session["customer"]
            print(f"💳 Customer ID: {customer_id}")

            subscription_id = session["subscription"]
            print(f"📋 Subscription ID: {subscription_id}")

            # Get subscription details from Stripe
            subscription = stripe.Subscription.retrieve(subscription_id)
            print(f"✅ Retrieved subscription from Stripe: {subscription.status}")
            print(f"📦 Full subscription object keys: {subscription.keys()}")

            # Get period dates from subscription items
            # Stripe subscriptions have current_period_start/end in the subscription items
            subscription_item = subscription['items']['data'][0]
            period_start = subscription_item['current_period_start']
            period_end = subscription_item['current_period_end']

            print(f"🕐 Raw timestamps - start: {period_start}, end: {period_end}")

            # Convert Unix timestamps to UTC datetime strings
            start_date = datetime.fromtimestamp(period_start, tz=timezone.utc).isoformat()
            end_date = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()

            print(f"📅 Converted dates - start: {start_date}, end: {end_date}")

            # Update user in Supabase
            result = supabase.table("users").update({
                "subscription_tier": "pro",
                "subscription_status": subscription.status,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "subscription_start_date": start_date,
                "subscription_end_date": end_date,
            }).eq("clerk_user_id", clerk_user_id).execute()

            print(f"💾 Supabase update result: {result.data}")
            logger.info(f"Updated subscription for user {clerk_user_id}")

        except Exception as e:
            print(f"❌ Error in handle_checkout_completed: {str(e)}")
            logger.error(f"Error handling checkout completed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def handle_subscription_updated(self, subscription: Dict) -> None:
        """
        Handle subscription update events

        Args:
            subscription: Stripe subscription object
        """
        try:
            subscription_id = subscription["id"]

            # Get period end from subscription items
            subscription_item = subscription["items"]["data"][0]
            period_end = subscription_item["current_period_end"]

            # Convert Unix timestamp to UTC datetime string
            end_date = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()

            # Update subscription status in Supabase
            supabase.table("users").update({
                "subscription_status": subscription["status"],
                "subscription_end_date": end_date,
            }).eq("stripe_subscription_id", subscription_id).execute()

            logger.info(f"Updated subscription {subscription_id}")

        except Exception as e:
            logger.error(f"Error handling subscription updated: {str(e)}")
            raise

    def handle_subscription_deleted(self, subscription: Dict) -> None:
        """
        Handle subscription cancellation

        Args:
            subscription: Stripe subscription object
        """
        try:
            subscription_id = subscription["id"]

            # Downgrade to free tier
            supabase.table("users").update({
                "subscription_tier": "free",
                "subscription_status": "canceled",
                "stripe_subscription_id": None,
            }).eq("stripe_subscription_id", subscription_id).execute()

            logger.info(f"Canceled subscription {subscription_id}")

        except Exception as e:
            logger.error(f"Error handling subscription deleted: {str(e)}")
            raise


# Global service instance
stripe_service = StripeService()
