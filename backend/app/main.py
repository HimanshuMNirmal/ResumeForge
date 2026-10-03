"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import engine
from .auth.router import router as auth_router
from .profile.router import router as profile_router
from .keys.router import router as keys_router
from .resume.router import router as resume_router
from .history.router import router as history_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("ResumeForge API starting up…")
    yield
    await engine.dispose()
    logger.info("ResumeForge API shut down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,          # required for HttpOnly cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(auth_router, prefix=prefix)
    app.include_router(profile_router, prefix=prefix)
    app.include_router(keys_router, prefix=prefix)
    app.include_router(resume_router, prefix=prefix)
    app.include_router(history_router, prefix=prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    # ── Global exception handlers ─────────────────────────────────────────────
    from fastapi.exceptions import RequestValidationError
    from fastapi import HTTPException
    from .errors import (
        http_exception_handler,
        unhandled_exception_handler,
        validation_exception_handler,
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    return app


app = create_app()
