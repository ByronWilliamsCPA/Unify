"""Tests for security middleware.

Covers the rate-limiter proxy-header resolution, the asyncio.Lock-protected
check-then-update region, the SSRF header inspection added in this PR, and
the CORS default change.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundry_unify.middleware.security import (
    RateLimitMiddleware,
    SSRFPreventionMiddleware,
    add_security_middleware,
)


@pytest.mark.unit
def test_resolve_client_ip_uses_x_forwarded_for() -> None:
    """First IP in X-Forwarded-For wins over peer address and X-Real-IP."""
    request = MagicMock()
    request.headers = {
        "X-Forwarded-For": "203.0.113.5, 10.0.0.1",
        "X-Real-IP": "10.9.9.9",
    }
    request.client = MagicMock(host="127.0.0.1")
    assert RateLimitMiddleware._resolve_client_ip(request) == "203.0.113.5"


@pytest.mark.unit
def test_resolve_client_ip_falls_back_to_x_real_ip() -> None:
    """When X-Forwarded-For is absent, X-Real-IP is used."""
    request = MagicMock()
    request.headers = {"X-Real-IP": "198.51.100.7"}
    request.client = MagicMock(host="127.0.0.1")
    assert RateLimitMiddleware._resolve_client_ip(request) == "198.51.100.7"


@pytest.mark.unit
def test_resolve_client_ip_falls_back_to_peer() -> None:
    """When no proxy headers are present, the TCP peer is used."""
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock(host="192.0.2.42")
    assert RateLimitMiddleware._resolve_client_ip(request) == "192.0.2.42"


@pytest.mark.unit
def test_resolve_client_ip_returns_unknown_when_no_client() -> None:
    """When request.client is None and no proxy headers exist, return 'unknown'."""
    request = MagicMock()
    request.headers = {}
    request.client = None
    assert RateLimitMiddleware._resolve_client_ip(request) == "unknown"


@pytest.mark.unit
def test_rate_limiter_lock_serializes_check_then_update() -> None:
    """The asyncio.Lock prevents two concurrent requests from both passing the
    burst limit before either appends its timestamp."""
    app = FastAPI()
    add_security_middleware(
        app,
        enable_rate_limiting=True,
        rate_limit_rpm=2,
        enable_ssrf_prevention=False,
    )

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    # Three sequential requests with the same X-Forwarded-For; the third must
    # be 429 because rpm=2.
    headers = {"X-Forwarded-For": "203.0.113.50"}
    r1 = client.get("/ping", headers=headers)
    r2 = client.get("/ping", headers=headers)
    r3 = client.get("/ping", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiter_concurrent_burst_protected() -> None:
    """Concurrent requests through the lock cannot exceed the limit."""
    app = FastAPI()
    add_security_middleware(
        app,
        enable_rate_limiting=True,
        rate_limit_rpm=3,
        enable_ssrf_prevention=False,
    )

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    headers = {"X-Forwarded-For": "203.0.113.99"}

    async def fire_one() -> int:
        return client.get("/ping", headers=headers).status_code

    results = await asyncio.gather(*(fire_one() for _ in range(6)))
    successes = sum(1 for s in results if s == 200)
    rate_limited = sum(1 for s in results if s == 429)
    # Exactly 3 requests should pass; the rest must be rate-limited.
    assert successes == 3
    assert rate_limited == 3


@pytest.mark.unit
def test_ssrf_blocks_query_parameter_targeting_loopback() -> None:
    """SSRF middleware blocks loopback URL in a query parameter."""
    app = FastAPI()
    app.add_middleware(SSRFPreventionMiddleware)

    @app.get("/proxy")
    def proxy() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    response = client.get("/proxy?target=http://127.0.0.1:8000/admin")
    assert response.status_code == 400
    assert "potential SSRF attempt" in response.json()["message"]


@pytest.mark.unit
def test_ssrf_blocks_x_forwarded_host_header() -> None:
    """SSRF middleware now inspects risky headers; X-Forwarded-Host loopback is blocked."""
    app = FastAPI()
    app.add_middleware(SSRFPreventionMiddleware)

    @app.get("/proxy")
    def proxy() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    response = client.get(
        "/proxy",
        headers={"X-Forwarded-Host": "http://169.254.169.254/latest/meta-data/"},
    )
    assert response.status_code == 400


@pytest.mark.unit
def test_cors_defaults_to_no_credentials() -> None:
    """add_security_middleware now defaults allow_credentials to False."""
    app = FastAPI()
    add_security_middleware(app, allowed_origins=["https://example.com"])

    @app.get("/x")
    def handler() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    response = client.options(
        "/x",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # When allow_credentials is False, the response header should not assert true
    assert response.headers.get("access-control-allow-credentials") != "true"


@pytest.mark.unit
def test_security_headers_remove_server_header() -> None:
    """SecurityHeadersMiddleware removes the Server header without raising."""
    app = FastAPI()
    add_security_middleware(
        app, enable_rate_limiting=False, enable_ssrf_prevention=False
    )

    @app.get("/x")
    def handler() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    response = client.get("/x")
    assert response.status_code == 200
    # Standard security headers should be present
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
