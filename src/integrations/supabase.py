from functools import lru_cache

from supabase import create_client, Client

from config.settings import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get the Supabase client"""
    settings = get_settings()
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
        )
    
def get_table(table_name: str):
    """Get the Supabase table"""
    client = get_supabase_client()
    return client.table(table_name)


