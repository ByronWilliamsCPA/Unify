"""Tests for security middleware components.

Covers SecurityHeadersMiddleware, RateLimitMiddleware, SSRFPreventionMiddleware,
and the add_security_middleware helper.
"""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def plain_app() -> FastAPI:
    """FastAPI app with no middleware for bare middleware testing."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"ok": "true"}

    return app


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def client(self, plain_app: FastAPI) -> TestClient:
        from foundry_unify.middleware.security import SecurityHeadersMiddleware

        plain_app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(plain_app, raise_server_exceptions=True)

    @pytest.mark.unit
    def test_x_content_type_options(self, client: TestClient) -> None:
        """Middleware sets X-Content-Type-Options: nosniff."""
        response = client.get("/")
        assert response.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.unit
    def test_x_frame_options(self, client: TestClient) -> None:
        """Middleware sets X-Frame-Options: DENY."""
        response = client.get("/")
        assert response.headers.get("x-frame-options") == "DENY"

    @pytest.mark.unit
    def test_x_xss_protection(self, client: TestClient) -> None:
        """Middleware sets X-XSS-Protection header."""
        response = client.get("/")
        assert response.headers.get("x-xss-protection") == "1; mode=block"

    @pytest.mark.unit
    def test_content_security_policy(self, client: TestClient) -> None:
        """Middleware sets Content-Security-Policy header."""
        response = client.get("/")
        csp = response.headers.get("content-security-policy", "")
        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    @pytest.mark.unit
    def test_referrer_policy(self, client: TestClient) -> None:
        """Middleware sets Referrer-Policy header."""
        response = client.get("/")
        assert (
            response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        )

    @pytest.mark.unit
    def test_permissions_policy(self, client: TestClient) -> None:
        """Middleware sets Permissions-Policy header."""
        response = client.get("/")
        policy = response.headers.get("permissions-policy", "")
        assert "geolocation=()" in policy

    @pytest.mark.unit
    def test_no_hsts_on_http(self, client: TestClient) -> None:
        """Middleware does not add HSTS header on plain HTTP."""
        response = client.get("/")
        assert "strict-transport-security" not in response.headers


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def rate_limited_client(self, plain_app: FastAPI) -> TestClient:
        from foundry_unify.middleware.security import RateLimitMiddleware

        plain_app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=5,
            burst_size=3,
            max_tracked_ips=100,
            cleanup_interval=300,
        )
        return TestClient(plain_app, raise_server_exceptions=False)

    @pytest.mark.unit
    def test_allows_requests_under_limit(self, rate_limited_client: TestClient) -> None:
        """Requests below the rate limit pass through."""
        for _ in range(3):
            response = rate_limited_client.get("/")
            assert response.status_code == 200

    @pytest.mark.unit
    def test_blocks_requests_over_rate_limit(self, plain_app: FastAPI) -> None:
        """Requests exceeding per-minute limit return 429."""
        from foundry_unify.middleware.security import RateLimitMiddleware

        app = FastAPI()

        @app.get("/check")
        async def check() -> dict[str, str]:
            return {"ok": "true"}

        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=2,
            burst_size=10,
        )
        client = TestClient(app, raise_server_exceptions=False)

        # First two should pass
        for _ in range(2):
            client.get("/check")

        # Third should be rate limited
        response = client.get("/check")
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "Too Many Requests"

    @pytest.mark.unit
    def test_burst_limit_returns_429(self, plain_app: FastAPI) -> None:
        """Rapid burst requests exceeding burst_size return 429."""
        from foundry_unify.middleware.security import RateLimitMiddleware

        app = FastAPI()

        @app.get("/burst")
        async def burst() -> dict[str, str]:
            return {"ok": "true"}

        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=100,
            burst_size=1,
        )
        client = TestClient(app, raise_server_exceptions=False)

        # Both requests happen in the same second, second should hit burst limit
        client.get("/burst")
        response = client.get("/burst")
        assert response.status_code == 429

    @pytest.mark.unit
    def test_rate_limit_response_has_retry_after(self, plain_app: FastAPI) -> None:
        """Rate limit 429 response includes Retry-After header."""
        from foundry_unify.middleware.security import RateLimitMiddleware

        app = FastAPI()

        @app.get("/retry")
        async def retry() -> dict[str, str]:
            return {"ok": "true"}

        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=1,
            burst_size=10,
        )
        client = TestClient(app, raise_server_exceptions=False)

        client.get("/retry")
        response = client.get("/retry")
        assert response.status_code == 429
        assert "retry-after" in response.headers

    @pytest.mark.unit
    def test_handles_missing_client(self) -> None:
        """Middleware uses 'unknown' fallback when client is None."""
        from foundry_unify.middleware.security import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(app, requests_per_minute=10, burst_size=5)

        mock_request = MagicMock()
        mock_request.client = None

        mock_response = MagicMock()

        async def call_next(_req):
            return mock_response

        import asyncio

        response = asyncio.get_event_loop().run_until_complete(
            middleware.dispatch(mock_request, call_next)
        )
        assert response is mock_response
        assert "unknown" in middleware.requests

    @pytest.mark.unit
    def test_cleanup_removes_stale_ips(self) -> None:
        """_cleanup_stale_entries removes IPs with no recent activity."""
        from foundry_unify.middleware.security import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=60,
            cleanup_interval=0,
        )

        # Add a stale entry (timestamp far in the past)
        middleware.requests["stale-ip"] = [time.time() - 120]
        middleware._last_cleanup = time.time() - 10

        middleware._cleanup_stale_entries(time.time())

        assert "stale-ip" not in middleware.requests

    @pytest.mark.unit
    def test_cleanup_enforces_max_tracked_ips(self) -> None:
        """_cleanup_stale_entries drops oldest IPs when over max_tracked_ips."""
        from foundry_unify.middleware.security import RateLimitMiddleware

        app = MagicMock()
        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=60,
            max_tracked_ips=2,
            cleanup_interval=0,
        )

        now = time.time()
        middleware.requests["ip-old"] = [now - 30]
        middleware.requests["ip-mid"] = [now - 20]
        middleware.requests["ip-new"] = [now - 10]
        middleware._last_cleanup = now - 10

        middleware._cleanup_stale_entries(now)

        assert len(middleware.requests) <= 2


class TestSSRFPreventionMiddleware:
    """Tests for SSRFPreventionMiddleware."""

    @pytest.fixture
    def middleware(self):
        from foundry_unify.middleware.security import SSRFPreventionMiddleware

        return SSRFPreventionMiddleware(app=MagicMock())

    @pytest.mark.unit
    def test_is_private_ip_loopback(self, middleware) -> None:
        """_is_private_ip returns True for loopback addresses."""
        assert middleware._is_private_ip("127.0.0.1") is True
        assert middleware._is_private_ip("::1") is True

    @pytest.mark.unit
    def test_is_private_ip_rfc1918(self, middleware) -> None:
        """_is_private_ip returns True for RFC 1918 addresses."""
        assert middleware._is_private_ip("10.0.0.1") is True
        assert middleware._is_private_ip("192.168.1.1") is True
        assert middleware._is_private_ip("172.16.0.1") is True

    @pytest.mark.unit
    def test_is_private_ip_public(self, middleware) -> None:
        """_is_private_ip returns False for public IP addresses."""
        assert middleware._is_private_ip("8.8.8.8") is False
        assert middleware._is_private_ip("1.1.1.1") is False

    @pytest.mark.unit
    def test_is_private_ip_invalid(self, middleware) -> None:
        """_is_private_ip returns False for invalid input."""
        assert middleware._is_private_ip("not-an-ip") is False
        assert middleware._is_private_ip("") is False

    @pytest.mark.unit
    def test_is_blocked_url_localhost(self, middleware) -> None:
        """_is_blocked_url returns True for localhost URLs."""
        assert middleware._is_blocked_url("http://localhost/api") is True
        assert middleware._is_blocked_url("http://127.0.0.1/api") is True

    @pytest.mark.unit
    def test_is_blocked_url_blocked_scheme(self, middleware) -> None:
        """_is_blocked_url returns True for blocked URL schemes."""
        assert middleware._is_blocked_url("file:///etc/passwd") is True
        assert middleware._is_blocked_url("gopher://evil.com") is True

    @pytest.mark.unit
    def test_is_blocked_url_cloud_metadata(self, middleware) -> None:
        """_is_blocked_url returns True for cloud metadata endpoints."""
        assert (
            middleware._is_blocked_url("http://169.254.169.254/latest/meta-data")
            is True
        )

    @pytest.mark.unit
    def test_is_blocked_url_public(self, middleware) -> None:
        """_is_blocked_url returns False for legitimate public URLs."""
        assert middleware._is_blocked_url("https://api.example.com/data") is False
        assert middleware._is_blocked_url("https://8.8.8.8/query") is False

    @pytest.mark.unit
    def test_is_blocked_url_decimal_ip(self, middleware) -> None:
        """_is_blocked_url detects obfuscated decimal IP notation."""
        # 2130706433 is decimal for 127.0.0.1
        assert middleware._is_blocked_url("http://2130706433/") is True

    @pytest.mark.unit
    def test_blocks_ssrf_in_query_params(self) -> None:
        """Middleware returns 400 when SSRF URL appears in query params."""
        from foundry_unify.middleware.security import SSRFPreventionMiddleware

        app = FastAPI()

        @app.get("/fetch")
        async def fetch(url: str) -> dict[str, str]:
            return {"url": url}

        app.add_middleware(SSRFPreventionMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/fetch", params={"url": "http://169.254.169.254/meta-data"}
        )
        assert response.status_code == 400
        assert "SSRF" in response.json()["message"]

    @pytest.mark.unit
    def test_allows_safe_query_params(self) -> None:
        """Middleware allows query params containing safe external URLs."""
        from foundry_unify.middleware.security import SSRFPreventionMiddleware

        app = FastAPI()

        @app.get("/fetch")
        async def fetch(url: str) -> dict[str, str]:
            return {"url": url}

        app.add_middleware(SSRFPreventionMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/fetch", params={"url": "https://api.example.com/data"})
        assert response.status_code == 200


class TestAddSecurityMiddleware:
    """Tests for add_security_middleware helper."""

    @pytest.mark.unit
    def test_adds_middleware_to_app(self) -> None:
        """add_security_middleware registers middleware without raising."""
        from foundry_unify.middleware.security import add_security_middleware

        app = FastAPI()
        add_security_middleware(app)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/nonexistent")
        assert response.status_code == 404

    @pytest.mark.unit
    def test_rate_limiting_can_be_disabled(self) -> None:
        """add_security_middleware respects enable_rate_limiting=False."""
        from foundry_unify.middleware.security import add_security_middleware

        app = FastAPI()

        @app.get("/")
        async def root() -> dict[str, str]:
            return {"ok": "true"}

        add_security_middleware(app, enable_rate_limiting=False)
        client = TestClient(app, raise_server_exceptions=False)

        for _ in range(10):
            response = client.get("/")
            assert response.status_code == 200

    @pytest.mark.unit
    def test_ssrf_prevention_can_be_disabled(self) -> None:
        """add_security_middleware respects enable_ssrf_prevention=False."""
        from foundry_unify.middleware.security import add_security_middleware

        app = FastAPI()

        @app.get("/fetch")
        async def fetch(url: str = "") -> dict[str, str]:
            return {"url": url}

        add_security_middleware(app, enable_ssrf_prevention=False)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/fetch", params={"url": "http://localhost/"})
        assert response.status_code == 200
