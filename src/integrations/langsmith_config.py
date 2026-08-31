import logging
import os

from langsmith import Client

from config.settings import get_settings

logger = logging.getLogger(__name__)


def init_tracing() -> Client | None:
    """Initialise LangSmith tracing.

    Returns None when tracing is switched off or unconfigured — tracing is
    observability, so a missing key must never stop the app from starting.
    """
    settings = get_settings()

    if not settings.LANGSMITH_TRACING:
        logger.info("LangSmith tracing disabled (LANGSMITH_TRACING is false)")
        return None

    if not settings.LANGSMITH_API_KEY:
        logger.warning("LANGSMITH_TRACING is on but LANGSMITH_API_KEY is empty; tracing disabled")
        return None

    # LangChain reads these env vars itself, so they must be set on the process.
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

    return Client()


def run_config(research_id: str) -> dict:
    """Pass to .ainvoke(config=...) so every run is
    searchable in LangSmith by research task."""
    return {
        "run_name": "research",
        "tags": ["research", research_id],
        "metadata": {"research_id": research_id},
    }
