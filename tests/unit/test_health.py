"""Tests for health check endpoints.

Covers the three Kubernetes probe patterns (liveness, readiness, startup)
and the basic /health alias.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """Create a FastAPI app with health routes mounted."""
    from foundry_unify.api.health import router

    _app = FastAPI()
    _app.include_router(router)
    return _app


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    """Return a synchronous TestClient for the health app."""
    return TestClient(app)


class TestLivenessProbe:
    """Tests for GET /health/live."""

    @pytest.mark.unit
    def test_returns_200(self, client: TestClient) -> None:
        """Liveness probe returns HTTP 200."""
        response = client.get("/health/live")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_returns_ok_status(self, client: TestClient) -> None:
        """Liveness probe body has status 'ok'."""
        response = client.get("/health/live")
        assert response.json()["status"] == "ok"

    @pytest.mark.unit
    def test_returns_uptime(self, client: TestClient) -> None:
        """Liveness probe includes non-negative uptime_seconds."""
        response = client.get("/health/live")
        data = response.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    @pytest.mark.unit
    def test_returns_version(self, client: TestClient) -> None:
        """Liveness probe includes version field."""
        response = client.get("/health/live")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    @pytest.mark.unit
    def test_returns_python_version(self, client: TestClient) -> None:
        """Liveness probe includes python_version field."""
        response = client.get("/health/live")
        data = response.json()
        assert "python_version" in data
        assert "." in data["python_version"]


class TestReadinessProbe:
    """Tests for GET /health/ready."""

    @pytest.mark.unit
    def test_returns_200_when_no_checks(self, client: TestClient) -> None:
        """Readiness probe returns 200 when no dependency checks are configured."""
        response = client.get("/health/ready")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_returns_ok_status(self, client: TestClient) -> None:
        """Readiness probe body has status 'ok' when all checks pass."""
        response = client.get("/health/ready")
        assert response.json()["status"] == "ok"

    @pytest.mark.unit
    def test_returns_checks_dict(self, client: TestClient) -> None:
        """Readiness probe includes checks dictionary."""
        response = client.get("/health/ready")
        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    @pytest.mark.unit
    def test_returns_uptime(self, client: TestClient) -> None:
        """Readiness probe includes uptime_seconds."""
        response = client.get("/health/ready")
        data = response.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


class TestStartupProbe:
    """Tests for GET /health/startup."""

    @pytest.mark.unit
    def test_returns_200(self, client: TestClient) -> None:
        """Startup probe returns HTTP 200."""
        response = client.get("/health/startup")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_returns_started_status(self, client: TestClient) -> None:
        """Startup probe body has status 'started'."""
        response = client.get("/health/startup")
        assert response.json()["status"] == "started"

    @pytest.mark.unit
    def test_returns_uptime(self, client: TestClient) -> None:
        """Startup probe includes uptime_seconds."""
        response = client.get("/health/startup")
        data = response.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


class TestHealthAlias:
    """Tests for GET /health/ (alias for liveness)."""

    @pytest.mark.unit
    def test_returns_200(self, client: TestClient) -> None:
        """Health alias returns HTTP 200."""
        response = client.get("/health/")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_matches_liveness_response(self, client: TestClient) -> None:
        """Health alias returns the same status as the liveness probe."""
        alias = client.get("/health/")
        live = client.get("/health/live")
        assert alias.json()["status"] == live.json()["status"]


class TestReadinessCheckHelpers:
    """Tests for individual dependency check functions."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_cache_returns_readiness_check(self) -> None:
        """check_cache returns a ReadinessCheck with name 'cache'."""
        from foundry_unify.api.health import ReadinessCheck, check_cache

        result = await check_cache()

        assert isinstance(result, ReadinessCheck)
        assert result.name == "cache"
        assert result.status is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_service_returns_readiness_check(self) -> None:
        """check_external_service returns a ReadinessCheck with name 'external_api'."""
        from foundry_unify.api.health import ReadinessCheck, check_external_service

        result = await check_external_service()

        assert isinstance(result, ReadinessCheck)
        assert result.name == "external_api"
        assert result.status is True
