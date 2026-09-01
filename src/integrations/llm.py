from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from config.settings import get_settings

DEFAULT_PROVIDER = "google"

MODEL_BY_PROVIDER = {
    "google": "gemini-3.1-flash-lite",
    "groq": "openai/gpt-oss-120b",
}


@lru_cache
def get_llm(
    provider: str = DEFAULT_PROVIDER, temperature: float = 0.0
) -> BaseChatModel:
    """Return a cached chat model for the given provider.

    Unknown providers raise. The previous version fell through to Groq for any
    string that was not exactly "google", so a typo silently swapped vendors and
    only showed up as a different model in the response.
    """
    model = MODEL_BY_PROVIDER.get(provider)
    if model is None:
        raise ValueError(
            f"Unknown LLM provider {provider!r}. "
            f"Expected one of: {', '.join(sorted(MODEL_BY_PROVIDER))}."
        )

    settings = get_settings()
    if provider == "google":
        return ChatGoogleGenerativeAI(
            api_key=settings.GOOGLE_API_KEY,
            model=model,
            temperature=temperature,
        )
    return ChatGroq(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
    )
