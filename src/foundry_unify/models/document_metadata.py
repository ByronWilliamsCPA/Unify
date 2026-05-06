"""Inbound DocumentMetadata schema -- B1-scoped subset of prepare-doc output.

Only fields consumed in B1 are modeled. `extra="ignore"` ensures forward-compat
with the full schema in image_detection/src/image_preprocessing_detector/schema.py.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DoclingRoutingParams(BaseModel):
    """Docling pipeline configuration pre-computed by foundry-prepare-doc.

    Mirrors DoclingRoutingParams in image_detection/schema.py:755.
    Only fields that affect the /v1/convert/file form data are included.
    """

    model_config = ConfigDict(extra="ignore")

    pipeline: Literal["standard", "vlm", "legacy"] = "standard"
    vlm_model: str | None = None
    ocr_enabled: bool = True
    ocr_force: bool = False
    ocr_engine: str = "auto"
    ocr_lang: str | None = None
    tables_enabled: bool = True
    table_mode: Literal["fast", "accurate"] = "accurate"

    def to_form_data(self) -> dict[str, str]:
        """Convert to multipart form fields for POST /v1/convert/file."""
        data: dict[str, str] = {"output_format": "json"}

        if self.pipeline != "standard":
            data["pipeline"] = self.pipeline

        if self.vlm_model:
            data["vlm_model"] = self.vlm_model

        if not self.ocr_enabled:
            data["ocr"] = "false"
        elif self.ocr_force:
            data["force_ocr"] = "true"

        if self.ocr_engine != "auto":
            data["ocr_engine"] = self.ocr_engine

        if self.ocr_lang:
            data["ocr_lang"] = self.ocr_lang

        if not self.tables_enabled:
            data["tables"] = "false"
        else:
            data["table_mode"] = self.table_mode

        return data


class ProcessingRecommendation(BaseModel):
    """Tier recommendation from foundry-prepare-doc routing engine."""

    model_config = ConfigDict(extra="ignore")

    tier: Literal["standard", "vlm_assisted", "vlm_validated"] = "standard"


class InboundDocumentMetadata(BaseModel):
    """B1-scoped subset of DocumentMetadata.json written by foundry-prepare-doc.

    Full schema: image_detection/src/image_preprocessing_detector/schema.py:1249
    """

    model_config = ConfigDict(extra="ignore")

    document_id: str
    trace_id: str
    source_track: str
    num_pages: int = Field(ge=1)
    pdf_type: str | None = None
    processing_status: Literal["complete", "halted"] = "complete"
    docling_params: DoclingRoutingParams | None = None
    processing_recommendation: ProcessingRecommendation | None = None
