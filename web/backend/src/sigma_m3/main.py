"""Compose the local API; HTTP requests never fit models or upload raw data."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sigma_m3.core.db import database
from sigma_m3.core.http import install_error_handlers, router as health_router
from sigma_m3.core.settings import PROJECT_ROOT, Settings
from sigma_m3.modules.catalog.router import router as catalog_router
from sigma_m3.modules.configuration.router import router as configuration_router
from sigma_m3.api.runs import router as runs_router
from sigma_m3.api.monthly import router as monthly_router
from sigma_m3.api.workspace import router as workspace_router
from sigma_m3.api.purchasing import router as purchasing_router
from sigma_m3.api.results import router as results_router


def create_app(settings=None):
    settings = settings or Settings.from_env()
    engine, sessions = database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="SIGMA M3 local API", version="0.1.0", lifespan=lifespan)
    app.state.engine, app.state.sessions, app.state.settings = engine, sessions, settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )
    install_error_handlers(app)
    for router in (
        health_router, catalog_router, configuration_router, runs_router,
        monthly_router, workspace_router, purchasing_router, results_router,
    ):
        app.include_router(router)
    frontend = PROJECT_ROOT / "M3/frontend/dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
