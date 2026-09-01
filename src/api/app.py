from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.health import router as health_router
from api.routes.research import router as research_router
from config.settings import get_settings
from integrations.langfuse_config import init_tracing, shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialise tracing, flush on shutdown."""
    app.state.langfuse = init_tracing()
    yield
    # Langfuse batches spans and flush() does not wait for the in-flight
    # request, so a plain flush here can lose the last requests' traces.
    shutdown()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Research Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # allow_credentials + a wildcard origin is rejected by browsers and silently
    # disables CORS, so refuse the combination loudly instead.
    allow_credentials = "*" not in settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(research_router)

    return app
