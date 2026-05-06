"""DOMAssembler -- converts a DoclingRawResponse into the canonical DoclingDOM schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from foundry_unify.models.docling_dom import (
    DoclingDOM,
    DOMMetadata,
    ElementDOM,
    PageDOM,
)

if TYPE_CHECKING:
    from foundry_unify.adapters.docling_serve_client import DoclingRawResponse


class DOMAssembler:
    """Converts a raw Docling API response into the foundry-unify DoclingDOM schema.

    Maps Docling's internal JSON structure (pages[].items[]) to the
    DoclingDOM format expected by foundry-chunk.
    """

    @staticmethod
    def assemble(
        raw_response: DoclingRawResponse,
        document_id: str,
        trace_id: str,
        source_track: Literal["document", "audio"],
        processing_tier: Literal["standard", "vlm_assisted", "vlm_validated"],
        processing_status: Literal["complete", "halted"] = "complete",
    ) -> DoclingDOM:
        """Build a DoclingDOM from a DoclingRawResponse.

        Args:
            raw_response: Parsed response from DoclingServeClient.convert_file().
            document_id: Stable document identifier from upstream metadata.
            trace_id: Pipeline trace ID from the Cloud Workflows request.
            source_track: "document" or "audio" -- carried through to the output.
            processing_tier: Which Docling pipeline tier was used.
            processing_status: "complete" or "halted" (halted skips OCR, empty pages).

        Returns:
            Fully assembled DoclingDOM ready for GCS serialization.
        """
        if processing_status == "halted" or not raw_response.success:
            return DoclingDOM(
                document_id=document_id,
                trace_id=trace_id,
                source_track=source_track,
                processing_status="halted",
                pages=[],
                metadata=DOMMetadata(
                    processing_tier=processing_tier,
                    layout_confidence=0.0,
                    ocr_applied=False,
                    page_count=0,
                ),
            )

        raw_pages: list[dict[str, Any]] = raw_response.json_content.get("pages", [])  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
        pages = [DOMAssembler._assemble_page(page_data) for page_data in raw_pages]

        return DoclingDOM(
            document_id=document_id,
            trace_id=trace_id,
            source_track=source_track,
            processing_status="complete",
            pages=pages,
            metadata=DOMMetadata(
                processing_tier=processing_tier,
                layout_confidence=1.0,  # early-return above guarantees success=True here
                ocr_applied=raw_response.ocr_applied,
                page_count=len(pages),
            ),
        )

    @staticmethod
    def _assemble_page(page_data: dict[str, Any]) -> PageDOM:  # pyright: ignore[reportExplicitAny]
        page_no: int = page_data.get("page_no", 1)  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
        items: list[dict[str, Any]] = page_data.get("items", [])  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
        elements = [
            DOMAssembler._assemble_element(item, page_no, order)
            for order, item in enumerate(items, start=1)
        ]
        return PageDOM(
            page_number=page_no,
            reading_order_confidence=1.0,
            elements=elements,
        )

    @staticmethod
    def _assemble_element(
        item: dict[str, Any],  # pyright: ignore[reportExplicitAny]
        page_no: int,
        reading_order: int,
    ) -> ElementDOM:
        return ElementDOM(
            element_id=f"p{page_no}-e{reading_order}",
            element_type=item.get("label", "Text"),  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
            text=item.get("text", ""),  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
            reading_order=reading_order,
            confidence=float(item.get("confidence", 1.0)),  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
            ocr_engine_provenance="docling-standard",
            is_parasitic=bool(item.get("is_parasitic", False)),  # pyright: ignore[reportAny, reportExplicitAny]  # Docling JSON schema is unversioned; typed access via Any is intentional here.
        )
