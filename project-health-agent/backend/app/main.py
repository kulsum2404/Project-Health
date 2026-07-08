"""
FastAPI application entrypoint.

Sets up CORS, lifespan events (DB init, scheduler), and mounts all routers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine

from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Database engine (module-level for reuse)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
        )
    return _engine


def get_session():
    """Yield a database session for dependency injection."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — init DB and optional scheduler on startup."""
    settings = get_settings()
    logger.info("Starting %s", settings.app_name)

    # Create all tables
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created/verified")

    # Ensure upload and reports directories exist
    settings.upload_path
    settings.reports_path

    # Start scheduler if enabled
    if settings.scheduler_enabled:
        try:
            from app.scheduler.weekly_job import start_scheduler
            start_scheduler()
            logger.info("Scheduler started with cron: %s", settings.scheduler_cron)
        except Exception as e:
            logger.error("Failed to start scheduler: %s", e)

    yield

    # Cleanup
    logger.info("Shutting down %s", settings.app_name)
    if settings.scheduler_enabled:
        try:
            from app.scheduler.weekly_job import stop_scheduler
            stop_scheduler()
        except Exception:
            pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered project health reporting with RAG classification",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    from app.api.projects import router as projects_router
    from app.api.reports import router as reports_router
    from app.api.monthly import router as monthly_router

    app.include_router(projects_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(monthly_router, prefix="/api")

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "app": settings.app_name}

    return app


app = create_app()
