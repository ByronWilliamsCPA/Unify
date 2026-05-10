"""Tests for security middleware components."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundry_unify.middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    SSRFPreventionMiddleware,
    add_security_middleware,
)


def _make_app_with_security_headers() -> FastAPI:
    """Return a minimal FastAPI app with SecurityHeadersMiddleware."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        """Health check."""
        return {"ok": "true"}

    return app


@pytest.mark.unit
def test_security_headers_added_to_response() -> None:
    """SecurityHeadersMiddleware adds OWASP headers to every response."""
    client = TestClient(_make_app_with_security_headers())
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


@pytest.mark.unit
def test_security_headers_no_hsts_on_http() -> None:
    """Strict-Transport-Security is omitted for plain-HTTP requests."""
    client = TestClient(_make_app_with_security_headers())
    response = client.get("/ping")
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.unit
def test_add_security_middleware_installs_without_error() -> None:
    """add_security_middleware runs without raising and produces a usable app."""
    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, str]:
        """Health check."""
        return {"ok": "true"}

    add_security_middleware(app)
    client = TestClient(app, raise_server_exceptions=True)
    response = client.get("/ping")
    assert response.status_code == 200


@pytest.mark.unit
def test_add_security_middleware_with_options() -> None:
    """add_security_middleware accepts rate-limiting and SSRF options."""
    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, str]:
        """Health check."""
        return {"ok": "true"}

    add_security_middleware(
        app,
        enable_rate_limiting=True,
        rate_limit_rpm=300,
        enable_ssrf_prevention=True,
    )
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/ping")
    assert response.status_code == 200


@pytest.mark.unit
def test_rate_limit_middleware_init_defaults() -> None:
    """RateLimitMiddleware stores constructor parameters."""
    from starlette.applications import Starlette

    inner = Starlette()
    rl = RateLimitMiddleware(inner, requests_per_minute=120, burst_size=20)
    assert rl.requests_per_minute == 120
    assert rl.burst_size == 20


@pytest.mark.unit
def test_ssrf_private_ip_loopback() -> None:
    """SSRFPreventionMiddleware._is_private_ip returns True for loopback addresses."""
    assert SSRFPreventionMiddleware._is_private_ip("127.0.0.1") is True
    assert SSRFPreventionMiddleware._is_private_ip("::1") is True


@pytest.mark.unit
def test_ssrf_private_ip_rfc1918() -> None:
    """SSRFPreventionMiddleware._is_private_ip returns True for RFC-1918 ranges."""
    assert SSRFPreventionMiddleware._is_private_ip("10.0.0.1") is True
    assert SSRFPreventionMiddleware._is_private_ip("192.168.1.1") is True
    assert SSRFPreventionMiddleware._is_private_ip("172.16.0.1") is True


@pytest.mark.unit
def test_ssrf_private_ip_public_address() -> None:
    """SSRFPreventionMiddleware._is_private_ip returns False for public IPs."""
    assert SSRFPreventionMiddleware._is_private_ip("8.8.8.8") is False


@pytest.mark.unit
def test_ssrf_private_ip_invalid_string() -> None:
    """SSRFPreventionMiddleware._is_private_ip returns False for non-IP strings."""
    assert SSRFPreventionMiddleware._is_private_ip("not-an-ip") is False
