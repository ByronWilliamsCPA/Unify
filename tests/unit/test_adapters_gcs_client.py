"""Tests for GCSArtifactReader and GCSArtifactWriter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from foundry_unify.adapters.gcs_client import GCSArtifactReader, GCSArtifactWriter
from foundry_unify.core.exceptions import GCSError
from foundry_unify.models.docling_dom import DoclingDOM, DOMMetadata


def _make_metadata_json() -> str:
    return json.dumps(
        {
            "document_id": "doc-001",
            "trace_id": "trace-abc",
            "source_track": "document",
            "num_pages": 2,
            "pdf_type": "born_digital",
            "processing_recommendation": {"tier": "standard"},
        }
    )


@pytest.fixture
def mock_gcs_client() -> MagicMock:
    return MagicMock()


@pytest.mark.unit
def test_reader_downloads_document_metadata(mock_gcs_client: MagicMock) -> None:
    mock_blob = MagicMock()
    mock_blob.download_as_text.return_value = _make_metadata_json()
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    reader = GCSArtifactReader(
        client=mock_gcs_client, bucket_template="rag-pipeline-{env}"
    )
    meta = reader.download_document_metadata(env="dev", trace_id="trace-abc")

    assert meta.document_id == "doc-001"
    assert meta.source_track == "document"
    mock_gcs_client.bucket.assert_called_once_with("rag-pipeline-dev")


@pytest.mark.unit
def test_reader_constructs_correct_blob_path(mock_gcs_client: MagicMock) -> None:
    mock_blob = MagicMock()
    mock_blob.download_as_text.return_value = _make_metadata_json()
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    reader = GCSArtifactReader(
        client=mock_gcs_client, bucket_template="rag-pipeline-{env}"
    )
    reader.download_document_metadata(env="staging", trace_id="trace-xyz")

    mock_gcs_client.bucket.return_value.blob.assert_called_once_with(
        "trace-xyz/01-preprocessed/DocumentMetadata.json"
    )


@pytest.mark.unit
def test_reader_raises_gcs_error_on_download_failure(
    mock_gcs_client: MagicMock,
) -> None:
    mock_gcs_client.bucket.return_value.blob.return_value.download_as_text.side_effect = Exception(
        "access denied"
    )
    reader = GCSArtifactReader(
        client=mock_gcs_client, bucket_template="rag-pipeline-{env}"
    )

    with pytest.raises(GCSError) as exc_info:
        reader.download_document_metadata(env="dev", trace_id="trace-fail")

    assert "trace-fail" in exc_info.value.details.get("path", "")


@pytest.mark.unit
def test_writer_uploads_dom_to_correct_path(mock_gcs_client: MagicMock) -> None:
    mock_blob = MagicMock()
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    writer = GCSArtifactWriter(
        client=mock_gcs_client, bucket_template="rag-pipeline-{env}"
    )
    dom = DoclingDOM(
        document_id="doc-1",
        trace_id="trace-1",
        source_track="document",
        pages=[],
        metadata=DOMMetadata(processing_tier="standard", page_count=0),
    )
    result = writer.write_docling_dom(dom=dom, env="prod", trace_id="trace-1")

    mock_gcs_client.bucket.assert_called_once_with("rag-pipeline-prod")
    mock_gcs_client.bucket.return_value.blob.assert_called_once_with(
        "trace-1/03-docling-dom/DoclingDOM.json"
    )
    mock_blob.upload_from_string.assert_called_once()
    uploaded = (
        mock_blob.upload_from_string.call_args.kwargs.get("data")
        or mock_blob.upload_from_string.call_args.args[0]
    )
    data = json.loads(uploaded)
    assert data["document_id"] == "doc-1"
    assert result == "gs://rag-pipeline-prod/trace-1/03-docling-dom/DoclingDOM.json"
    assert (
        mock_blob.upload_from_string.call_args.kwargs.get("content_type")
        == "application/json"
    )


@pytest.mark.unit
def test_writer_raises_gcs_error_on_upload_failure(mock_gcs_client: MagicMock) -> None:
    mock_gcs_client.bucket.return_value.blob.return_value.upload_from_string.side_effect = Exception(
        "quota exceeded"
    )
    writer = GCSArtifactWriter(
        client=mock_gcs_client, bucket_template="rag-pipeline-{env}"
    )
    dom = DoclingDOM(
        document_id="d",
        trace_id="t",
        source_track="document",
        pages=[],
        metadata=DOMMetadata(processing_tier="standard", page_count=0),
    )
    with pytest.raises(GCSError):
        writer.write_docling_dom(dom=dom, env="dev", trace_id="t")


@pytest.mark.unit
def test_reader_raises_on_invalid_json(mock_gcs_client: MagicMock) -> None:
    """GCS returns corrupt JSON -- Pydantic ValidationError propagates (not wrapped in GCSError)."""
    mock_blob = MagicMock()
    mock_blob.download_as_text.return_value = "not-valid-json"
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    reader = GCSArtifactReader(
        client=mock_gcs_client, bucket_template="rag-pipeline-{env}"
    )
    with pytest.raises(ValidationError):
        reader.download_document_metadata(env="dev", trace_id="trace-corrupt")
