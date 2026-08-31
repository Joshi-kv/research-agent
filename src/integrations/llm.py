from functools import lru_cache

from langchain_groq import ChatGroq

from config.settings import get_settings

DEFAULT_ROLE = "synthesis"

MODEL_BY_ROLE = {
    "search": "groq/compound",          # Groq's agentic model, built for tool use & search
    "scrape": "qwen/qwen3.8-27b",       # Strong 27B model, good at extraction & structured reading
    "synthesis": "openai/gpt-oss-120b",  # Largest available model, best for final synthesis
}


@lru_cache
def get_llm(role: str = DEFAULT_ROLE, temperature: float = 0.0) -> ChatGroq:
    """Return a cached ChatGroq client for the given role.

    Unknown roles fall back to the default model rather than constructing a
    client with model=None, which fails only later at call time.
    """
    model_name = MODEL_BY_ROLE.get(role, MODEL_BY_ROLE[DEFAULT_ROLE])
    settings = get_settings()

    return ChatGroq(
        model=model_name,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
    )
