"""POST /process endpoint for Cloud Workflows entry point.

Receives {trace_id, env, source_track}, orchestrates OCR via docling-serve,
and writes DoclingDOM.json to GCS.
"""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from foundry_unify.adapters.docling_serve_client import (
    DoclingRawResponse,
    DoclingServeClient,
)
from foundry_unify.adapters.gcs_client import GCSArtifactReader, GCSArtifactWriter
from foundry_unify.core.config import settings
from foundry_unify.core.exceptions import DoclingServiceError, GCSError
from foundry_unify.pipeline.dom_assembler import DOMAssembler
from foundry_unify.pipeline.layout_postprocessor import LayoutPostprocessor
from foundry_unify.pipeline.tier_selector import ProcessingTier, TierSelector
from foundry_unify.utils.logging import get_logger

router = APIRouter(tags=["pipeline"])
logger = get_logger(__name__)


class ProcessRequest(BaseModel):
    """Request body for POST /process."""

    trace_id: str
    env: Literal["dev", "staging", "prod"]
    source_track: Literal["document", "audio"]


class ProcessResponse(BaseModel):
    """Response body for POST /process."""

    trace_id: str
    document_id: str
    processing_status: Literal["complete", "halted"]
    processing_tier: str
    gcs_path: str


@router.post(
    "/process",
    status_code=status.HTTP_200_OK,
    summary="Orchestrate OCR for a document or normalize an audio transcript",
)
async def process(request: ProcessRequest) -> ProcessResponse:
    """Entry point for Cloud Workflows.

    Document track: downloads DocumentMetadata.json from GCS, runs OCR via
    docling-serve, applies KI-002 mitigation, assembles DoclingDOM, writes to GCS.

    Audio track: not supported in B1. Returns 422 NOT_IMPLEMENTED_YET.
    """
    log = logger.bind(trace_id=request.trace_id, env=request.env)
    log.info("process_start", source_track=request.source_track)

    if request.source_track == "audio":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="audio track normalization is not implemented in B1; it is coming in B2",
        )

    reader = GCSArtifactReader(bucket_template=settings.gcs_bucket_template)
    writer = GCSArtifactWriter(bucket_template=settings.gcs_bucket_template)

    try:
        metadata = reader.download_document_metadata(
            env=request.env, trace_id=request.trace_id
        )
    except GCSError as exc:
        log.exception("gcs_read_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read DocumentMetadata.json: {exc}",
        ) from exc

    tier = TierSelector.select(metadata)

    if tier == ProcessingTier.HALTED:
        log.info("process_halted", document_id=metadata.document_id)
        dom = DOMAssembler.assemble(
            raw_response=_empty_raw_response(),
            document_id=metadata.document_id,
            trace_id=request.trace_id,
            source_track="document",
            processing_tier="standard",
            processing_status="halted",
        )
        try:
            gcs_path = writer.write_docling_dom(
                dom=dom, env=request.env, trace_id=request.trace_id
            )
        except GCSError as exc:
            log.exception("gcs_write_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to write DoclingDOM.json: {exc}",
            ) from exc
        return ProcessResponse(
            trace_id=request.trace_id,
            document_id=metadata.document_id,
            processing_status="halted",
            processing_tier=tier.value,
            gcs_path=gcs_path,
        )

    docling_client = DoclingServeClient(
        base_url=settings.docling_serve_url,
        timeout=settings.docling_serve_timeout_seconds,
    )

    # #ASSUME: External Resources: for B1 we send a sentinel PDF to trigger the
    # docling-serve code path. Real GCS page-image download is wired in B2.
    # #VERIFY: Replace with actual GCS page image download before B1 gate.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"%PDF-1.4 sentinel-for-b1")
        tmp_path = Path(tmp.name)

    try:
        raw = docling_client.convert_file(
            file_path=tmp_path,
            routing_params=metadata.docling_params,
        )
    except DoclingServiceError as exc:
        log.exception("docling_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"docling-serve error: {exc}",
        ) from exc
    finally:
        with contextlib.suppress(FileNotFoundError):
            await asyncio.to_thread(tmp_path.unlink)

    postprocessor = LayoutPostprocessor(
        confidence_threshold=settings.layout_confidence_threshold
    )
    pages = postprocessor.apply(raw.json_content.get("pages", []))  # pyright: ignore[reportAny]
    corrected_raw = DoclingRawResponse(
        success=raw.success,
        json_content={**raw.json_content, "pages": pages},  # pyright: ignore[reportAny]
        page_count=raw.page_count,
        ocr_applied=raw.ocr_applied,
        processing_time_ms=raw.processing_time_ms,
        error=raw.error,
    )

    # HALTED was already checked above; the remaining tier values map to the
    # three literals that DOMAssembler.assemble accepts.
    dom = DOMAssembler.assemble(
        raw_response=corrected_raw,
        document_id=metadata.document_id,
        trace_id=request.trace_id,
        source_track="document",
        processing_tier=tier.value,
    )

    try:
        gcs_path = writer.write_docling_dom(
            dom=dom, env=request.env, trace_id=request.trace_id
        )
    except GCSError as exc:
        log.exception("gcs_write_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to write DoclingDOM.json: {exc}",
        ) from exc

    log.info("process_complete", document_id=metadata.document_id, gcs_path=gcs_path)
    return ProcessResponse(
        trace_id=request.trace_id,
        document_id=metadata.document_id,
        processing_status="complete",
        processing_tier=tier.value,
        gcs_path=gcs_path,
    )


def _empty_raw_response() -> DoclingRawResponse:
    """Return a minimal DoclingRawResponse for halted documents."""
    return DoclingRawResponse(
        success=False,
        json_content={},
        page_count=0,
        ocr_applied=False,
        processing_time_ms=0.0,
    )
