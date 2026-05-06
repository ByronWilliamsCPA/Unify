"""API package for Foundry Unify.

This package contains FastAPI routers and API-related functionality.
"""

from __future__ import annotations

from foundry_unify.api.health import router as health_router

__all__ = ["health_router"]
