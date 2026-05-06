"""Tests for DoclingServeClient."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from foundry_unify.adapters.docling_serve_client import (
    DoclingServeClient,
)
from foundry_unify.core.exceptions import DoclingServiceError
from foundry_unify.models.document_metadata import DoclingRoutingParams


@pytest.fixture
def client() -> DoclingServeClient:
    return DoclingServeClient(base_url="http://test-docling:5001", timeout=10.0)


@pytest.mark.unit
def test_health_check_returns_true_on_200(client: DoclingServeClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response
        mock_get.return_value = mock_http
        assert client.health_check() is True


@pytest.mark.unit
def test_health_check_returns_false_on_connect_error(
    client: DoclingServeClient,
) -> None:
    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.get.side_effect = httpx.ConnectError("refused")
        mock_get.return_value = mock_http
        assert client.health_check() is False


@pytest.mark.unit
def test_convert_file_sends_correct_form_data(
    client: DoclingServeClient, tmp_path: Path
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    params = DoclingRoutingParams(ocr_force=True)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "documents": [
            {
                "status": "success",
                "json_content": {"schema_name": "DoclingDocument", "pages": []},
                "metadata": {
                    "page_count": 1,
                    "ocr_applied": True,
                    "processing_time_ms": 500,
                },
            }
        ]
    }

    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_get.return_value = mock_http

        result = client.convert_file(pdf, routing_params=params)

        call_kwargs = mock_http.post.call_args
        assert call_kwargs.kwargs["data"]["force_ocr"] == "true"
        assert result.success is True
        assert result.page_count == 1


@pytest.mark.unit
def test_convert_file_raises_on_http_error(
    client: DoclingServeClient, tmp_path: Path
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF test")

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_get.return_value = mock_http

        with pytest.raises(DoclingServiceError) as exc_info:
            client.convert_file(pdf)

    assert exc_info.value.details.get("status_code") == 503


@pytest.mark.unit
def test_convert_file_raises_on_connect_error(
    client: DoclingServeClient, tmp_path: Path
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF test")

    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("refused")
        mock_get.return_value = mock_http

        with pytest.raises(DoclingServiceError):
            client.convert_file(pdf)


@pytest.mark.unit
def test_convert_file_raises_on_missing_file(client: DoclingServeClient) -> None:
    with pytest.raises(FileNotFoundError):
        client.convert_file(Path("/nonexistent/doc.pdf"))
