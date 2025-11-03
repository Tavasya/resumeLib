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

    def _map_stripe_status_to_tier(self, stripe_status: str, current_tier: str) -> tuple[str, str]:
        """
        Map Stripe subscription status to our tier/status model

        Business Logic:
        - tier = "free" means user has NEVER paid
        - tier = "pro" means user HAS paid (at least once)
        - status tracks current state: active, trialing, or canceled

        Args:
            stripe_status: Status from Stripe (trialing, active, past_due, etc.)
            current_tier: User's current tier in our system

        Returns:
            tuple: (tier, status) for our system
        """
        # User is trialing - hasn't paid yet, so they're free
        if stripe_status == "trialing":
            return ("free", "trialing")

        # First successful payment - user becomes pro/active
        elif stripe_status == "active":
            return ("pro", "active")

        # Payment issues - user never successfully paid, back to free/canceled
        elif stripe_status in ["past_due", "incomplete", "incomplete_expired", "unpaid"]:
            # If they were already pro (paid before), keep them pro but canceled
            if current_tier == "pro":
                return ("pro", "canceled")
            # If they were free (never paid), they stay free/canceled
            else:
                return ("free", "canceled")

        # User canceled subscription
        elif stripe_status == "canceled":
            # Keep their tier (shows if they ever paid) but mark canceled
            return (current_tier, "canceled")

        # Fallback for unknown statuses
        else:
            logger.warning(f"Unknown Stripe status: {stripe_status}, defaulting to free/active")
            return ("free", "active")

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
            print(f"📊 Getting subscription status for user: {clerk_user_id}")

            result = supabase.table("users")\
                .select("subscription_tier, subscription_status, subscription_end_date, user_resume_url")\
                .eq("clerk_user_id", clerk_user_id)\
                .single()\
                .execute()

            if not result.data:
                raise ValueError("User not found")

            print(f"📊 Raw data from Supabase: {result.data}")

            status = result.data.get("subscription_status", "active")
            is_trialing = status == "trialing"
            tier = result.data.get("subscription_tier", "free")
            end_date = result.data.get("subscription_end_date")

            # Determine if user has Pro access
            # Pro access if:
            # 1. Currently trialing (free/trialing - has trial access)
            # 2. Paying customer (pro/active - has paid access)
            # 3. Canceled but still within period (pro/canceled with future end_date)
            has_pro_access = (
                is_trialing or  # In trial period
                (tier == "pro" and status == "active")  # Paying customer
            )

            # If canceled, check if they still have access until period ends
            if status == "canceled" and tier == "pro" and end_date:
                try:
                    # Parse ISO format datetime string
                    end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    # Still has access if subscription hasn't ended yet
                    if end_datetime > now:
                        has_pro_access = True
                except Exception:
                    # If date parsing fails, no access for canceled
                    pass

            response = {
                "tier": tier,
                "status": status,
                "end_date": end_date,
                "is_pro": has_pro_access,  # True if user has Pro access (paid OR trialing OR canceled but still in period)
                "is_trialing": is_trialing,
                "trial_end_date": end_date if is_trialing else None,
                "user_resume_url": result.data.get("user_resume_url")
            }

            print(f"📊 Returning subscription status:")
            print(f"   - Tier: {response['tier']}")
            print(f"   - Status: {response['status']}")
            print(f"   - Is Pro: {response['is_pro']} ← Has Pro Access")
            print(f"   - Is Trialing: {response['is_trialing']}")
            print(f"   - End Date: {response['end_date']}")

            return response

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

        When user completes checkout, they enter trial period (free/trialing).
        They won't become pro/active until first payment succeeds after trial.

        Args:
            session: Stripe checkout session object
        """
        try:
            clerk_user_id = session["metadata"]["clerk_user_id"]
            customer_id = session["customer"]
            subscription_id = session["subscription"]

            # Get subscription details from Stripe
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Get period dates from subscription items
            # Stripe subscriptions have current_period_start/end in the subscription items
            subscription_item = subscription['items']['data'][0]
            period_start = subscription_item['current_period_start']
            period_end = subscription_item['current_period_end']

            # Convert Unix timestamps to UTC datetime strings
            start_date = datetime.fromtimestamp(period_start, tz=timezone.utc).isoformat()
            end_date = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()

            # Map Stripe status to our tier/status model
            # New subscriptions always start as "free" tier
            tier, status = self._map_stripe_status_to_tier(
                subscription.status,
                current_tier="free"
            )

            print(f"🔔 CHECKOUT COMPLETED")
            print(f"   User: {clerk_user_id}")
            print(f"   Stripe Status: {subscription.status}")
            print(f"   → Mapped to: {tier}/{status}")

            # Update user in Supabase
            supabase.table("users").update({
                "subscription_tier": tier,
                "subscription_status": status,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "subscription_start_date": start_date,
                "subscription_end_date": end_date,
            }).eq("clerk_user_id", clerk_user_id).execute()

            logger.info(f"Updated subscription for user {clerk_user_id}: {tier}/{status} (Stripe: {subscription.status})")

        except Exception as e:
            logger.error(f"Error handling checkout completed: {str(e)}")
            raise

    def handle_subscription_updated(self, subscription: Dict) -> None:
        """
        Handle subscription update events

        This is called when subscription status changes:
        - Trial ends and payment succeeds (trialing → active): free/trialing → pro/active
        - Payment fails: stays at current tier but becomes canceled
        - Subscription renewed: stays pro/active

        Args:
            subscription: Stripe subscription object
        """
        try:
            subscription_id = subscription["id"]

            # Get current tier from database to determine if user has ever paid
            result = supabase.table("users")\
                .select("subscription_tier")\
                .eq("stripe_subscription_id", subscription_id)\
                .single()\
                .execute()

            current_tier = result.data.get("subscription_tier", "free") if result.data else "free"

            # Get period end from subscription items
            subscription_item = subscription["items"]["data"][0]
            period_end = subscription_item["current_period_end"]

            # Convert Unix timestamp to UTC datetime string
            end_date = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()

            # Map Stripe status to our tier/status model
            tier, status = self._map_stripe_status_to_tier(
                subscription["status"],
                current_tier=current_tier
            )

            print(f"🔔 SUBSCRIPTION UPDATED")
            print(f"   Subscription ID: {subscription_id}")
            print(f"   Current Tier: {current_tier}")
            print(f"   Stripe Status: {subscription['status']}")
            print(f"   → New Tier/Status: {tier}/{status}")

            # Update subscription status in Supabase
            supabase.table("users").update({
                "subscription_tier": tier,
                "subscription_status": status,
                "subscription_end_date": end_date,
            }).eq("stripe_subscription_id", subscription_id).execute()

            logger.info(f"Updated subscription {subscription_id}: {current_tier} → {tier}/{status} (Stripe: {subscription['status']})")

        except Exception as e:
            logger.error(f"Error handling subscription updated: {str(e)}")
            raise

    def handle_subscription_deleted(self, subscription: Dict) -> None:
        """
        Handle subscription deletion

        When subscription is deleted:
        - If user was pro/active (paid customer): → pro/canceled (churned customer)
        - If user was free/trialing (never paid): → free/canceled (trial abandonment)

        Args:
            subscription: Stripe subscription object
        """
        try:
            subscription_id = subscription["id"]

            # Get current tier to preserve payment history
            result = supabase.table("users")\
                .select("subscription_tier")\
                .eq("stripe_subscription_id", subscription_id)\
                .single()\
                .execute()

            current_tier = result.data.get("subscription_tier", "free") if result.data else "free"

            print(f"🔔 SUBSCRIPTION DELETED")
            print(f"   Subscription ID: {subscription_id}")
            print(f"   Current Tier: {current_tier}")
            print(f"   → Final State: {current_tier}/canceled (preserving payment history)")

            # Keep tier (to track if they ever paid), set status to canceled
            supabase.table("users").update({
                "subscription_tier": current_tier,  # Preserve tier (pro = ever paid, free = never paid)
                "subscription_status": "canceled",
                "stripe_subscription_id": None,
            }).eq("stripe_subscription_id", subscription_id).execute()

            logger.info(f"Canceled subscription {subscription_id}: user stays {current_tier}/canceled")

        except Exception as e:
            logger.error(f"Error handling subscription deleted: {str(e)}")
            raise

    def create_review_checkout_session(
        self,
        submission_id: str,
        clerk_user_id: str,
        email: str
    ) -> Dict[str, str]:
        """
        Create a Stripe checkout session for Resume Review one-time payment

        Args:
            submission_id: UUID of the review submission
            clerk_user_id: Clerk user ID
            email: User email

        Returns:
            dict: Contains checkout_url and session_id
        """
        try:
            # Get or create Stripe customer
            customer_id = self.get_or_create_customer(clerk_user_id, email)

            # Construct redirect URLs
            success_url = f"{settings.FRONTEND_URL}/resume-review/{submission_id}?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{settings.FRONTEND_URL}/resume-review/{submission_id}?payment=cancelled"

            print(f"💳 Creating review checkout session:")
            print(f"   Submission ID: {submission_id}")
            print(f"   Success URL: {success_url}")
            print(f"   Cancel URL: {cancel_url}")

            # Create one-time payment checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": settings.STRIPE_REVIEW_PRICE_ID,
                        "quantity": 1,
                    }
                ],
                mode="payment",  # One-time payment (not subscription)
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "clerk_user_id": clerk_user_id,
                    "submission_id": submission_id,
                    "type": "resume_review",  # Distinguish from subscription payments
                },
            )

            print(f"✅ Checkout session created:")
            print(f"   Session ID: {checkout_session.id}")
            print(f"   Checkout URL: {checkout_session.url}")

            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            }

        except Exception as e:
            logger.error(f"Error creating review checkout session: {str(e)}")
            raise

    def handle_review_payment_success(self, session: Dict) -> None:
        """
        Handle successful review payment

        Args:
            session: Stripe checkout session object
        """
        try:
            submission_id = session["metadata"]["submission_id"]
            payment_intent_id = session.get("payment_intent")

            # Update review submission as paid
            supabase.table("review_submissions").update({
                "paid": True,
                "stripe_session_id": session["id"],
                "stripe_payment_intent_id": payment_intent_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", submission_id).execute()

            logger.info(f"Marked review submission {submission_id} as paid")

        except Exception as e:
            logger.error(f"Error handling review payment success: {str(e)}")
            raise


# Global service instance
stripe_service = StripeService()
