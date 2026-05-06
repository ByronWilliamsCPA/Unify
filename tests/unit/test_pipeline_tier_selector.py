"""Tests for TierSelector."""

import pytest

from foundry_unify.models.document_metadata import (
    InboundDocumentMetadata,
)
from foundry_unify.pipeline.tier_selector import ProcessingTier, TierSelector


def _make_metadata(**kwargs: object) -> InboundDocumentMetadata:
    base = {
        "document_id": "doc-1",
        "trace_id": "trace-1",
        "source_track": "document",
        "num_pages": 1,
        "processing_version": {"version": "1.0"},
        "pages": [{"page_number": 1}],
    }
    base.update(kwargs)
    return InboundDocumentMetadata.model_validate(base)


@pytest.mark.unit
def test_selects_standard_tier() -> None:
    meta = _make_metadata(processing_recommendation={"tier": "standard"})
    tier = TierSelector.select(meta)
    assert tier == ProcessingTier.STANDARD


@pytest.mark.unit
def test_selects_vlm_assisted_tier() -> None:
    meta = _make_metadata(processing_recommendation={"tier": "vlm_assisted"})
    tier = TierSelector.select(meta)
    assert tier == ProcessingTier.VLM_ASSISTED


@pytest.mark.unit
def test_selects_vlm_validated_tier() -> None:
    meta = _make_metadata(processing_recommendation={"tier": "vlm_validated"})
    tier = TierSelector.select(meta)
    assert tier == ProcessingTier.VLM_VALIDATED


@pytest.mark.unit
def test_defaults_to_standard_when_no_recommendation() -> None:
    meta = _make_metadata()  # no processing_recommendation
    tier = TierSelector.select(meta)
    assert tier == ProcessingTier.STANDARD


@pytest.mark.unit
def test_halted_document_returns_halted_tier() -> None:
    meta = _make_metadata(processing_status="halted")
    tier = TierSelector.select(meta)
    assert tier == ProcessingTier.HALTED
