"""Tests for POST /process endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from foundry_unify.main import app
from foundry_unify.models.docling_dom import DoclingDOM, DOMMetadata, PageDOM


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_dom() -> DoclingDOM:
    return DoclingDOM(
        document_id="doc-1",
        trace_id="trace-abc",
        source_track="document",
        pages=[PageDOM(page_number=1, elements=[])],
        metadata=DOMMetadata(processing_tier="standard", page_count=1),
    )


@pytest.mark.unit
def test_process_returns_200_for_document_track(client: TestClient) -> None:
    with (
        patch("foundry_unify.api.process.GCSArtifactReader") as mock_reader_cls,
        patch("foundry_unify.api.process.DoclingServeClient") as mock_docling_cls,
        patch("foundry_unify.api.process.GCSArtifactWriter") as mock_writer_cls,
    ):
        mock_meta = MagicMock()
        mock_meta.source_track = "document"
        mock_meta.document_id = "doc-1"
        mock_meta.processing_status = "complete"
        mock_meta.docling_params = None
        mock_meta.processing_recommendation = MagicMock(tier="standard")

        mock_reader_cls.return_value.download_document_metadata.return_value = mock_meta

        mock_raw = MagicMock()
        mock_raw.success = True
        mock_raw.json_content = {"pages": [{"page_no": 1, "items": []}]}
        mock_raw.page_count = 1
        mock_raw.ocr_applied = True
        mock_raw.processing_time_ms = 500.0
        mock_raw.error = None
        mock_docling_cls.return_value.convert_file.return_value = mock_raw

        mock_writer_cls.return_value.write_docling_dom.return_value = (
            "gs://rag-pipeline-dev/trace-abc/03-docling-dom/DoclingDOM.json"
        )

        response = client.post(
            "/process",
            json={"trace_id": "trace-abc", "env": "dev", "source_track": "document"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-abc"
    assert "gcs_path" in data


@pytest.mark.unit
def test_process_returns_422_for_missing_source_track(client: TestClient) -> None:
    response = client.post(
        "/process",
        json={"trace_id": "trace-abc", "env": "dev"},
    )
    assert response.status_code == 422


@pytest.mark.unit
def test_process_returns_422_for_audio_track_in_b1(client: TestClient) -> None:
    """Audio track is not supported in B1 -- returns 422 with NOT_IMPLEMENTED_YET."""
    with patch("foundry_unify.api.process.GCSArtifactReader") as mock_reader_cls:
        mock_meta = MagicMock()
        mock_meta.source_track = "audio"
        mock_reader_cls.return_value.download_document_metadata.return_value = mock_meta

        response = client.post(
            "/process",
            json={"trace_id": "trace-audio", "env": "dev", "source_track": "audio"},
        )

    assert response.status_code == 422
    assert "audio" in response.json()["detail"].lower()


@pytest.mark.unit
def test_process_returns_200_for_halted_document(client: TestClient) -> None:
    with (
        patch("foundry_unify.api.process.GCSArtifactReader") as mock_reader_cls,
        patch("foundry_unify.api.process.GCSArtifactWriter") as mock_writer_cls,
    ):
        mock_meta = MagicMock()
        mock_meta.source_track = "document"
        mock_meta.document_id = "doc-enc"
        mock_meta.processing_status = "halted"
        mock_meta.docling_params = None
        mock_meta.processing_recommendation = None
        mock_reader_cls.return_value.download_document_metadata.return_value = mock_meta
        mock_writer_cls.return_value.write_docling_dom.return_value = "gs://..."

        response = client.post(
            "/process",
            json={"trace_id": "trace-enc", "env": "dev", "source_track": "document"},
        )

    assert response.status_code == 200
    assert response.json()["processing_status"] == "halted"
