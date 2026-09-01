from config.settings import get_settings


def test_get_settings():
    """Test that get_settings returns a Settings object."""
    settings = get_settings()
    assert settings is not None


def test_settings_has_groq_api_key():
    """Test that settings contains GROQ_API_KEY."""
    settings = get_settings()
    assert hasattr(settings, "GROQ_API_KEY")


def test_settings_has_langfuse_keys():
    """Test that settings contains the Langfuse credentials."""
    settings = get_settings()
    assert hasattr(settings, "LANGFUSE_PUBLIC_KEY")
    assert hasattr(settings, "LANGFUSE_SECRET_KEY")
    assert hasattr(settings, "LANGFUSE_BASE_URL")


def test_settings_has_tavily_api_key():
    """Test that settings contains TAVILY_API_KEY."""
    settings = get_settings()
    assert hasattr(settings, "TAVILY_API_KEY")


def test_get_settings_is_cached():
    """Test that get_settings uses lru_cache (returns same instance)."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2