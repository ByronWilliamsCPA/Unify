"""Tests for security middleware.

Covers SecurityHeadersMiddleware, RateLimitMiddleware, SSRFPreventionMiddleware,
and the add_security_middleware factory function.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from foundry_unify.middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    SSRFPreventionMiddleware,
    add_security_middleware,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_app(middleware_cls: Any, **kwargs: Any) -> FastAPI:
    """Build a FastAPI app with a single middleware and a ping route."""
    app = FastAPI()
    app.add_middleware(middleware_cls, **kwargs)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    return app


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Return TestClient with SecurityHeadersMiddleware."""
        app = _simple_app(SecurityHeadersMiddleware)
        return TestClient(app)

    @pytest.mark.unit
    def test_x_content_type_options_nosniff(self, client: TestClient) -> None:
        """Verify X-Content-Type-Options header is set to nosniff."""
        response = client.get("/ping")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.unit
    def test_x_frame_options_deny(self, client: TestClient) -> None:
        """Verify X-Frame-Options header is set to DENY."""
        response = client.get("/ping")

        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.unit
    def test_x_xss_protection_set(self, client: TestClient) -> None:
        """Verify X-XSS-Protection header is present."""
        response = client.get("/ping")

        assert "X-XSS-Protection" in response.headers
        assert "1" in response.headers["X-XSS-Protection"]

    @pytest.mark.unit
    def test_content_security_policy_present(self, client: TestClient) -> None:
        """Verify Content-Security-Policy header is present."""
        response = client.get("/ping")

        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src" in csp

    @pytest.mark.unit
    def test_referrer_policy_set(self, client: TestClient) -> None:
        """Verify Referrer-Policy header is present."""
        response = client.get("/ping")

        assert "Referrer-Policy" in response.headers

    @pytest.mark.unit
    def test_permissions_policy_set(self, client: TestClient) -> None:
        """Verify Permissions-Policy header is present."""
        response = client.get("/ping")

        assert "Permissions-Policy" in response.headers

    @pytest.mark.unit
    def test_server_header_removed(self, client: TestClient) -> None:
        """Verify Server header is removed from response."""
        response = client.get("/ping")

        assert "server" not in response.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hsts_added_for_https_scheme(self) -> None:
        """Verify HSTS header is added when request uses HTTPS scheme."""
        from starlette.testclient import TestClient as StarletteClient

        app = _simple_app(SecurityHeadersMiddleware)
        https_client = StarletteClient(app, base_url="https://testserver")
        response = https_client.get("/ping")

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    @pytest.mark.unit
    def test_hsts_absent_for_http_scheme(self, client: TestClient) -> None:
        """Verify HSTS header is NOT added for plain HTTP requests."""
        response = client.get("/ping")

        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_removes_server_header_if_present(self) -> None:
        """Verify dispatch removes existing Server header."""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        mock_response = MagicMock(spec=Response)
        mock_response.headers = {"server": "uvicorn"}

        async def call_next(_req: Request) -> Response:
            return mock_response  # type: ignore[return-value]

        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.scheme = "http"

        result = await middleware.dispatch(mock_request, call_next)

        assert "server" not in result.headers


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def rate_limited_client(self) -> TestClient:
        """Return TestClient with a very low rate limit for easy testing."""
        app = _simple_app(
            RateLimitMiddleware,
            requests_per_minute=3,
            burst_size=2,
        )
        return TestClient(app)

    @pytest.mark.unit
    def test_request_below_limit_succeeds(
        self, rate_limited_client: TestClient
    ) -> None:
        """Verify requests below the rate limit return 200."""
        response = rate_limited_client.get("/ping")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_rate_limit_exceeded_returns_429(
        self, rate_limited_client: TestClient
    ) -> None:
        """Verify exceeding rate limit returns HTTP 429."""
        for _ in range(3):
            rate_limited_client.get("/ping")

        response = rate_limited_client.get("/ping")

        assert response.status_code == 429

    @pytest.mark.unit
    def test_rate_limit_response_body(self, rate_limited_client: TestClient) -> None:
        """Verify 429 response has expected body fields."""
        for _ in range(3):
            rate_limited_client.get("/ping")

        response = rate_limited_client.get("/ping")
        body = response.json()

        assert "error" in body
        assert "message" in body
        assert "retry_after" in body

    @pytest.mark.unit
    def test_rate_limit_retry_after_header(
        self, rate_limited_client: TestClient
    ) -> None:
        """Verify 429 response includes Retry-After header."""
        for _ in range(3):
            rate_limited_client.get("/ping")

        response = rate_limited_client.get("/ping")

        assert "Retry-After" in response.headers

    @pytest.mark.unit
    def test_burst_limit_exceeded_returns_429(self) -> None:
        """Verify exceeding burst limit (requests per second) returns 429."""
        app = _simple_app(
            RateLimitMiddleware,
            requests_per_minute=100,
            burst_size=1,
        )
        client = TestClient(app)

        r1 = client.get("/ping")
        assert r1.status_code == 200

        r2 = client.get("/ping")
        assert r2.status_code == 429
        body = r2.json()
        assert "Burst limit exceeded" in body["message"]

    @pytest.mark.unit
    def test_burst_limit_response_retry_after_is_1(self) -> None:
        """Verify burst limit 429 has Retry-After: 1."""
        app = _simple_app(
            RateLimitMiddleware,
            requests_per_minute=100,
            burst_size=1,
        )
        client = TestClient(app)
        client.get("/ping")
        response = client.get("/ping")

        assert response.headers.get("Retry-After") == "1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch_handles_none_client(self) -> None:
        """Verify dispatch handles request with None client gracefully."""
        middleware = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_minute=60,
            burst_size=10,
        )

        mock_request = MagicMock(spec=Request)
        mock_request.client = None

        mock_response = PlainTextResponse("ok")

        async def call_next(_req: Request) -> Response:
            return mock_response

        result = await middleware.dispatch(mock_request, call_next)

        assert result.status_code == 200


class TestRateLimitCleanup:
    """Tests for RateLimitMiddleware._cleanup_stale_entries."""

    @pytest.mark.unit
    def test_cleanup_skipped_before_interval(self) -> None:
        """Verify cleanup does not run before cleanup_interval elapses."""
        rl = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_minute=60,
            burst_size=10,
            cleanup_interval=3600,
        )
        rl.requests["1.2.3.4"] = [time.time()]
        original_last = rl._last_cleanup

        rl._cleanup_stale_entries(time.time())

        assert rl._last_cleanup == original_last

    @pytest.mark.unit
    def test_cleanup_removes_stale_ips(self) -> None:
        """Verify cleanup removes IPs with only old timestamps."""
        rl = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_minute=60,
            burst_size=10,
            cleanup_interval=0,
        )
        rl.requests["stale-ip"] = [time.time() - 120]
        rl._last_cleanup = 0

        rl._cleanup_stale_entries(time.time())

        assert "stale-ip" not in rl.requests

    @pytest.mark.unit
    def test_cleanup_keeps_recent_ips(self) -> None:
        """Verify cleanup retains IPs with recent timestamps."""
        rl = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_minute=60,
            burst_size=10,
            cleanup_interval=0,
        )
        rl.requests["recent-ip"] = [time.time() - 5]
        rl._last_cleanup = 0

        rl._cleanup_stale_entries(time.time())

        assert "recent-ip" in rl.requests

    @pytest.mark.unit
    def test_cleanup_trims_over_max_tracked(self) -> None:
        """Verify cleanup removes oldest IPs when max_tracked_ips is exceeded."""
        rl = RateLimitMiddleware(
            app=MagicMock(),
            requests_per_minute=60,
            burst_size=10,
            max_tracked_ips=2,
            cleanup_interval=0,
        )
        now = time.time()
        rl.requests["oldest"] = [now - 50]
        rl.requests["middle"] = [now - 30]
        rl.requests["newest"] = [now - 5]
        rl._last_cleanup = 0

        rl._cleanup_stale_entries(now)

        assert len(rl.requests) <= 2
        assert "oldest" not in rl.requests


# ---------------------------------------------------------------------------
# SSRFPreventionMiddleware
# ---------------------------------------------------------------------------


class TestSSRFPreventionMiddlewareIsPrivateIp:
    """Tests for SSRFPreventionMiddleware._is_private_ip static method."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",
            "10.0.0.1",
            "192.168.1.1",
            "172.16.0.1",
            "::1",
            "169.254.1.1",
        ],
    )
    def test_private_ips_return_true(self, ip: str) -> None:
        """Verify private/loopback IPs are detected as private."""
        assert SSRFPreventionMiddleware._is_private_ip(ip) is True

    @pytest.mark.unit
    def test_unspecified_address_returns_true(self) -> None:
        """Verify the unspecified address (all-zeros) is treated as private."""
        assert SSRFPreventionMiddleware._is_private_ip("0.0.0.0") is True  # noqa: S104

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "ip",
        [
            "8.8.8.8",
            "1.1.1.1",
            "93.184.216.34",
        ],
    )
    def test_public_ips_return_false(self, ip: str) -> None:
        """Verify public IPs are not flagged as private."""
        assert SSRFPreventionMiddleware._is_private_ip(ip) is False

    @pytest.mark.unit
    def test_invalid_ip_returns_false(self) -> None:
        """Verify invalid IP strings return False without raising."""
        result = SSRFPreventionMiddleware._is_private_ip("not-an-ip")

        assert result is False

    @pytest.mark.unit
    def test_ipv6_mapped_private_ipv4_returns_true(self) -> None:
        """Verify IPv4-mapped IPv6 address for private IP is blocked."""
        result = SSRFPreventionMiddleware._is_private_ip("::ffff:192.168.1.1")

        assert result is True


class TestSSRFPreventionMiddlewareExtractors:
    """Tests for URL extraction static methods."""

    @pytest.mark.unit
    def test_extract_host_from_valid_url(self) -> None:
        """Verify host extraction from a standard URL."""
        host = SSRFPreventionMiddleware._extract_host_from_url(
            "http://example.com/path"
        )

        assert host == "example.com"

    @pytest.mark.unit
    def test_extract_host_returns_none_for_empty(self) -> None:
        """Verify host extraction returns None for empty string."""
        host = SSRFPreventionMiddleware._extract_host_from_url("")

        assert host is None or isinstance(host, str)

    @pytest.mark.unit
    def test_extract_scheme_from_valid_url(self) -> None:
        """Verify scheme extraction from a standard URL."""
        scheme = SSRFPreventionMiddleware._extract_scheme_from_url("ftp://example.com")

        assert scheme == "ftp"

    @pytest.mark.unit
    def test_extract_scheme_returns_none_for_empty(self) -> None:
        """Verify scheme extraction returns None for empty string."""
        scheme = SSRFPreventionMiddleware._extract_scheme_from_url("")

        assert scheme is None


class TestSSRFPreventionMiddlewareIsBlockedUrl:
    """Tests for SSRFPreventionMiddleware._is_blocked_url method."""

    @pytest.fixture
    def middleware(self) -> SSRFPreventionMiddleware:
        """Return a bare SSRFPreventionMiddleware instance."""
        return SSRFPreventionMiddleware(app=MagicMock())

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://127.0.0.1:70/",
            "dict://localhost:11111/",
            "ftp://internal.example.com/file",
        ],
    )
    def test_blocked_schemes_are_rejected(
        self, middleware: SSRFPreventionMiddleware, url: str
    ) -> None:
        """Verify URLs with blocked schemes are flagged."""
        assert middleware._is_blocked_url(url) is True

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost/admin",
            "http://127.0.0.1/api",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://kubernetes.default/",
        ],
    )
    def test_blocked_hosts_are_rejected(
        self, middleware: SSRFPreventionMiddleware, url: str
    ) -> None:
        """Verify URLs pointing to blocked hostnames are flagged."""
        assert middleware._is_blocked_url(url) is True

    @pytest.mark.unit
    def test_private_ip_url_is_blocked(
        self, middleware: SSRFPreventionMiddleware
    ) -> None:
        """Verify URL pointing to a private IP range is blocked."""
        assert middleware._is_blocked_url("http://192.168.1.100/secret") is True

    @pytest.mark.unit
    def test_public_url_is_allowed(self, middleware: SSRFPreventionMiddleware) -> None:
        """Verify legitimate public URL is not blocked."""
        assert middleware._is_blocked_url("https://api.example.com/data") is False

    @pytest.mark.unit
    def test_decimal_ip_obfuscation_blocked(
        self, middleware: SSRFPreventionMiddleware
    ) -> None:
        """Verify decimal integer IP notation for loopback is blocked."""
        # 2130706433 == 127.0.0.1
        assert middleware._is_blocked_url("http://2130706433/") is True

    @pytest.mark.unit
    def test_url_without_host_not_blocked(
        self, middleware: SSRFPreventionMiddleware
    ) -> None:
        """Verify URL that cannot be parsed to a host is not blocked."""
        assert middleware._is_blocked_url("not-a-url") is False


class TestSSRFPreventionMiddlewareDispatch:
    """Tests for SSRFPreventionMiddleware dispatch via FastAPI TestClient."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Return TestClient with SSRFPreventionMiddleware."""
        app = _simple_app(SSRFPreventionMiddleware)
        return TestClient(app)

    @pytest.mark.unit
    def test_normal_request_passes_through(self, client: TestClient) -> None:
        """Verify a normal request without URL params is allowed."""
        response = client.get("/ping")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_ssrf_url_in_query_param_blocked(self, client: TestClient) -> None:
        """Verify request with SSRF URL in query param returns 400."""
        response = client.get("/ping", params={"url": "http://169.254.169.254/latest"})

        assert response.status_code == 400

    @pytest.mark.unit
    def test_ssrf_block_response_body(self, client: TestClient) -> None:
        """Verify SSRF block response contains expected fields."""
        response = client.get("/ping", params={"url": "http://localhost/admin"})
        body = response.json()

        assert "error" in body
        assert "message" in body
        assert "SSRF" in body["message"] or "blocked" in body["message"].lower()

    @pytest.mark.unit
    def test_legitimate_url_in_query_param_allowed(self, client: TestClient) -> None:
        """Verify request with legitimate URL in query param is allowed."""
        response = client.get(
            "/ping", params={"callback": "https://api.example.com/hook"}
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_non_url_query_param_allowed(self, client: TestClient) -> None:
        """Verify query params that are not URL-like are not blocked."""
        response = client.get("/ping", params={"q": "search terms"})

        assert response.status_code == 200

    @pytest.mark.unit
    def test_blocked_scheme_in_query_param(self, client: TestClient) -> None:
        """Verify request with file:// URL in query param is blocked."""
        response = client.get("/ping", params={"src": "file:///etc/passwd"})

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# add_security_middleware factory
# ---------------------------------------------------------------------------


class TestAddSecurityMiddleware:
    """Tests for the add_security_middleware factory function."""

    @pytest.mark.unit
    def test_basic_call_does_not_raise(self) -> None:
        """Verify add_security_middleware completes without error."""
        app = FastAPI()

        add_security_middleware(app)

    @pytest.mark.unit
    def test_rate_limiting_disabled(self) -> None:
        """Verify rate limiting can be disabled."""
        app = FastAPI()

        add_security_middleware(app, enable_rate_limiting=False)

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        client = TestClient(app)
        for _ in range(5):
            r = client.get("/ping")
            assert r.status_code == 200

    @pytest.mark.unit
    def test_ssrf_prevention_disabled(self) -> None:
        """Verify SSRF prevention can be disabled."""
        app = FastAPI()

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        add_security_middleware(app, enable_ssrf_prevention=False)
        client = TestClient(app)

        response = client.get("/ping", params={"url": "http://127.0.0.1/test"})
        assert response.status_code == 200

    @pytest.mark.unit
    def test_https_redirect_enabled(self) -> None:
        """Verify HTTPSRedirectMiddleware is added when enable_https_redirect=True."""
        app = FastAPI()

        add_security_middleware(app, enable_https_redirect=True)

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        client = TestClient(app, follow_redirects=False)
        response = client.get("/ping")
        assert response.status_code in (301, 307)

    @pytest.mark.unit
    def test_allowed_hosts_configured(self) -> None:
        """Verify TrustedHostMiddleware blocks unknown hosts when allowed_hosts is set."""
        app = FastAPI()

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        add_security_middleware(app, allowed_hosts=["trusted.example.com"])

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/ping")
        assert response.status_code == 400

    @pytest.mark.unit
    def test_allowed_origins_passed_to_cors(self) -> None:
        """Verify CORS middleware is configured with provided allowed_origins."""
        app = FastAPI()

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        add_security_middleware(
            app,
            allowed_origins=["https://example.com"],
            enable_rate_limiting=False,
            enable_ssrf_prevention=False,
        )

        client = TestClient(app)
        response = client.options(
            "/ping",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)

    @pytest.mark.unit
    def test_custom_rate_limit_rpm(self) -> None:
        """Verify custom rate_limit_rpm is applied."""
        app = FastAPI()

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        add_security_middleware(
            app,
            enable_ssrf_prevention=False,
            rate_limit_rpm=2,
        )

        client = TestClient(app)
        assert client.get("/ping").status_code == 200
        assert client.get("/ping").status_code == 200
        assert client.get("/ping").status_code == 429

    @pytest.mark.unit
    def test_security_headers_present_after_factory(self) -> None:
        """Verify security headers are present on responses after factory call."""
        app = FastAPI()

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "ok"}

        add_security_middleware(
            app,
            enable_rate_limiting=False,
            enable_ssrf_prevention=False,
        )

        client = TestClient(app)
        response = client.get("/ping")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers


# ---------------------------------------------------------------------------
# Exception path coverage for _extract_host_from_url and _extract_scheme_from_url
# ---------------------------------------------------------------------------


class TestSSRFExceptionPaths:
    """Tests for exception handler branches in extractor static methods."""

    @pytest.mark.unit
    def test_extract_host_returns_none_on_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify _extract_host_from_url returns None when urlparse raises."""
        import urllib.parse as urlparse_module

        def raising_urlparse(_url: str) -> None:
            raise ValueError("boom")

        monkeypatch.setattr(urlparse_module, "urlparse", raising_urlparse)

        result = SSRFPreventionMiddleware._extract_host_from_url("http://example.com")

        assert result is None

    @pytest.mark.unit
    def test_extract_scheme_returns_none_on_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify _extract_scheme_from_url returns None when urlparse raises."""
        import urllib.parse as urlparse_module

        def raising_urlparse(_url: str) -> None:
            raise ValueError("boom")

        monkeypatch.setattr(urlparse_module, "urlparse", raising_urlparse)

        result = SSRFPreventionMiddleware._extract_scheme_from_url("http://example.com")

        assert result is None

    @pytest.mark.unit
    def test_decimal_ip_above_max_ipv4_not_blocked(self) -> None:
        """Verify a decimal host that exceeds 0xFFFFFFFF is not treated as an IP."""
        middleware = SSRFPreventionMiddleware(app=MagicMock())
        # 4294967296 == 2^32, exceeds 0xFFFFFFFF so the decimal-IP branch is skipped
        result = middleware._is_blocked_url("http://4294967296/path")

        assert result is False

    @pytest.mark.unit
    def test_decimal_ip_public_range_not_blocked(self) -> None:
        """Verify decimal notation for a public IP is allowed."""
        middleware = SSRFPreventionMiddleware(app=MagicMock())
        # 134744072 == 8.8.8.8 (public Google DNS)
        result = middleware._is_blocked_url("http://134744072/path")

        assert result is False

    @pytest.mark.unit
    def test_is_blocked_url_handles_ipaddress_valueerror(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify _is_blocked_url catches ValueError from ipaddress.ip_address."""
        import ipaddress as ipaddress_module

        original_ip_address = ipaddress_module.ip_address

        def raising_ip_address(val: Any) -> Any:
            if isinstance(val, int):
                raise ValueError("forced error")
            return original_ip_address(val)

        monkeypatch.setattr(ipaddress_module, "ip_address", raising_ip_address)

        middleware = SSRFPreventionMiddleware(app=MagicMock())
        # 1249739203 is a decimal-notation host within valid IPv4 int range
        result = middleware._is_blocked_url("http://1249739203/path")

        assert result is False
