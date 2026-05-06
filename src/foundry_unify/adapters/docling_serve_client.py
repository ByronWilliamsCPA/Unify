"""HTTP client adapter for the docling-serve REST API.

Adapted from image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py.
Parses the `documents[]` array response format from POST /v1/convert/file.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Any

import httpx

from foundry_unify.core.exceptions import DoclingServiceError
from foundry_unify.utils.logging import get_logger

if TYPE_CHECKING:
    from foundry_unify.models.document_metadata import DoclingRoutingParams

logger = get_logger(__name__)


@dataclass(frozen=True)
class DoclingRawResponse:
    """Parsed response from docling-serve /v1/convert/file.

    Attributes:
        success: Whether the conversion succeeded.
        json_content: Raw Docling JSON document (contains pages, tables, etc.).
        page_count: Number of pages in the document.
        ocr_applied: Whether OCR was applied.
        processing_time_ms: Server-reported processing time.
        error: Error message if conversion failed.
    """

    success: bool
    json_content: dict[str, Any]
    page_count: int
    ocr_applied: bool
    processing_time_ms: float
    error: str | None = None


@dataclass
class DoclingServeClient:
    """HTTP client for the docling-serve REST API.

    Sends documents to POST /v1/convert/file and returns structured responses.
    Uses HTTP (not HTTPS) intentionally: docling-serve runs on a private LAN.
    """

    base_url: str = "http://192.168.1.209:5001"
    timeout: float = 300.0
    _client: httpx.Client | None = field(default=None, repr=False, init=False)

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(  # nosec B113
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def health_check(self) -> bool:
        """Return True if docling-serve responds to GET /health."""
        try:
            response = self._get_client().get("/health", timeout=5.0)
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
        return bool(response.status_code == 200)

    def convert_file(
        self,
        file_path: Path,
        routing_params: DoclingRoutingParams | None = None,
    ) -> DoclingRawResponse:
        """Upload a file to docling-serve and return the parsed response.

        Args:
            file_path: Path to the document (PDF or image).
            routing_params: Pre-computed Docling flags from foundry-prepare-doc.

        Raises:
            FileNotFoundError: If file_path does not exist.
            DoclingServiceError: On connection failure, timeout, or HTTP error.
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        form_data = (
            routing_params.to_form_data()
            if routing_params
            else {"output_format": "json"}
        )

        logger.info(
            "docling_convert_start",
            file=str(file_path),
            pipeline=form_data.get("pipeline", "standard"),
        )

        start = time.perf_counter()
        try:
            response = self._get_client().post(
                "/v1/convert/file",
                files={"file": (file_path.name, file_path.read_bytes())},
                data=form_data,
            )
        except httpx.ConnectError as exc:
            msg = f"Cannot connect to docling-serve at {self.base_url}: {exc}"
            raise DoclingServiceError(msg) from exc
        except httpx.TimeoutException as exc:
            elapsed = (time.perf_counter() - start) * 1000
            msg = f"docling-serve timeout after {elapsed:.0f}ms"
            raise DoclingServiceError(msg) from exc

        if response.status_code != 200:
            msg = f"docling-serve returned HTTP {response.status_code}: {response.text[:500]}"
            raise DoclingServiceError(msg, status_code=response.status_code)

        return self._parse_response(
            response.json(), (time.perf_counter() - start) * 1000
        )

    @staticmethod
    def _parse_response(
        raw: dict[str, Any],
        elapsed_ms: float,
    ) -> DoclingRawResponse:
        """Parse the JSON response from /v1/convert/file.

        Handles both the contract format (`documents[]` array) and the legacy
        single-document format (`document` key) for compatibility with older
        docling-serve deployments.
        """
        # Contract format: {"documents": [{...}]}
        docs = raw.get("documents")
        if docs and isinstance(docs, list) and len(docs) > 0:
            doc = docs[0]
        else:
            # Legacy format: {"document": {...}} -- older docling-serve versions
            doc = raw.get("document", {})

        json_content: dict[str, Any] = doc.get("json_content") or {}
        meta: dict[str, Any] = doc.get("metadata") or {}

        page_count = meta.get("page_count") or len(json_content.get("pages", []))
        processing_time = meta.get("processing_time_ms", elapsed_ms)
        is_success = doc.get("status") == "success"

        logger.info(
            "docling_convert_complete",
            success=is_success,
            pages=page_count,
            time_ms=f"{elapsed_ms:.0f}",
        )

        return DoclingRawResponse(
            success=is_success,
            json_content=json_content,
            page_count=page_count or 1,
            ocr_applied=bool(meta.get("ocr_applied", True)),
            processing_time_ms=processing_time,
            error=doc.get("error"),
        )

    def __enter__(self) -> DoclingServeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
