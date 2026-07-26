from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_middleware
from app.startup.events import on_shutdown, on_startup

configure_logging()
logger = get_logger(__name__)

# Resolved at import time: backend/app/main.py → backend/ → repo root → frontend/dist
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await on_startup()
    yield
    await on_shutdown()


def _mount_frontend(app: FastAPI) -> None:
    """Serve the React production build from FastAPI when the dist/ folder exists.

    StaticFiles(html=True) serves index.html for directory requests,
    giving us SPA catch-all behavior.  Because this is mounted *after*
    the API router, /api/v1/* routes always take priority.
    """
    if not _FRONTEND_DIST.is_dir():
        logger.info("frontend_not_mounted", reason="dist directory not found", path=str(_FRONTEND_DIST))
        return

    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
    logger.info("frontend_mounted", path=str(_FRONTEND_DIST))


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="AI-Powered Behavioral Anomaly Detection Platform",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # In production (Render), serve the React frontend from the same process.
    # In development, the Vite dev server runs separately — dist/ won't exist.
    _mount_frontend(app)

    return app


app = create_app()