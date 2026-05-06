"""Tests for the DoclingDOM output schema."""

import pytest

from foundry_unify.models.docling_dom import (
    BBox,
    DoclingDOM,
    DOMMetadata,
    ElementDOM,
    PageDOM,
)


@pytest.mark.unit
def test_bbox_validates_coordinates() -> None:
    bbox = BBox(x1=0.0, y1=0.0, x2=100.0, y2=50.0)
    assert bbox.x2 > bbox.x1


@pytest.mark.unit
def test_element_dom_defaults() -> None:
    element = ElementDOM(
        element_id="p1-e1",
        element_type="Text",
        text="Hello world",
        reading_order=1,
    )
    assert element.is_parasitic is False
    assert element.confidence == 1.0
    assert element.ocr_engine_provenance == "docling-standard"


@pytest.mark.unit
def test_page_dom_has_reading_order_confidence() -> None:
    page = PageDOM(page_number=1, elements=[])
    assert page.reading_order_confidence == 1.0


@pytest.mark.unit
def test_docling_dom_serializes_to_json() -> None:
    dom = DoclingDOM(
        document_id="doc-123",
        trace_id="trace-abc",
        source_track="document",
        pages=[
            PageDOM(
                page_number=1,
                elements=[
                    ElementDOM(
                        element_id="p1-e1",
                        element_type="Text",
                        text="Hello",
                        reading_order=1,
                    )
                ],
            )
        ],
        metadata=DOMMetadata(processing_tier="standard", page_count=1),
    )
    data = dom.model_dump()
    assert data["document_id"] == "doc-123"
    assert data["pages"][0]["elements"][0]["text"] == "Hello"
    assert data["metadata"]["processing_tier"] == "standard"


@pytest.mark.unit
def test_docling_dom_halted_status() -> None:
    dom = DoclingDOM(
        document_id="doc-halted",
        trace_id="trace-xyz",
        source_track="document",
        processing_status="halted",
        pages=[],
        metadata=DOMMetadata(processing_tier="standard", page_count=0),
    )
    assert dom.processing_status == "halted"
    assert dom.pages == []
