"""FastAPI application entry point for Foundry Unify.

Exposes `app` for use by the uvicorn runner:
    uvicorn foundry_unify.main:app
"""

from __future__ import annotations

from fastapi import FastAPI

from foundry_unify import __version__
from foundry_unify.api.health import router as health_router
from foundry_unify.middleware.correlation import CorrelationMiddleware
from foundry_unify.middleware.security import add_security_middleware

app = FastAPI(
    title="Foundry Unify",
    description="OCR orchestration and layout analysis service for the Foundry RAG pipeline",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CorrelationMiddleware)
add_security_middleware(app)

app.include_router(health_router)
