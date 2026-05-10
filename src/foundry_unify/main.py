"""FastAPI application factory for Foundry Unify."""

from __future__ import annotations

from fastapi import FastAPI

from foundry_unify.api import health_router
from foundry_unify.api.process import router as process_router

app = FastAPI(
    title="Foundry Unify",
    description="OCR orchestration and layout analysis service for the Foundry RAG pipeline",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(process_router)
