"""Tests for DOMAssembler."""

from typing import Any

import pytest

from foundry_unify.adapters.docling_serve_client import DoclingRawResponse
from foundry_unify.models.docling_dom import DoclingDOM
from foundry_unify.pipeline.dom_assembler import DOMAssembler


def _make_raw_response(
    pages: list[dict[str, Any]], **kwargs: Any
) -> DoclingRawResponse:
    return DoclingRawResponse(
        success=True,
        json_content={"schema_name": "DoclingDocument", "pages": pages},
        page_count=len(pages),
        ocr_applied=True,
        processing_time_ms=500.0,
        **kwargs,
    )


@pytest.mark.unit
def test_assemble_single_page_with_text_element() -> None:
    raw = _make_raw_response(
        [
            {
                "page_no": 1,
                "items": [{"label": "Text", "text": "Hello world", "confidence": 0.95}],
            }
        ]
    )
    dom = DOMAssembler.assemble(
        raw_response=raw,
        document_id="doc-1",
        trace_id="trace-1",
        source_track="document",
        processing_tier="standard",
    )
    assert isinstance(dom, DoclingDOM)
    assert dom.document_id == "doc-1"
    assert dom.source_track == "document"
    assert len(dom.pages) == 1
    assert dom.pages[0].page_number == 1
    assert len(dom.pages[0].elements) == 1
    assert dom.pages[0].elements[0].text == "Hello world"
    assert dom.pages[0].elements[0].element_type == "Text"


@pytest.mark.unit
def test_assemble_assigns_reading_order_from_item_position() -> None:
    raw = _make_raw_response(
        [
            {
                "page_no": 1,
                "items": [
                    {"label": "Text", "text": "First"},
                    {"label": "Text", "text": "Second"},
                    {"label": "Table", "text": "table data"},
                ],
            }
        ]
    )
    dom = DOMAssembler.assemble(
        raw_response=raw,
        document_id="d",
        trace_id="t",
        source_track="document",
        processing_tier="standard",
    )
    orders = [e.reading_order for e in dom.pages[0].elements]
    assert orders == [1, 2, 3]


@pytest.mark.unit
def test_assemble_multi_page_document() -> None:
    raw = _make_raw_response(
        [
            {"page_no": 1, "items": [{"label": "Text", "text": "Page 1"}]},
            {"page_no": 2, "items": [{"label": "Text", "text": "Page 2"}]},
        ]
    )
    dom = DOMAssembler.assemble(
        raw_response=raw,
        document_id="d",
        trace_id="t",
        source_track="document",
        processing_tier="standard",
    )
    assert len(dom.pages) == 2
    assert dom.pages[1].page_number == 2


@pytest.mark.unit
def test_assemble_halted_document_produces_empty_dom() -> None:
    raw = DoclingRawResponse(
        success=False,
        json_content={},
        page_count=0,
        ocr_applied=False,
        processing_time_ms=0.0,
    )
    dom = DOMAssembler.assemble(
        raw_response=raw,
        document_id="d",
        trace_id="t",
        source_track="document",
        processing_tier="standard",
        processing_status="halted",
    )
    assert dom.processing_status == "halted"
    assert dom.pages == []


@pytest.mark.unit
def test_assemble_sets_metadata_tier() -> None:
    raw = _make_raw_response([{"page_no": 1, "items": []}])
    dom = DOMAssembler.assemble(
        raw_response=raw,
        document_id="d",
        trace_id="t",
        source_track="document",
        processing_tier="vlm_assisted",
    )
    assert dom.metadata.processing_tier == "vlm_assisted"


@pytest.mark.unit
def test_assemble_element_id_is_unique_per_page() -> None:
    raw = _make_raw_response(
        [
            {
                "page_no": 1,
                "items": [
                    {"label": "Text", "text": "a"},
                    {"label": "Text", "text": "b"},
                ],
            },
        ]
    )
    dom = DOMAssembler.assemble(
        raw_response=raw,
        document_id="d",
        trace_id="t",
        source_track="document",
        processing_tier="standard",
    )
    ids = [e.element_id for e in dom.pages[0].elements]
    assert len(ids) == len(set(ids))
