import logging
import time

import httpx
from fastapi import APIRouter, Request

from config.settings import get_settings
from integrations.llm import DEFAULT_PROVIDER, MODEL_BY_PROVIDER, get_llm

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health(request: Request):
    """Liveness probe. Cheap, no external calls — safe to poll."""
    return {"status": "ok", "version": request.app.version}


@router.get("/health/deep")
async def health_deep(request: Request):
    """Readiness probe. Calls out to every dependency, including the LLM.

    Costs one LLM request, so this is deliberately not the endpoint a load
    balancer polls.
    """
    checks: dict[str, dict] = {}
    overall = "ok"

    # --- Supabase ---
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/",
                headers={"apikey": settings.SUPABASE_SERVICE_KEY},
            )
        resp.raise_for_status()
        checks["supabase"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception:
        logger.exception("supabase health check failed")
        checks["supabase"] = {"status": "error"}
        overall = "degraded"

    # --- LLM ---
    # Probe the provider the app actually runs on. Naming a role here (the
    # old "synthesis") silently fell through to the other vendor.
    t0 = time.monotonic()
    try:
        llm = get_llm()
        await llm.ainvoke("ping")
        checks["llm"] = {
            "status": "ok",
            "provider": DEFAULT_PROVIDER,
            "model": MODEL_BY_PROVIDER[DEFAULT_PROVIDER],
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception:
        logger.exception("llm health check failed")
        checks["llm"] = {"status": "error"}
        overall = "degraded"

    # --- LangSmith ---
    checks["langsmith"] = {
        "status": "ok" if settings.LANGSMITH_API_KEY else "disabled",
        "tracing": settings.LANGSMITH_TRACING,
        "project": settings.LANGSMITH_PROJECT,
    }

    return {"status": overall, "version": request.app.version, "checks": checks}
