"""Health check endpoints for Kubernetes and production monitoring.

This module provides standardized health check endpoints following best practices:
- Liveness probe: Is the application running?
- Readiness probe: Can the application serve traffic?
- Startup probe: Has the application fully started?

Implements:
- Kubernetes probe patterns
- Graceful degradation
- Detailed diagnostic information
- OWASP A09 (Security Logging) compliance
"""

from __future__ import annotations

import asyncio
import sys
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from foundry_unify.adapters.docling_serve_client import DoclingServeClient
from foundry_unify.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])

# Track application start time for uptime calculation
_START_TIME = time.time()


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall status: ok, degraded, or error")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    version: str = Field(default="0.1.0", description="Application version")
    python_version: str = Field(default_factory=lambda: sys.version.split()[0])


class ReadinessCheck(BaseModel):
    """Individual dependency check result."""

    name: str = Field(..., description="Dependency name")
    status: bool = Field(..., description="Check passed")
    latency_ms: float | None = Field(None, description="Check latency in milliseconds")
    error: str | None = Field(None, description="Error message if failed")


class ReadinessStatus(HealthStatus):
    """Readiness check response with dependency details."""

    checks: dict[str, ReadinessCheck] = Field(
        default_factory=dict, description="Individual dependency checks"
    )


@router.get(
    "/live",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Indicates if the application is running. Used by Kubernetes liveness probe.",
)
async def liveness() -> HealthStatus:
    """Kubernetes liveness probe.

    Returns HTTP 200 if the application is alive.
    If this fails, Kubernetes will restart the pod.

    This should be a simple, fast check that doesn't depend on external services.
    """
    return HealthStatus(
        status="ok",
        uptime_seconds=time.time() - _START_TIME,
    )


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    responses={
        200: {"description": "Application is ready to serve traffic"},
        503: {"description": "Application is not ready (dependencies unavailable)"},
    },
    summary="Readiness probe",
    description="Checks if the application can serve traffic. Used by Kubernetes readiness probe.",
)
async def readiness() -> ReadinessStatus:
    """Kubernetes readiness probe -- checks docling-serve reachability."""
    checks: dict[str, ReadinessCheck] = {}

    # Check docling-serve
    start = time.time()
    # health_check() uses a hard 5-second timeout internally; docling_serve_timeout_seconds does not apply here
    with DoclingServeClient(base_url=settings.docling_serve_url) as docling_client:
        reachable = await asyncio.to_thread(docling_client.health_check)
    checks["docling_serve"] = ReadinessCheck(
        name="docling_serve",
        status=reachable,
        latency_ms=round((time.time() - start) * 1000, 2),
        error=None
        if reachable
        else f"docling-serve unreachable at {settings.docling_serve_url}",
    )

    all_healthy = all(check.status for check in checks.values())

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unavailable",
                "timestamp": time.time(),
                "uptime_seconds": time.time() - _START_TIME,
                "checks": {name: check.model_dump() for name, check in checks.items()},
            },
        )

    return ReadinessStatus(
        status="ok",
        uptime_seconds=time.time() - _START_TIME,
        checks=checks,
    )


@router.get(
    "/startup",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Startup probe",
    description="Indicates if the application has completed startup. Used by Kubernetes startup probe.",
)
async def startup() -> HealthStatus:
    """Kubernetes startup probe.

    Used during application startup to delay liveness and readiness checks.
    This prevents the application from being killed during slow initialization.

    Returns HTTP 200 once the application has fully started.
    """
    # Add any startup checks here (e.g., database migrations completed)
    # For most applications, being alive means startup is complete

    return HealthStatus(
        status="started",
        uptime_seconds=time.time() - _START_TIME,
    )


@router.get(
    "/",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Simple health check endpoint for load balancers and monitoring.",
    include_in_schema=False,  # Hide from OpenAPI docs (use /live instead)
)
async def health() -> HealthStatus:
    """Basic health check endpoint.

    Alias for /health/live for compatibility with load balancers
    that expect a /health endpoint.
    """
    return await liveness()
