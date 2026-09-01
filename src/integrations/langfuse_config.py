"""Langfuse tracing.

Replaces the LangSmith integration. Two things it does better here:

* One trace per research run. LangSmith was wired through env vars, so each
  agent .invoke() became its own disconnected root run - five traces per
  request with nothing tying them together. `trace_run()` opens a root span and
  every step nests underneath it.
* Self-hostable. LANGFUSE_BASE_URL points anywhere, so this works against
  cloud.langfuse.com or a local docker deployment with no code change.

Tracing is observability: every failure path here degrades to "no tracing"
rather than taking the app down.
"""

import logging
from contextlib import contextmanager, nullcontext

from langfuse import Langfuse, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from config.settings import get_settings

logger = logging.getLogger(__name__)

_client: Langfuse | None = None


def init_tracing() -> Langfuse | None:
    """Initialise the Langfuse client. Returns None when tracing is off.

    Called once from the app lifespan. The credentials are verified up front so
    a typo shows up in the startup log instead of silently dropping every trace.
    """
    global _client
    settings = get_settings()

    if not settings.LANGFUSE_TRACING:
        logger.info("Langfuse tracing disabled (LANGFUSE_TRACING is false)")
        _client = None
        return None

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        logger.info(
            "Langfuse tracing disabled (LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY unset)"
        )
        _client = None
        return None

    try:
        client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            base_url=settings.LANGFUSE_BASE_URL,
            environment=settings.LANGFUSE_ENVIRONMENT,
            tracing_enabled=True,
        )
        if not client.auth_check():
            logger.warning(
                "Langfuse credentials rejected by %s; tracing disabled",
                settings.LANGFUSE_BASE_URL,
            )
            _client = None
            return None
    except Exception:
        logger.exception("Langfuse init failed; continuing without tracing")
        _client = None
        return None

    logger.info("Langfuse tracing enabled (%s)", settings.LANGFUSE_BASE_URL)
    _client = client
    return client


def get_langfuse() -> Langfuse | None:
    """The initialised client, or None when tracing is off."""
    return _client


def get_handler() -> CallbackHandler | None:
    """LangChain callback handler, or None when tracing is off.

    Pass into .invoke(config={"callbacks": [...]}) so LLM calls, tool calls and
    token usage land under the current span.
    """
    if _client is None:
        return None
    try:
        return CallbackHandler()
    except Exception:
        logger.exception("could not build Langfuse callback handler")
        return None


def callbacks() -> list:
    """Callback list for a runnable config. Empty when tracing is off."""
    handler = get_handler()
    return [handler] if handler else []


@contextmanager
def trace_run(name: str, *, input: dict | None = None, tags: list[str] | None = None):
    """Group everything inside into a single Langfuse trace.

    A no-op context manager when tracing is off, so callers never branch.
    Yields the trace id (None when untraced) so it can be returned to the caller
    or written alongside the stored result.
    """
    if _client is None:
        with nullcontext():
            yield None
        return

    try:
        with _client.start_as_current_observation(
            name=name, as_type="span", input=input
        ):
            with propagate_attributes(trace_name=name, tags=tags or []):
                yield _client.get_current_trace_id()
    except Exception:
        # A tracing backend that is down must not fail the research run.
        logger.exception("Langfuse trace failed; continuing untraced")
        yield None


def update_trace(output=None, metadata: dict | None = None) -> None:
    """Attach the result to the span opened by trace_run()."""
    if _client is None:
        return
    try:
        _client.update_current_span(output=output, metadata=metadata)
    except Exception:
        logger.exception("could not update Langfuse span")


def flush() -> None:
    """Flush buffered spans. Langfuse batches, so shutdown must drain."""
    if _client is not None:
        try:
            _client.flush()
        except Exception:
            logger.exception("Langfuse flush failed")
