"""Tests for the inbound DocumentMetadata schema (B1-scoped subset)."""

import pytest

from foundry_unify.models.document_metadata import (
    DoclingRoutingParams,
    InboundDocumentMetadata,
)


@pytest.mark.unit
def test_docling_routing_params_to_form_data_defaults() -> None:
    params = DoclingRoutingParams()
    data = params.to_form_data()
    assert data["output_format"] == "json"
    assert "pipeline" not in data  # standard is the default, not sent explicitly


@pytest.mark.unit
def test_docling_routing_params_force_ocr() -> None:
    params = DoclingRoutingParams(ocr_force=True)
    data = params.to_form_data()
    assert data["force_ocr"] == "true"


@pytest.mark.unit
def test_docling_routing_params_no_ocr() -> None:
    params = DoclingRoutingParams(ocr_enabled=False)
    data = params.to_form_data()
    assert data["ocr"] == "false"


@pytest.mark.unit
def test_docling_routing_params_vlm_pipeline() -> None:
    params = DoclingRoutingParams(
        pipeline="vlm", vlm_model="ibm-granite/granite-docling-258M"
    )
    data = params.to_form_data()
    assert data["pipeline"] == "vlm"
    assert data["vlm_model"] == "ibm-granite/granite-docling-258M"


@pytest.mark.unit
def test_inbound_document_metadata_parses_minimal_json() -> None:
    raw = {
        "document_id": "doc-001",
        "trace_id": "trace-001",
        "source_track": "document",
        "num_pages": 3,
        "pdf_type": "born_digital",
        "processing_recommendation": {"tier": "standard"},
        "processing_version": {"version": "1.0.0"},
        "pages": [{"page_number": i} for i in range(1, 4)],
        "extra_unknown_field": "ignored",
    }
    meta = InboundDocumentMetadata.model_validate(raw)
    assert meta.document_id == "doc-001"
    assert meta.source_track == "document"
    assert meta.processing_recommendation is not None
    assert meta.processing_recommendation.tier == "standard"


@pytest.mark.unit
def test_inbound_document_metadata_halted_status() -> None:
    raw = {
        "document_id": "doc-enc",
        "trace_id": "trace-enc",
        "source_track": "document",
        "num_pages": 1,
        "processing_status": "halted",
        "processing_version": {"version": "1.0.0"},
        "pages": [{"page_number": 1}],
    }
    meta = InboundDocumentMetadata.model_validate(raw)
    assert meta.processing_status == "halted"


@pytest.mark.unit
def test_inbound_document_metadata_missing_docling_params_returns_none() -> None:
    raw = {
        "document_id": "doc-002",
        "trace_id": "trace-002",
        "source_track": "document",
        "num_pages": 1,
        "processing_version": {"version": "1.0.0"},
        "pages": [{"page_number": 1}],
    }
    meta = InboundDocumentMetadata.model_validate(raw)
    assert meta.docling_params is None
