"""DoclingDOM output schema -- the canonical artifact written to GCS 03-docling-dom/.

Both the document track (OCR'd PDFs) and the audio track (normalized transcripts)
produce this identical schema. foundry-chunk reads it without knowing the source track.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BBox(BaseModel):
    """Bounding box in page-coordinate space (points from top-left)."""

    model_config = ConfigDict(frozen=True)

    x1: float
    y1: float
    x2: float
    y2: float


class ElementDOM(BaseModel):
    """A single layout element on a page."""

    model_config = ConfigDict(extra="ignore")

    element_id: str
    element_type: str = Field(
        description="Docling layout class: Text, Table, Picture, etc."
    )
    text: str = ""
    bbox: BBox | None = None
    reading_order: int = Field(ge=1)
    ocr_engine_provenance: str = "docling-standard"
    is_parasitic: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PageDOM(BaseModel):
    """A single page in the DoclingDOM."""

    model_config = ConfigDict(extra="ignore")

    page_number: int = Field(ge=1)
    reading_order_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    elements: list[ElementDOM] = Field(default_factory=list)


class DOMMetadata(BaseModel):
    """Processing provenance metadata attached to each DoclingDOM."""

    model_config = ConfigDict(extra="ignore")

    processing_tier: Literal["standard", "vlm_assisted", "vlm_validated"]
    layout_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ocr_applied: bool = True
    page_count: int = Field(ge=0)


class DoclingDOM(BaseModel):
    """Canonical output artifact for foundry-unify.

    Written to gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json.
    Schema is identical for document-track and audio-track inputs.
    """

    model_config = ConfigDict(extra="ignore")

    document_id: str
    trace_id: str
    source_track: Literal["document", "audio"]
    processing_status: Literal["complete", "halted"] = "complete"
    pages: list[PageDOM]
    metadata: DOMMetadata
