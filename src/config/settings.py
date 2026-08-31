from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # LLM
    GROQ_API_KEY: str

    # TOOLS
    TAVILY_API_KEY: str

    # SUPABASE
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    # Only needed once we verify user JWTs ourselves; optional until then.
    SUPABASE_JWT_KEY: str = ""

    # OBSERVABILITY
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "research-assistant"
    
    #APP
    CORS_ORIGINS: list[str] = []
    
@lru_cache
def get_settings() -> Settings:
    return Settings()