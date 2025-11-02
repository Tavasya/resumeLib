from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Google Custom Search
    GOOGLE_API_KEY: str
    GOOGLE_CX: str

    # OpenAI
    OPENAI_API_KEY: str

    # Clerk Authentication
    CLERK_PUBLISHABLE_KEY: str
    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str
    CLERK_JWKS_URL: str

    # Stripe Payment
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_ID_PRO: str  # Price ID for Pro subscription
    STRIPE_REVIEW_PRICE_ID: str  # Price ID for Resume Review one-time payment

    # Application
    APP_NAME: str = "Resume Library"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"  # For Stripe redirects

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
