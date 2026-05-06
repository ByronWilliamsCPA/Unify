"""Tests for LayoutPostprocessor — KI-002 Table->Text reclassification."""

from typing import Any

import pytest

from foundry_unify.pipeline.layout_postprocessor import LayoutPostprocessor


def _make_raw_pages(items_per_page: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        {"page_no": i + 1, "size": {"width": 612, "height": 792}, "items": items}
        for i, items in enumerate(items_per_page)
    ]


@pytest.mark.unit
def test_low_confidence_table_reclassified_to_text() -> None:
    pages = _make_raw_pages(
        [
            [
                {"label": "Table", "confidence": 0.3, "text": "col1 col2\nrow1 row2"},
            ]
        ]
    )
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Text"


@pytest.mark.unit
def test_high_confidence_table_preserved() -> None:
    pages = _make_raw_pages(
        [
            [
                {"label": "Table", "confidence": 0.8, "text": "col1 | col2"},
            ]
        ]
    )
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Table"


@pytest.mark.unit
def test_table_at_threshold_is_reclassified() -> None:
    """Confidence equal to the threshold is reclassified (< is strict; == triggers)."""
    pages = _make_raw_pages(
        [
            [
                {"label": "Table", "confidence": 0.5, "text": "..."},
            ]
        ]
    )
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Text"


@pytest.mark.unit
def test_original_pages_not_mutated() -> None:
    """apply() must not modify the caller's input list."""
    pages = _make_raw_pages(
        [
            [
                {"label": "Table", "confidence": 0.2, "text": "col1 col2"},
            ]
        ]
    )
    original_label = pages[0]["items"][0]["label"]
    LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert pages[0]["items"][0]["label"] == original_label


@pytest.mark.unit
def test_non_table_elements_not_affected() -> None:
    pages = _make_raw_pages(
        [
            [
                {"label": "Text", "confidence": 0.1, "text": "paragraph"},
                {"label": "Picture", "confidence": 0.2, "text": ""},
            ]
        ]
    )
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Text"
    assert result[0]["items"][1]["label"] == "Picture"


@pytest.mark.unit
def test_element_without_confidence_field_preserved_as_table() -> None:
    """Missing confidence field defaults to 1.0 — do not reclassify."""
    pages = _make_raw_pages(
        [
            [
                {"label": "Table", "text": "col1 col2"},
            ]
        ]
    )
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Table"


@pytest.mark.unit
def test_empty_pages_returns_empty_list() -> None:
    result = LayoutPostprocessor(confidence_threshold=0.5).apply([])
    assert result == []


@pytest.mark.unit
def test_reclassified_element_tagged_with_ki002_flag() -> None:
    pages = _make_raw_pages(
        [
            [
                {"label": "Table", "confidence": 0.2, "text": "text"},
            ]
        ]
    )
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0].get("ki002_reclassified") is True
