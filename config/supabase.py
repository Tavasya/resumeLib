"""
Supabase client configuration and initialization
"""
from supabase import create_client, Client
from .settings import settings


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance

    Returns:
        Client: Initialized Supabase client
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


# Global Supabase client instance
supabase: Client = get_supabase_client()
