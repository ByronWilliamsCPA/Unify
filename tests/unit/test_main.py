"""Smoke tests for the FastAPI application entry point.

Verifies that `foundry_unify.main:app` constructs successfully, registers
the expected routes, and gates the docs UI on the ENVIRONMENT variable.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_app_imports_and_constructs() -> None:
    """The module-level `app` object exists and is a FastAPI instance."""
    from fastapi import FastAPI

    from foundry_unify.main import app

    assert isinstance(app, FastAPI)
    assert app.title == "Foundry Unify"


@pytest.mark.unit
def test_health_router_registered() -> None:
    """Health router is mounted and /health/live responds 200."""
    from foundry_unify.main import app

    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200


@pytest.mark.unit
def test_docs_url_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ENVIRONMENT=production, the docs and redoc URLs are disabled."""
    import foundry_unify.main as main_module

    monkeypatch.setenv("ENVIRONMENT", "production")
    importlib.reload(main_module)
    try:
        assert main_module.app.docs_url is None
        assert main_module.app.redoc_url is None
    finally:
        # Restore non-production state for downstream tests
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        importlib.reload(main_module)


@pytest.mark.unit
def test_docs_url_enabled_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ENVIRONMENT is unset or non-production, /docs and /redoc are exposed."""
    import foundry_unify.main as main_module

    monkeypatch.delenv("ENVIRONMENT", raising=False)
    importlib.reload(main_module)
    assert main_module.app.docs_url == "/docs"
    assert main_module.app.redoc_url == "/redoc"
