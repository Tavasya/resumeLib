"""
Stripe client configuration and initialization
"""
import stripe
from .settings import settings


# Initialize Stripe with API key
stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_client():
    """
    Get the configured Stripe module

    Returns:
        stripe module with API key configured
    """
    return stripe
