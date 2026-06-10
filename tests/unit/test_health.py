"""Tests for health check endpoints.

Covers liveness, readiness, startup, and base health endpoints,
plus the ReadinessCheck helper functions and response models.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import foundry_unify.api.health as health_module
from foundry_unify.api.health import (
    ReadinessCheck,
    ReadinessStatus,
    check_cache,
    check_external_service,
    router,
)

# ---------------------------------------------------------------------------
# Shared app fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app() -> FastAPI:
    """Return a minimal FastAPI app with the health router mounted."""
    _app = FastAPI()
    _app.include_router(router)
    return _app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a synchronous TestClient for the health app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health/live
# ---------------------------------------------------------------------------


class TestLivenessEndpoint:
    """Tests for the /health/live liveness probe endpoint."""

    @pytest.mark.unit
    def test_liveness_returns_200(self, client: TestClient) -> None:
        """Verify liveness probe returns HTTP 200."""
        response = client.get("/health/live")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_liveness_status_ok(self, client: TestClient) -> None:
        """Verify liveness response body contains status ok."""
        response = client.get("/health/live")
        body = response.json()

        assert body["status"] == "ok"

    @pytest.mark.unit
    def test_liveness_uptime_positive(self, client: TestClient) -> None:
        """Verify uptime_seconds is a positive number."""
        response = client.get("/health/live")
        body = response.json()

        assert body["uptime_seconds"] >= 0

    @pytest.mark.unit
    def test_liveness_response_has_version(self, client: TestClient) -> None:
        """Verify liveness response includes version field."""
        response = client.get("/health/live")
        body = response.json()

        assert "version" in body
        assert isinstance(body["version"], str)
        assert len(body["version"]) > 0

    @pytest.mark.unit
    def test_liveness_response_has_python_version(self, client: TestClient) -> None:
        """Verify liveness response includes python_version field."""
        response = client.get("/health/live")
        body = response.json()

        assert "python_version" in body
        assert isinstance(body["python_version"], str)

    @pytest.mark.unit
    def test_liveness_response_has_timestamp(self, client: TestClient) -> None:
        """Verify liveness response includes a numeric timestamp."""
        response = client.get("/health/live")
        body = response.json()

        assert "timestamp" in body
        assert isinstance(body["timestamp"], float)


# ---------------------------------------------------------------------------
# GET /health/ready
# ---------------------------------------------------------------------------


class TestReadinessEndpoint:
    """Tests for the /health/ready readiness probe endpoint."""

    @pytest.mark.unit
    def test_readiness_returns_200_when_no_checks(self, client: TestClient) -> None:
        """Verify readiness returns 200 when no dependency checks are configured."""
        response = client.get("/health/ready")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_readiness_status_ok(self, client: TestClient) -> None:
        """Verify readiness response body contains status ok."""
        response = client.get("/health/ready")
        body = response.json()

        assert body["status"] == "ok"

    @pytest.mark.unit
    def test_readiness_checks_empty_by_default(self, client: TestClient) -> None:
        """Verify checks dict is empty when no dependencies are wired up."""
        response = client.get("/health/ready")
        body = response.json()

        assert body["checks"] == {}

    @pytest.mark.unit
    def test_readiness_uptime_positive(self, client: TestClient) -> None:
        """Verify uptime_seconds is a non-negative number."""
        response = client.get("/health/ready")
        body = response.json()

        assert body["uptime_seconds"] >= 0

    @pytest.mark.unit
    def test_readiness_returns_503_when_check_fails(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify a failing registered check drives /health/ready to HTTP 503."""

        async def failing_check() -> ReadinessCheck:
            return ReadinessCheck(name="cache", status=False, error="down")

        # Replace the whole registry so pre-existing entries cannot leak in
        monkeypatch.setattr(health_module, "READINESS_CHECKS", {"cache": failing_check})

        response = client.get("/health/ready")
        body = response.json()

        assert response.status_code == 503
        assert body["detail"]["status"] == "unavailable"
        assert body["detail"]["checks"]["cache"]["error"] == "down"

    @pytest.mark.unit
    def test_readiness_returns_200_with_passing_check(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify a passing registered check is reported in the 200 response."""

        async def passing_check() -> ReadinessCheck:
            return ReadinessCheck(name="cache", status=True, latency_ms=1.0)

        monkeypatch.setattr(health_module, "READINESS_CHECKS", {"cache": passing_check})

        response = client.get("/health/ready")
        body = response.json()

        assert response.status_code == 200
        assert body["status"] == "ok"
        assert body["checks"]["cache"]["status"] is True

    @pytest.mark.unit
    def test_readiness_returns_503_when_check_raises(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify a raising probe degrades to a failed check, not an HTTP 500."""

        async def raising_check() -> ReadinessCheck:
            msg = "probe exploded"
            raise RuntimeError(msg)

        monkeypatch.setattr(health_module, "READINESS_CHECKS", {"cache": raising_check})

        response = client.get("/health/ready")
        body = response.json()

        assert response.status_code == 503
        assert body["detail"]["checks"]["cache"]["status"] is False
        assert body["detail"]["checks"]["cache"]["error"] == "probe exploded"


# ---------------------------------------------------------------------------
# GET /health/startup
# ---------------------------------------------------------------------------


class TestStartupEndpoint:
    """Tests for the /health/startup startup probe endpoint."""

    @pytest.mark.unit
    def test_startup_returns_200(self, client: TestClient) -> None:
        """Verify startup probe returns HTTP 200."""
        response = client.get("/health/startup")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_startup_status_started(self, client: TestClient) -> None:
        """Verify startup response body contains status started."""
        response = client.get("/health/startup")
        body = response.json()

        assert body["status"] == "started"

    @pytest.mark.unit
    def test_startup_uptime_non_negative(self, client: TestClient) -> None:
        """Verify uptime_seconds is non-negative."""
        response = client.get("/health/startup")
        body = response.json()

        assert body["uptime_seconds"] >= 0


# ---------------------------------------------------------------------------
# GET /health/ (base alias)
# ---------------------------------------------------------------------------


class TestBaseHealthEndpoint:
    """Tests for the /health/ base health alias endpoint."""

    @pytest.mark.unit
    def test_base_health_returns_200(self, client: TestClient) -> None:
        """Verify /health/ returns HTTP 200."""
        response = client.get("/health/")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_base_health_delegates_to_liveness(self, client: TestClient) -> None:
        """Verify /health/ returns same status as liveness endpoint."""
        base_response = client.get("/health/")
        live_response = client.get("/health/live")

        assert base_response.json()["status"] == live_response.json()["status"]


# ---------------------------------------------------------------------------
# check_cache helper function
# ---------------------------------------------------------------------------


class TestCheckCache:
    """Tests for the check_cache async helper function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_returns_readiness_check(self) -> None:
        """Verify check_cache returns a ReadinessCheck instance."""
        result = await check_cache()

        assert isinstance(result, ReadinessCheck)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_name_is_cache(self) -> None:
        """Verify check_cache result has name 'cache'."""
        result = await check_cache()

        assert result.name == "cache"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_status_true(self) -> None:
        """Verify check_cache placeholder reports status True."""
        result = await check_cache()

        assert result.status is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_latency_non_negative(self) -> None:
        """Verify check_cache includes a non-negative latency_ms."""
        result = await check_cache()

        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_no_error_on_success(self) -> None:
        """Verify check_cache error field is None on success."""
        result = await check_cache()

        assert result.error is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_returns_error_on_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify check_cache captures exception message in error field."""
        import foundry_unify.api.health as health_module

        real_time = health_module.time.time
        call_count = 0

        def patched_time() -> float:
            nonlocal call_count
            call_count += 1
            # Call 1: start = time.time() in check_cache - succeeds
            # Call 2: latency calculation inside try block - raises
            # Call 3: latency calculation inside except block - succeeds
            if call_count == 2:
                raise RuntimeError("cache unavailable")
            return real_time()

        monkeypatch.setattr(health_module.time, "time", patched_time)

        result = await check_cache()

        assert result.status is False
        assert result.error == "cache unavailable"


# ---------------------------------------------------------------------------
# check_external_service helper function
# ---------------------------------------------------------------------------


class TestCheckExternalService:
    """Tests for the check_external_service async helper function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_service_returns_readiness_check(self) -> None:
        """Verify check_external_service returns a ReadinessCheck instance."""
        result = await check_external_service()

        assert isinstance(result, ReadinessCheck)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_service_name(self) -> None:
        """Verify check_external_service result has name 'external_api'."""
        result = await check_external_service()

        assert result.name == "external_api"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_service_status_true(self) -> None:
        """Verify check_external_service placeholder reports status True."""
        result = await check_external_service()

        assert result.status is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_service_latency_non_negative(self) -> None:
        """Verify check_external_service includes a non-negative latency_ms."""
        result = await check_external_service()

        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_service_error_on_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify check_external_service captures exception in error field."""
        import foundry_unify.api.health as health_module

        real_time = health_module.time.time
        call_count = 0

        def patched_time() -> float:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ConnectionError("service unreachable")
            return real_time()

        monkeypatch.setattr(health_module.time, "time", patched_time)

        result = await check_external_service()

        assert result.status is False
        assert result.error == "service unreachable"


# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------


class TestReadinessCheckModel:
    """Tests for the ReadinessCheck pydantic model."""

    @pytest.mark.unit
    def test_readiness_check_minimal(self) -> None:
        """Verify ReadinessCheck can be constructed with minimal fields."""
        check = ReadinessCheck(name="db", status=True)

        assert check.name == "db"
        assert check.status is True
        assert check.latency_ms is None
        assert check.error is None

    @pytest.mark.unit
    def test_readiness_check_with_all_fields(self) -> None:
        """Verify ReadinessCheck accepts all optional fields."""
        check = ReadinessCheck(
            name="redis",
            status=False,
            latency_ms=12.5,
            error="connection refused",
        )

        assert check.name == "redis"
        assert check.status is False
        assert check.latency_ms == 12.5
        assert check.error == "connection refused"

    @pytest.mark.unit
    def test_readiness_status_inherits_health_fields(self) -> None:
        """Verify ReadinessStatus includes checks dict alongside HealthStatus fields."""
        readiness_status = ReadinessStatus(
            status="ok",
            uptime_seconds=10.0,
            checks={"cache": ReadinessCheck(name="cache", status=True)},
        )

        assert readiness_status.status == "ok"
        assert "cache" in readiness_status.checks
        assert readiness_status.checks["cache"].status is True


# ---------------------------------------------------------------------------
# API __init__ import
# ---------------------------------------------------------------------------


class TestApiInit:
    """Tests for the api package __init__ exports."""

    @pytest.mark.unit
    def test_health_router_exported(self) -> None:
        """Verify health_router is importable from the api package."""
        from foundry_unify.api import health_router

        assert health_router is not None

    @pytest.mark.unit
    def test_health_router_prefix(self) -> None:
        """Verify health_router is configured with /health prefix."""
        from foundry_unify.api import health_router

        assert health_router.prefix == "/health"
