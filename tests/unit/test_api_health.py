"""Tests for health endpoints including docling-serve reachability check."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from foundry_unify.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.unit
def test_liveness_returns_200(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.unit
def test_readiness_includes_docling_serve_check_when_reachable(
    client: TestClient,
) -> None:
    with patch("foundry_unify.api.health.DoclingServeClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.health_check.return_value = True
        mock_cls.return_value = mock_instance

        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert "docling_serve" in data["checks"]
    assert data["checks"]["docling_serve"]["status"] is True


@pytest.mark.unit
def test_readiness_returns_503_when_docling_serve_unreachable(
    client: TestClient,
) -> None:
    with patch("foundry_unify.api.health.DoclingServeClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.health_check.return_value = False
        mock_cls.return_value = mock_instance

        response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["status"] == "unavailable"
    assert "docling_serve" in data["detail"]["checks"]
    assert data["detail"]["checks"]["docling_serve"]["status"] is False
