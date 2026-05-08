"""FastAPI application entry point for Foundry Unify.

Exposes `app` for use by the uvicorn runner:
    uvicorn foundry_unify.main:app
"""

from __future__ import annotations

import os

from fastapi import FastAPI

from foundry_unify import __version__
from foundry_unify.api.health import router as health_router
from foundry_unify.middleware.correlation import CorrelationMiddleware
from foundry_unify.middleware.security import add_security_middleware

# #ASSUME: Security: ENVIRONMENT signals trusted production deployment context
# #VERIFY: docker-compose.prod.yml sets ENVIRONMENT=production; staging/dev unset
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "").lower() == "production"

# #CRITICAL: Security: docs UI exposes full API contract; disable in production
# #VERIFY: docs_url/redoc_url are None when ENVIRONMENT=production
app = FastAPI(
    title="Foundry Unify",
    description=(
        "OCR orchestration and layout analysis service for the Foundry RAG pipeline"
    ),
    version=__version__,
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
)

# #ASSUME: Concurrency: middleware order matters; correlation runs first to
# tag every request, security middleware runs second so it sees the tag.
# #VERIFY: integration test asserts X-Correlation-ID propagates through stack
app.add_middleware(CorrelationMiddleware)
add_security_middleware(app)

app.include_router(health_router)
