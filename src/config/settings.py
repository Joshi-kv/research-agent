from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # A .env accumulates keys for tools that read the environment directly.
        # Rejecting them would make an unrelated leftover crash the app at boot.
        extra="ignore",
    )

    # LLM
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    # TOOLS
    TAVILY_API_KEY: str

    # SUPABASE
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    # Only needed once we verify user JWTs ourselves; optional until then.
    SUPABASE_JWT_KEY: str = ""

    # OBSERVABILITY
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    # Point at a self-hosted deployment to keep traces on your own infra.
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_ENVIRONMENT: str = "development"
    # Tracing turns itself on once both keys are set; flip this to false to keep
    # it off without having to remove them.
    LANGFUSE_TRACING: bool = True
    
    #APP
    CORS_ORIGINS: list[str] = []
    
@lru_cache
def get_settings() -> Settings:
    return Settings()