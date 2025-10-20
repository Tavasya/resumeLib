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

    # Application
    APP_NAME: str = "Resume Library"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
