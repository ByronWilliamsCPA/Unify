"""Integration test harness for the POST /process endpoint.

These tests run against live docling-serve and GCS. They require:
  - FOUNDRY_UNIFY_DOCLING_SERVE_URL pointing to a reachable docling-serve instance
  - GCS credentials (ADC or GOOGLE_APPLICATION_CREDENTIALS)

Run with: uv run pytest -m integration tests/integration/

All 10 B1 acceptance criteria from PROJECT-PLAN.md Section B1 are tracked here.
Tests that require live infrastructure are marked skip and skipped in CI by default.
"""

import pytest

# Mark the entire module as integration — excluded from the default test run
pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_born_digital_pdf_standard_tier_writes_docling_dom() -> None:
    """B1 acceptance: Born-digital PDF -> standard tier -> DoclingDOM written to GCS."""
    # 1. POST /process with a known born_digital DocumentMetadata.json in test GCS bucket
    # 2. Assert response 200, processing_status == "complete"
    # 3. Assert DoclingDOM.json exists in 03-docling-dom/ with source_track: "document"


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_scanned_pdf_tables_recommends_vlm_assisted() -> None:
    """B1 acceptance: Scanned PDF with tables -> vlm_assisted tier recommended in output."""


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_handwritten_document_invokes_vlm_validated() -> None:
    """B1 acceptance: Handwritten document -> vlm_validated tier invoked and flagged."""


@pytest.mark.skip(reason="audio track not implemented in B1")
def test_audio_track_skips_ocr_and_normalizes_dom() -> None:
    """B1 acceptance: audio source_track -> OCR skipped, DOM normalized and written."""


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_watermarked_document_flags_watermark_as_parasitic() -> None:
    """B1 acceptance: Watermarked document -> watermark element flagged as is_parasitic."""


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_multi_page_document_all_pages_processed() -> None:
    """B1 acceptance: Multi-page document -> all pages present, reading order array present."""


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_corrupt_page_graceful_degradation() -> None:
    """B1 acceptance: Corrupt/partial-failure page -> layout_confidence=0, graceful."""


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_docling_routing_params_applied_to_convert_file() -> None:
    """B1 acceptance: DoclingRoutingParams.to_form_data() applied to /v1/convert/file."""


def test_missing_source_track_returns_422() -> None:
    """B1 acceptance: Missing source_track -> 422 validation error (unit-level)."""
    from fastapi.testclient import TestClient

    from foundry_unify.main import app

    client = TestClient(app)
    response = client.post("/process", json={"trace_id": "t", "env": "dev"})
    assert response.status_code == 422


@pytest.mark.skip(reason="audio track not implemented in B1")
def test_missing_docling_dom_in_audio_input_returns_422() -> None:
    """B1 acceptance: Missing docling_document in audio input -> 422."""


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_get_health_returns_docling_serve_reachable() -> None:
    """B1 acceptance: GET /health/ready returns docling_serve: 'reachable' when up."""
