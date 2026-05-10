# Phase B1: Layout and Basic OCR — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build end-to-end document processing for the `standard` tier: a born-digital PDF enters via `POST /process`, docling-serve performs OCR via the HTTP API, and a valid `DoclingDOM.json` is written to GCS — with KI-002 table-misclassification mitigation shipped from day one.

**Architecture:** `POST /process` receives `{trace_id, env, source_track}` from Cloud Workflows; a `GCSArtifactReader` downloads `DocumentMetadata.json` from GCS; the `DoclingServeClient` calls the live `http://192.168.1.209:5001/v1/convert/file` endpoint with routing params pre-computed by foundry-prepare-doc; the `LayoutPostprocessor` applies the KI-002 confidence-threshold fix before `DOMAssembler` converts the raw Docling JSON into the canonical `DoclingDOM.json` schema written by `GCSArtifactWriter`. The audio track (`source_track: "audio"`) is detected and rejected with a clear error code in B1 — full audio normalization is B2.

**Tech Stack:** FastAPI, httpx (Docling HTTP client), google-cloud-storage (GCS I/O), Pydantic v2 (all schemas), structlog (correlation-aware logging), pytest + unittest.mock (unit tests, no live dependencies).

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/foundry_unify/models/__init__.py` | Create | Package init |
| `src/foundry_unify/models/document_metadata.py` | Create | `InboundDocumentMetadata`, `DoclingRoutingParams`, `ProcessingRecommendation` — the subset of fields B1 actually consumes, `extra="ignore"` for forward-compat |
| `src/foundry_unify/models/docling_dom.py` | Create | `DoclingDOM`, `PageDOM`, `ElementDOM`, `DOMMetadata`, `BBox` — the canonical output schema written to GCS |
| `src/foundry_unify/adapters/__init__.py` | Create | Package init |
| `src/foundry_unify/adapters/docling_serve_client.py` | Create | `DoclingServeClient` + `DoclingRawResponse` — adapts reference `docling_client.py` to foundry_unify imports and contract response format |
| `src/foundry_unify/adapters/gcs_client.py` | Create | `GCSArtifactReader` (download metadata + images) and `GCSArtifactWriter` (write DOM) |
| `src/foundry_unify/pipeline/__init__.py` | Create | Package init |
| `src/foundry_unify/pipeline/source_track_router.py` | Create | `SourceTrackRouter` — validates `source_track`, raises `MissingSourceTrackError` (422) |
| `src/foundry_unify/pipeline/tier_selector.py` | Create | `TierSelector` — reads `processing_recommendation.tier`, handles `halted` fast-path |
| `src/foundry_unify/pipeline/layout_postprocessor.py` | Create | `LayoutPostprocessor` — KI-002 mitigation: reclassify `Table` confidence < threshold → `Text` |
| `src/foundry_unify/pipeline/dom_assembler.py` | Create | `DOMAssembler` — converts `DoclingRawResponse` + metadata into `DoclingDOM` |
| `src/foundry_unify/api/process.py` | Create | `POST /process` FastAPI endpoint + `ProcessRequest` schema |
| `src/foundry_unify/core/config.py` | Modify | Add `docling_serve_url`, `docling_serve_timeout_seconds`, `layout_confidence_threshold`, `gcs_bucket_template` |
| `src/foundry_unify/core/exceptions.py` | Modify | Add `DoclingServiceError`, `GCSError`, `MissingSourceTrackError`, `MissingDoclingDOMError` |
| `src/foundry_unify/api/health.py` | Modify | Add `docling_serve` reachability check in `readiness()` |
| `src/foundry_unify/main.py` | Modify | Register `process_router` |

Tests mirror the `src` layout under `tests/unit/` and `tests/integration/`.

---

## Task 1: Branch, Dependencies, and Config

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/foundry_unify/core/config.py`
- Modify: `src/foundry_unify/core/exceptions.py`

- [ ] **Step 1: Create the feature branch**

```bash
git checkout main && git pull origin main
git checkout -b feat/phase-b1-layout-ocr
git branch --show-current
```

Expected output: `feat/phase-b1-layout-ocr`

- [ ] **Step 2: Add runtime dependencies to pyproject.toml**

In `pyproject.toml`, add to the `dependencies` list (under `pydantic-settings`):

```toml
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=23.1.0",
    "rich>=13.5.0",
    "httpx>=0.27.0",
    "google-cloud-storage>=2.10.0",
    "fastapi>=0.120.1",
    "uvicorn[standard]>=0.23.0",
    "python-multipart>=0.0.18",
    "starlette>=0.49.1",
]
```

Remove `fastapi`, `uvicorn`, `python-multipart`, `starlette` from the `api` optional group to avoid duplication.

- [ ] **Step 3: Sync dependencies**

```bash
uv sync --all-extras
```

Expected: Lock file updated, no errors.

- [ ] **Step 4: Add B1 settings to config.py**

Replace the entire `Settings` class in `src/foundry_unify/core/config.py`:

```python
"""Configuration settings for Foundry Unify."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables (prefix: FOUNDRY_UNIFY_)."""

    model_config = SettingsConfigDict(
        env_prefix="foundry_unify_",
        case_sensitive=False,
        extra="ignore",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False
    include_timestamp: bool = True

    # docling-serve connection
    docling_serve_url: str = Field(
        default="http://192.168.1.209:5001",
        description="Base URL for the docling-serve HTTP API",
    )
    docling_serve_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        description="Request timeout in seconds for docling-serve calls",
    )

    # KI-002 mitigation: Table confidence threshold
    layout_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Table detections below this confidence are reclassified to Text (KI-002)",
    )

    # GCS
    gcs_bucket_template: str = Field(
        default="rag-pipeline-{env}",
        description="GCS bucket name template; {env} is replaced with the request env value",
    )


settings = Settings()
```

- [ ] **Step 5: Add pipeline-specific exceptions to exceptions.py**

Append to `src/foundry_unify/core/exceptions.py` (before the `__all__` list):

```python
class DoclingServiceError(ExternalServiceError):
    """Docling-serve API errors (connection failures, HTTP errors, parse failures).

    Example:
        >>> raise DoclingServiceError(
        ...     "docling-serve returned HTTP 503",
        ...     status_code=503,
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            service_name="docling-serve",
            status_code=status_code,
            details=details,
            error_code="DOCLING_SERVICE_ERROR",
        )


class GCSError(ExternalServiceError):
    """GCS read or write errors.

    Example:
        >>> raise GCSError("Failed to download DocumentMetadata.json", path="gs://...")
    """

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if path:
            details["path"] = path
        super().__init__(
            message,
            service_name="GCS",
            details=details,
            error_code="GCS_ERROR",
        )


class MissingSourceTrackError(ValidationError):
    """Source track field absent or unrecognized in input metadata.

    Triggers a 422 response with error code MISSING_SOURCE_TRACK.
    """

    def __init__(self, received: str | None = None) -> None:
        super().__init__(
            "source_track field is missing or unrecognized",
            field="source_track",
            value=received,
            error_code="MISSING_SOURCE_TRACK",
        )


class MissingDoclingDOMError(ValidationError):
    """Audio track input is missing the pre-assembled docling_document field.

    Triggers a 422 response with error code MISSING_DOCLING_DOM.
    """

    def __init__(self) -> None:
        super().__init__(
            "docling_document field is required for audio track input",
            field="docling_document",
            error_code="MISSING_DOCLING_DOM",
        )
```

Update `__all__` to include the new exceptions:

```python
__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "ConfigurationError",
    "DatabaseError",
    "DoclingServiceError",
    "ExternalServiceError",
    "GCSError",
    "MissingDoclingDOMError",
    "MissingSourceTrackError",
    "ProjectBaseError",
    "ResourceNotFoundError",
    "ValidationError",
]
```

- [ ] **Step 6: Verify existing tests still pass**

```bash
uv run pytest tests/ -v
```

Expected: All existing tests PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/foundry_unify/core/config.py src/foundry_unify/core/exceptions.py
git commit -m "feat: add B1 dependencies, settings, and pipeline exceptions"
```

---

## Task 2: DoclingDOM Output Schema

**Files:**
- Create: `src/foundry_unify/models/__init__.py`
- Create: `src/foundry_unify/models/docling_dom.py`
- Create: `tests/unit/test_models_docling_dom.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_models_docling_dom.py`:

```python
"""Tests for the DoclingDOM output schema."""

import pytest

from foundry_unify.models.docling_dom import (
    BBox,
    DOMMetadata,
    DoclingDOM,
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_models_docling_dom.py -v
```

Expected: `ModuleNotFoundError` — `foundry_unify.models.docling_dom` does not exist.

- [ ] **Step 3: Create the models package and DoclingDOM schema**

Create `src/foundry_unify/models/__init__.py`:

```python
"""Data models for Foundry Unify input/output schemas."""
```

Create `src/foundry_unify/models/docling_dom.py`:

```python
"""DoclingDOM output schema — the canonical artifact written to GCS 03-docling-dom/.

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
    element_type: str = Field(description="Docling layout class: Text, Table, Picture, etc.")
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_models_docling_dom.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/models/ tests/unit/test_models_docling_dom.py
git commit -m "feat: add DoclingDOM output schema"
```

---

## Task 3: DocumentMetadata Input Schema

**Files:**
- Create: `src/foundry_unify/models/document_metadata.py`
- Create: `tests/unit/test_models_document_metadata.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_models_document_metadata.py`:

```python
"""Tests for the inbound DocumentMetadata schema (B1-scoped subset)."""

import json

import pytest

from foundry_unify.models.document_metadata import (
    DoclingRoutingParams,
    InboundDocumentMetadata,
    ProcessingRecommendation,
)


@pytest.mark.unit
def test_docling_routing_params_to_form_data_defaults() -> None:
    params = DoclingRoutingParams()
    data = params.to_form_data()
    assert data["output_format"] == "json"
    assert "pipeline" not in data  # standard is the default, not sent explicitly


@pytest.mark.unit
def test_docling_routing_params_force_ocr() -> None:
    params = DoclingRoutingParams(ocr_force=True)
    data = params.to_form_data()
    assert data["force_ocr"] == "true"


@pytest.mark.unit
def test_docling_routing_params_no_ocr() -> None:
    params = DoclingRoutingParams(ocr_enabled=False)
    data = params.to_form_data()
    assert data["ocr"] == "false"


@pytest.mark.unit
def test_docling_routing_params_vlm_pipeline() -> None:
    params = DoclingRoutingParams(pipeline="vlm", vlm_model="ibm-granite/granite-docling-258M")
    data = params.to_form_data()
    assert data["pipeline"] == "vlm"
    assert data["vlm_model"] == "ibm-granite/granite-docling-258M"


@pytest.mark.unit
def test_inbound_document_metadata_parses_minimal_json() -> None:
    raw = {
        "document_id": "doc-001",
        "trace_id": "trace-001",
        "source_track": "document",
        "num_pages": 3,
        "pdf_type": "born_digital",
        "processing_recommendation": {"tier": "standard"},
        "processing_version": {"version": "1.0.0"},
        "pages": [{"page_number": i} for i in range(1, 4)],
        "extra_unknown_field": "ignored",
    }
    meta = InboundDocumentMetadata.model_validate(raw)
    assert meta.document_id == "doc-001"
    assert meta.source_track == "document"
    assert meta.processing_recommendation is not None
    assert meta.processing_recommendation.tier == "standard"


@pytest.mark.unit
def test_inbound_document_metadata_halted_status() -> None:
    raw = {
        "document_id": "doc-enc",
        "trace_id": "trace-enc",
        "source_track": "document",
        "num_pages": 1,
        "processing_status": "halted",
        "processing_version": {"version": "1.0.0"},
        "pages": [{"page_number": 1}],
    }
    meta = InboundDocumentMetadata.model_validate(raw)
    assert meta.processing_status == "halted"


@pytest.mark.unit
def test_inbound_document_metadata_missing_docling_params_returns_none() -> None:
    raw = {
        "document_id": "doc-002",
        "trace_id": "trace-002",
        "source_track": "document",
        "num_pages": 1,
        "processing_version": {"version": "1.0.0"},
        "pages": [{"page_number": 1}],
    }
    meta = InboundDocumentMetadata.model_validate(raw)
    assert meta.docling_params is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_models_document_metadata.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create the document metadata schema**

Create `src/foundry_unify/models/document_metadata.py`:

```python
"""Inbound DocumentMetadata schema — B1-scoped subset of prepare-doc output.

Only fields consumed in B1 are modeled. `extra="ignore"` ensures forward-compat
with the full schema in image_detection/src/image_preprocessing_detector/schema.py.
"""

from __future__ import annotations

from typing import Any, Literal

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_models_document_metadata.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/models/document_metadata.py tests/unit/test_models_document_metadata.py
git commit -m "feat: add InboundDocumentMetadata and DoclingRoutingParams models"
```

---

## Task 4: DoclingServeClient Adapter

**Files:**
- Create: `src/foundry_unify/adapters/__init__.py`
- Create: `src/foundry_unify/adapters/docling_serve_client.py`
- Create: `tests/unit/test_adapters_docling_serve_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_adapters_docling_serve_client.py`:

```python
"""Tests for DoclingServeClient."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from foundry_unify.adapters.docling_serve_client import DoclingRawResponse, DoclingServeClient
from foundry_unify.core.exceptions import DoclingServiceError
from foundry_unify.models.document_metadata import DoclingRoutingParams


@pytest.fixture
def client() -> DoclingServeClient:
    return DoclingServeClient(base_url="http://test-docling:5001", timeout=10.0)


@pytest.mark.unit
def test_health_check_returns_true_on_200(client: DoclingServeClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch.object(client._get_client(), "get", return_value=mock_response):
        with patch.object(client, "_get_client") as mock_get:
            mock_http = MagicMock()
            mock_http.get.return_value = mock_response
            mock_get.return_value = mock_http
            assert client.health_check() is True


@pytest.mark.unit
def test_health_check_returns_false_on_connect_error(client: DoclingServeClient) -> None:
    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.get.side_effect = httpx.ConnectError("refused")
        mock_get.return_value = mock_http
        assert client.health_check() is False


@pytest.mark.unit
def test_convert_file_sends_correct_form_data(
    client: DoclingServeClient, tmp_path: Path
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    params = DoclingRoutingParams(ocr_force=True)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "documents": [
            {
                "status": "success",
                "json_content": {"schema_name": "DoclingDocument", "pages": []},
                "metadata": {"page_count": 1, "ocr_applied": True, "processing_time_ms": 500},
            }
        ]
    }

    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_get.return_value = mock_http

        result = client.convert_file(pdf, routing_params=params)

        call_kwargs = mock_http.post.call_args
        assert call_kwargs.kwargs["data"]["force_ocr"] == "true"
        assert result.success is True
        assert result.page_count == 1


@pytest.mark.unit
def test_convert_file_raises_on_http_error(
    client: DoclingServeClient, tmp_path: Path
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF test")

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mock_get.return_value = mock_http

        with pytest.raises(DoclingServiceError) as exc_info:
            client.convert_file(pdf)

    assert exc_info.value.details.get("status_code") == 503


@pytest.mark.unit
def test_convert_file_raises_on_connect_error(
    client: DoclingServeClient, tmp_path: Path
) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF test")

    with patch.object(client, "_get_client") as mock_get:
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("refused")
        mock_get.return_value = mock_http

        with pytest.raises(DoclingServiceError):
            client.convert_file(pdf)


@pytest.mark.unit
def test_convert_file_raises_on_missing_file(client: DoclingServeClient) -> None:
    with pytest.raises(FileNotFoundError):
        client.convert_file(Path("/nonexistent/doc.pdf"))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_adapters_docling_serve_client.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create the adapter package and client**

Create `src/foundry_unify/adapters/__init__.py`:

```python
"""External service adapters for Foundry Unify."""
```

Create `src/foundry_unify/adapters/docling_serve_client.py`:

```python
"""HTTP client adapter for the docling-serve REST API.

Adapted from image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py.
Parses the `documents[]` array response format from POST /v1/convert/file.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from foundry_unify.core.exceptions import DoclingServiceError
from foundry_unify.utils.structured_logging import get_logger

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
    _client: httpx.Client | None = field(default=None, repr=False)

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
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

        form_data = routing_params.to_form_data() if routing_params else {"output_format": "json"}

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

        return self._parse_response(response.json(), (time.perf_counter() - start) * 1000)

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
            # Legacy format: {"document": {...}} — older docling-serve versions
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_adapters_docling_serve_client.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/adapters/ tests/unit/test_adapters_docling_serve_client.py
git commit -m "feat: add DoclingServeClient adapter"
```

---

## Task 5: SourceTrackRouter

**Files:**
- Create: `src/foundry_unify/pipeline/__init__.py`
- Create: `src/foundry_unify/pipeline/source_track_router.py`
- Create: `tests/unit/test_pipeline_source_track_router.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_pipeline_source_track_router.py`:

```python
"""Tests for SourceTrackRouter."""

import pytest

from foundry_unify.core.exceptions import MissingSourceTrackError
from foundry_unify.pipeline.source_track_router import SourceTrack, SourceTrackRouter


@pytest.mark.unit
def test_routes_document_track() -> None:
    track = SourceTrackRouter.detect({"source_track": "document"})
    assert track == SourceTrack.DOCUMENT


@pytest.mark.unit
def test_routes_audio_track() -> None:
    track = SourceTrackRouter.detect({"source_track": "audio"})
    assert track == SourceTrack.AUDIO


@pytest.mark.unit
def test_raises_on_missing_source_track() -> None:
    with pytest.raises(MissingSourceTrackError) as exc_info:
        SourceTrackRouter.detect({})
    assert exc_info.value.error_code == "MISSING_SOURCE_TRACK"


@pytest.mark.unit
def test_raises_on_unknown_source_track() -> None:
    with pytest.raises(MissingSourceTrackError) as exc_info:
        SourceTrackRouter.detect({"source_track": "video"})
    assert "video" in str(exc_info.value)


@pytest.mark.unit
def test_raises_on_none_source_track() -> None:
    with pytest.raises(MissingSourceTrackError):
        SourceTrackRouter.detect({"source_track": None})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_pipeline_source_track_router.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement SourceTrackRouter**

Create `src/foundry_unify/pipeline/__init__.py`:

```python
"""OCR orchestration pipeline components for Foundry Unify."""
```

Create `src/foundry_unify/pipeline/source_track_router.py`:

```python
"""Source track detection — determines document vs audio processing path."""

from __future__ import annotations

from enum import Enum
from typing import Any

from foundry_unify.core.exceptions import MissingSourceTrackError


class SourceTrack(str, Enum):
    """Valid source tracks for foundry-unify input."""

    DOCUMENT = "document"
    AUDIO = "audio"


class SourceTrackRouter:
    """Validates and extracts the source_track field from raw input metadata.

    Raises MissingSourceTrackError (maps to HTTP 422) for absent or unknown values.
    """

    _VALID: frozenset[str] = frozenset(t.value for t in SourceTrack)

    @classmethod
    def detect(cls, metadata: dict[str, Any]) -> SourceTrack:
        """Return the SourceTrack for the given metadata dict.

        Args:
            metadata: Raw JSON-parsed input metadata (DocumentMetadata or TranscriptMetadata).

        Raises:
            MissingSourceTrackError: If source_track is absent, None, or unrecognized.
        """
        value = metadata.get("source_track")
        if not value or value not in cls._VALID:
            raise MissingSourceTrackError(received=str(value) if value else None)
        return SourceTrack(value)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_pipeline_source_track_router.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/pipeline/ tests/unit/test_pipeline_source_track_router.py
git commit -m "feat: add SourceTrackRouter with MISSING_SOURCE_TRACK error"
```

---

## Task 6: TierSelector

**Files:**
- Create: `src/foundry_unify/pipeline/tier_selector.py`
- Create: `tests/unit/test_pipeline_tier_selector.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_pipeline_tier_selector.py`:

```python
"""Tests for TierSelector."""

import pytest

from foundry_unify.models.document_metadata import InboundDocumentMetadata, ProcessingRecommendation
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_pipeline_tier_selector.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement TierSelector**

Create `src/foundry_unify/pipeline/tier_selector.py`:

```python
"""Tier selection — maps DocumentMetadata processing recommendation to a pipeline tier."""

from __future__ import annotations

from enum import Enum

from foundry_unify.models.document_metadata import InboundDocumentMetadata


class ProcessingTier(str, Enum):
    """Docling pipeline tier for a given document."""

    STANDARD = "standard"
    VLM_ASSISTED = "vlm_assisted"
    VLM_VALIDATED = "vlm_validated"
    HALTED = "halted"


class TierSelector:
    """Reads processing_recommendation.tier from DocumentMetadata and returns the tier.

    Halted documents (encrypted, unreadable) bypass OCR entirely and emit a
    DoclingDOM with processing_status: "halted".
    """

    @staticmethod
    def select(metadata: InboundDocumentMetadata) -> ProcessingTier:
        """Return the ProcessingTier for this document.

        Args:
            metadata: Parsed inbound DocumentMetadata.

        Returns:
            HALTED if processing_status is "halted"; otherwise the tier from
            processing_recommendation (defaults to STANDARD).
        """
        if metadata.processing_status == "halted":
            return ProcessingTier.HALTED

        if metadata.processing_recommendation:
            return ProcessingTier(metadata.processing_recommendation.tier)

        return ProcessingTier.STANDARD
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_pipeline_tier_selector.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/pipeline/tier_selector.py tests/unit/test_pipeline_tier_selector.py
git commit -m "feat: add TierSelector with halted document fast-path"
```

---

## Task 7: LayoutPostprocessor (KI-002 Mitigation)

**Files:**
- Create: `src/foundry_unify/pipeline/layout_postprocessor.py`
- Create: `tests/unit/test_pipeline_layout_postprocessor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_pipeline_layout_postprocessor.py`:

```python
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
    pages = _make_raw_pages([[
        {"label": "Table", "confidence": 0.3, "text": "col1 col2\nrow1 row2"},
    ]])
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Text"


@pytest.mark.unit
def test_high_confidence_table_preserved() -> None:
    pages = _make_raw_pages([[
        {"label": "Table", "confidence": 0.8, "text": "col1 | col2"},
    ]])
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Table"


@pytest.mark.unit
def test_table_at_threshold_is_reclassified() -> None:
    """Confidence equal to the threshold is reclassified (< is strict; == triggers)."""
    pages = _make_raw_pages([[
        {"label": "Table", "confidence": 0.5, "text": "..."},
    ]])
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Text"


@pytest.mark.unit
def test_non_table_elements_not_affected() -> None:
    pages = _make_raw_pages([[
        {"label": "Text", "confidence": 0.1, "text": "paragraph"},
        {"label": "Picture", "confidence": 0.2, "text": ""},
    ]])
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Text"
    assert result[0]["items"][1]["label"] == "Picture"


@pytest.mark.unit
def test_element_without_confidence_field_preserved_as_table() -> None:
    """Missing confidence field defaults to 1.0 — do not reclassify."""
    pages = _make_raw_pages([[
        {"label": "Table", "text": "col1 col2"},
    ]])
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0]["label"] == "Table"


@pytest.mark.unit
def test_empty_pages_returns_empty_list() -> None:
    result = LayoutPostprocessor(confidence_threshold=0.5).apply([])
    assert result == []


@pytest.mark.unit
def test_reclassified_element_tagged_with_ki002_flag() -> None:
    pages = _make_raw_pages([[
        {"label": "Table", "confidence": 0.2, "text": "text"},
    ]])
    result = LayoutPostprocessor(confidence_threshold=0.5).apply(pages)
    assert result[0]["items"][0].get("ki002_reclassified") is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_pipeline_layout_postprocessor.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement LayoutPostprocessor**

Create `src/foundry_unify/pipeline/layout_postprocessor.py`:

```python
"""LayoutPostprocessor — applies KI-002 Table misclassification mitigation.

KI-002: Multi-column body text is misclassified as Table with 100% false-positive
rate when Docling layout confidence is below ~0.5. This postprocessor reclassifies
Table detections at or below the confidence threshold to Text, preventing downstream
reading-order corruption (KI-008).

Reference: image_detection/docs/known_issues/KI-002-docling-table-multicolumn.md
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass
class LayoutPostprocessor:
    """Applies KI-002 per-class confidence threshold to raw Docling page data.

    Args:
        confidence_threshold: Table detections at or below this value are
            reclassified to Text. Default matches the B1 config setting.
    """

    confidence_threshold: float = 0.5

    def apply(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply KI-002 mitigation to the pages list from a Docling JSON response.

        Args:
            pages: The `pages` list from `json_content` in the Docling response.
                Each page is a dict with `items` (layout elements).

        Returns:
            A deep-copied pages list with low-confidence Table elements reclassified.
        """
        if not pages:
            return []

        result = copy.deepcopy(pages)
        for page in result:
            for item in page.get("items", []):
                if item.get("label") != "Table":
                    continue
                # Missing confidence field defaults to 1.0 — no reclassification
                confidence: float = item.get("confidence", 1.0)
                if confidence <= self.confidence_threshold:
                    item["label"] = "Text"
                    item["ki002_reclassified"] = True
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_pipeline_layout_postprocessor.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/pipeline/layout_postprocessor.py tests/unit/test_pipeline_layout_postprocessor.py
git commit -m "feat: add LayoutPostprocessor with KI-002 Table->Text reclassification"
```

---

## Task 8: DOMAssembler

**Files:**
- Create: `src/foundry_unify/pipeline/dom_assembler.py`
- Create: `tests/unit/test_pipeline_dom_assembler.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_pipeline_dom_assembler.py`:

```python
"""Tests for DOMAssembler."""

from typing import Any

import pytest

from foundry_unify.adapters.docling_serve_client import DoclingRawResponse
from foundry_unify.models.docling_dom import DoclingDOM
from foundry_unify.pipeline.dom_assembler import DOMAssembler


def _make_raw_response(pages: list[dict[str, Any]], **kwargs: Any) -> DoclingRawResponse:
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
    raw = _make_raw_response([
        {
            "page_no": 1,
            "items": [
                {"label": "Text", "text": "Hello world", "confidence": 0.95}
            ],
        }
    ])
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
    raw = _make_raw_response([
        {
            "page_no": 1,
            "items": [
                {"label": "Text", "text": "First"},
                {"label": "Text", "text": "Second"},
                {"label": "Table", "text": "table data"},
            ],
        }
    ])
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
    raw = _make_raw_response([
        {"page_no": 1, "items": [{"label": "Text", "text": "Page 1"}]},
        {"page_no": 2, "items": [{"label": "Text", "text": "Page 2"}]},
    ])
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
    raw = _make_raw_response([
        {"page_no": 1, "items": [{"label": "Text", "text": "a"}, {"label": "Text", "text": "b"}]},
    ])
    dom = DOMAssembler.assemble(
        raw_response=raw, document_id="d", trace_id="t",
        source_track="document", processing_tier="standard",
    )
    ids = [e.element_id for e in dom.pages[0].elements]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_pipeline_dom_assembler.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement DOMAssembler**

Create `src/foundry_unify/pipeline/dom_assembler.py`:

```python
"""DOMAssembler — converts a DoclingRawResponse into the canonical DoclingDOM schema."""

from __future__ import annotations

from typing import Any, Literal

from foundry_unify.adapters.docling_serve_client import DoclingRawResponse
from foundry_unify.models.docling_dom import DOMMetadata, DoclingDOM, ElementDOM, PageDOM


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
            source_track: "document" or "audio" — carried through to the output.
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

        raw_pages: list[dict[str, Any]] = raw_response.json_content.get("pages", [])
        pages = [
            DOMAssembler._assemble_page(page_data)
            for page_data in raw_pages
        ]

        layout_confidence = (
            1.0 if raw_response.success else 0.0
        )

        return DoclingDOM(
            document_id=document_id,
            trace_id=trace_id,
            source_track=source_track,
            processing_status="complete",
            pages=pages,
            metadata=DOMMetadata(
                processing_tier=processing_tier,
                layout_confidence=layout_confidence,
                ocr_applied=raw_response.ocr_applied,
                page_count=len(pages),
            ),
        )

    @staticmethod
    def _assemble_page(page_data: dict[str, Any]) -> PageDOM:
        page_no: int = page_data.get("page_no", 1)
        items: list[dict[str, Any]] = page_data.get("items", [])
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
        item: dict[str, Any], page_no: int, reading_order: int
    ) -> ElementDOM:
        return ElementDOM(
            element_id=f"p{page_no}-e{reading_order}",
            element_type=item.get("label", "Text"),
            text=item.get("text", ""),
            reading_order=reading_order,
            confidence=float(item.get("confidence", 1.0)),
            ocr_engine_provenance="docling-standard",
            is_parasitic=bool(item.get("is_parasitic", False)),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_pipeline_dom_assembler.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/pipeline/dom_assembler.py tests/unit/test_pipeline_dom_assembler.py
git commit -m "feat: add DOMAssembler converting Docling response to DoclingDOM"
```

---

## Task 9: GCSArtifactReader

**Files:**
- Create: `src/foundry_unify/adapters/gcs_client.py` (reader portion)
- Create: `tests/unit/test_adapters_gcs_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_adapters_gcs_client.py`:

```python
"""Tests for GCSArtifactReader and GCSArtifactWriter."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from foundry_unify.adapters.gcs_client import GCSArtifactReader, GCSArtifactWriter
from foundry_unify.core.exceptions import GCSError
from foundry_unify.models.docling_dom import DOMMetadata, DoclingDOM, PageDOM


def _make_metadata_json() -> str:
    return json.dumps({
        "document_id": "doc-001",
        "trace_id": "trace-abc",
        "source_track": "document",
        "num_pages": 2,
        "pdf_type": "born_digital",
        "processing_recommendation": {"tier": "standard"},
        "processing_version": {"version": "1.0"},
        "pages": [{"page_number": 1}, {"page_number": 2}],
    })


@pytest.fixture
def mock_gcs_client() -> MagicMock:
    return MagicMock()


@pytest.mark.unit
def test_reader_downloads_document_metadata(mock_gcs_client: MagicMock) -> None:
    mock_blob = MagicMock()
    mock_blob.download_as_text.return_value = _make_metadata_json()
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    reader = GCSArtifactReader(client=mock_gcs_client, bucket_template="rag-pipeline-{env}")
    meta = reader.download_document_metadata(env="dev", trace_id="trace-abc")

    assert meta.document_id == "doc-001"
    assert meta.source_track == "document"
    mock_gcs_client.bucket.assert_called_once_with("rag-pipeline-dev")


@pytest.mark.unit
def test_reader_constructs_correct_blob_path(mock_gcs_client: MagicMock) -> None:
    mock_blob = MagicMock()
    mock_blob.download_as_text.return_value = _make_metadata_json()
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    reader = GCSArtifactReader(client=mock_gcs_client, bucket_template="rag-pipeline-{env}")
    reader.download_document_metadata(env="staging", trace_id="trace-xyz")

    mock_gcs_client.bucket.return_value.blob.assert_called_once_with(
        "trace-xyz/01-preprocessed/DocumentMetadata.json"
    )


@pytest.mark.unit
def test_reader_raises_gcs_error_on_download_failure(mock_gcs_client: MagicMock) -> None:
    mock_gcs_client.bucket.return_value.blob.return_value.download_as_text.side_effect = (
        Exception("access denied")
    )
    reader = GCSArtifactReader(client=mock_gcs_client, bucket_template="rag-pipeline-{env}")

    with pytest.raises(GCSError) as exc_info:
        reader.download_document_metadata(env="dev", trace_id="trace-fail")

    assert "trace-fail" in exc_info.value.details.get("path", "")


@pytest.mark.unit
def test_writer_uploads_dom_to_correct_path(mock_gcs_client: MagicMock) -> None:
    mock_blob = MagicMock()
    mock_gcs_client.bucket.return_value.blob.return_value = mock_blob

    writer = GCSArtifactWriter(client=mock_gcs_client, bucket_template="rag-pipeline-{env}")
    dom = DoclingDOM(
        document_id="doc-1",
        trace_id="trace-1",
        source_track="document",
        pages=[],
        metadata=DOMMetadata(processing_tier="standard", page_count=0),
    )
    writer.write_docling_dom(dom=dom, env="prod", trace_id="trace-1")

    mock_gcs_client.bucket.assert_called_once_with("rag-pipeline-prod")
    mock_gcs_client.bucket.return_value.blob.assert_called_once_with(
        "trace-1/03-docling-dom/DoclingDOM.json"
    )
    mock_blob.upload_from_string.assert_called_once()
    uploaded = mock_blob.upload_from_string.call_args.kwargs.get(
        "data"
    ) or mock_blob.upload_from_string.call_args.args[0]
    data = json.loads(uploaded)
    assert data["document_id"] == "doc-1"


@pytest.mark.unit
def test_writer_raises_gcs_error_on_upload_failure(mock_gcs_client: MagicMock) -> None:
    mock_gcs_client.bucket.return_value.blob.return_value.upload_from_string.side_effect = (
        Exception("quota exceeded")
    )
    writer = GCSArtifactWriter(client=mock_gcs_client, bucket_template="rag-pipeline-{env}")
    dom = DoclingDOM(
        document_id="d",
        trace_id="t",
        source_track="document",
        pages=[],
        metadata=DOMMetadata(processing_tier="standard", page_count=0),
    )
    with pytest.raises(GCSError):
        writer.write_docling_dom(dom=dom, env="dev", trace_id="t")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_adapters_gcs_client.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement GCSArtifactReader and GCSArtifactWriter**

Create `src/foundry_unify/adapters/gcs_client.py`:

```python
"""GCS adapter — reads DocumentMetadata.json from 01-preprocessed/ and writes DoclingDOM.json.

Paths follow the canonical GCS layout:
  gs://rag-pipeline-{env}/{trace_id}/01-preprocessed/DocumentMetadata.json  (read)
  gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json          (write)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from foundry_unify.core.exceptions import GCSError
from foundry_unify.models.document_metadata import InboundDocumentMetadata
from foundry_unify.utils.structured_logging import get_logger

if TYPE_CHECKING:
    from google.cloud import storage as gcs_storage

logger = get_logger(__name__)


@dataclass
class GCSArtifactReader:
    """Downloads DocumentMetadata.json from the 01-preprocessed/ GCS path."""

    bucket_template: str = "rag-pipeline-{env}"
    client: Any = field(default=None, repr=False)

    def _get_client(self) -> Any:
        if self.client is None:
            from google.cloud import storage
            self.client = storage.Client()
        return self.client

    def download_document_metadata(
        self, env: str, trace_id: str
    ) -> InboundDocumentMetadata:
        """Download and parse DocumentMetadata.json for the given trace.

        Args:
            env: Deployment environment (dev, staging, prod).
            trace_id: Cloud Workflows trace identifier.

        Raises:
            GCSError: On any GCS access failure.
        """
        bucket_name = self.bucket_template.format(env=env)
        blob_path = f"{trace_id}/01-preprocessed/DocumentMetadata.json"
        gcs_path = f"gs://{bucket_name}/{blob_path}"

        logger.info("gcs_read_start", path=gcs_path)
        try:
            text = self._get_client().bucket(bucket_name).blob(blob_path).download_as_text()
        except Exception as exc:
            raise GCSError(
                f"Failed to download DocumentMetadata.json: {exc}",
                path=gcs_path,
            ) from exc

        return InboundDocumentMetadata.model_validate_json(text)


@dataclass
class GCSArtifactWriter:
    """Writes the assembled DoclingDOM.json to the 03-docling-dom/ GCS path."""

    bucket_template: str = "rag-pipeline-{env}"
    client: Any = field(default=None, repr=False)

    def _get_client(self) -> Any:
        if self.client is None:
            from google.cloud import storage
            self.client = storage.Client()
        return self.client

    def write_docling_dom(
        self,
        dom: Any,
        env: str,
        trace_id: str,
    ) -> str:
        """Serialize DoclingDOM to JSON and upload to GCS.

        Args:
            dom: Assembled DoclingDOM instance.
            env: Deployment environment.
            trace_id: Cloud Workflows trace identifier.

        Returns:
            Full GCS URI of the written artifact.

        Raises:
            GCSError: On upload failure.
        """
        bucket_name = self.bucket_template.format(env=env)
        blob_path = f"{trace_id}/03-docling-dom/DoclingDOM.json"
        gcs_path = f"gs://{bucket_name}/{blob_path}"

        json_bytes = dom.model_dump_json(indent=2).encode("utf-8")

        logger.info("gcs_write_start", path=gcs_path, bytes=len(json_bytes))
        try:
            blob = self._get_client().bucket(bucket_name).blob(blob_path)
            blob.upload_from_string(
                data=json_bytes,
                content_type="application/json",
            )
        except Exception as exc:
            raise GCSError(
                f"Failed to write DoclingDOM.json: {exc}",
                path=gcs_path,
            ) from exc

        logger.info("gcs_write_complete", path=gcs_path)
        return gcs_path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_adapters_gcs_client.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/adapters/gcs_client.py tests/unit/test_adapters_gcs_client.py
git commit -m "feat: add GCSArtifactReader and GCSArtifactWriter"
```

---

## Task 10: Health Endpoint — docling-serve Reachability Check

**Files:**
- Modify: `src/foundry_unify/api/health.py`
- Create: `tests/unit/test_api_health.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_api_health.py`:

```python
"""Tests for health endpoints including docling-serve reachability check."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from foundry_unify.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.unit
def test_liveness_returns_200(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.unit
def test_readiness_includes_docling_serve_check_when_reachable(
    client: TestClient,
) -> None:
    with patch(
        "foundry_unify.api.health.DoclingServeClient"
    ) as mock_cls:
        mock_instance = MagicMock()
        mock_instance.health_check.return_value = True
        mock_cls.return_value = mock_instance

        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert "docling_serve" in data["checks"]
    assert data["checks"]["docling_serve"]["status"] is True


@pytest.mark.unit
def test_readiness_returns_503_when_docling_serve_unreachable(
    client: TestClient,
) -> None:
    with patch(
        "foundry_unify.api.health.DoclingServeClient"
    ) as mock_cls:
        mock_instance = MagicMock()
        mock_instance.health_check.return_value = False
        mock_cls.return_value = mock_instance

        response = client.get("/health/ready")

    assert response.status_code == 503
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_api_health.py -v
```

Expected: `liveness` PASS, readiness tests FAIL (no docling_serve check yet).

- [ ] **Step 3: Update health.py to include docling-serve check**

In `src/foundry_unify/api/health.py`, add the import at the top:

```python
from foundry_unify.adapters.docling_serve_client import DoclingServeClient
from foundry_unify.core.config import settings
```

Replace the `readiness()` function body with:

```python
@router.get(
    "/ready",
    response_model=ReadinessStatus,
    responses={
        200: {"description": "Application is ready to serve traffic"},
        503: {"description": "Application is not ready (dependencies unavailable)"},
    },
    summary="Readiness probe",
    description="Checks if the application can serve traffic. Includes docling-serve reachability.",
)
async def readiness() -> ReadinessStatus:
    """Kubernetes readiness probe — checks docling-serve reachability."""
    checks: dict[str, ReadinessCheck] = {}

    # Check docling-serve
    start = time.time()
    client = DoclingServeClient(base_url=settings.docling_serve_url)
    reachable = client.health_check()
    checks["docling_serve"] = ReadinessCheck(
        name="docling_serve",
        status=reachable,
        latency_ms=round((time.time() - start) * 1000, 2),
        error=None if reachable else f"docling-serve unreachable at {settings.docling_serve_url}",
    )

    all_healthy = all(check.status for check in checks.values())

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unavailable",
                "timestamp": time.time(),
                "uptime_seconds": time.time() - _START_TIME,
                "checks": {name: check.model_dump() for name, check in checks.items()},
            },
        )

    return ReadinessStatus(
        status="ok",
        uptime_seconds=time.time() - _START_TIME,
        checks=checks,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_api_health.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/foundry_unify/api/health.py tests/unit/test_api_health.py
git commit -m "feat: add docling-serve reachability check to readiness endpoint"
```

---

## Task 11: POST /process Endpoint

**Files:**
- Create: `src/foundry_unify/api/process.py`
- Create: `tests/unit/test_api_process.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_api_process.py`:

```python
"""Tests for POST /process endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from foundry_unify.main import app
from foundry_unify.models.docling_dom import DOMMetadata, DoclingDOM, PageDOM


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_dom() -> DoclingDOM:
    return DoclingDOM(
        document_id="doc-1",
        trace_id="trace-abc",
        source_track="document",
        pages=[PageDOM(page_number=1, elements=[])],
        metadata=DOMMetadata(processing_tier="standard", page_count=1),
    )


@pytest.mark.unit
def test_process_returns_200_for_document_track(client: TestClient) -> None:
    with (
        patch("foundry_unify.api.process.GCSArtifactReader") as mock_reader_cls,
        patch("foundry_unify.api.process.DoclingServeClient") as mock_docling_cls,
        patch("foundry_unify.api.process.GCSArtifactWriter") as mock_writer_cls,
    ):
        mock_meta = MagicMock()
        mock_meta.source_track = "document"
        mock_meta.document_id = "doc-1"
        mock_meta.processing_status = "complete"
        mock_meta.docling_params = None
        mock_meta.processing_recommendation = MagicMock(tier="standard")

        mock_reader_cls.return_value.download_document_metadata.return_value = mock_meta

        mock_raw = MagicMock()
        mock_raw.success = True
        mock_raw.json_content = {"pages": [{"page_no": 1, "items": []}]}
        mock_raw.page_count = 1
        mock_raw.ocr_applied = True
        mock_raw.processing_time_ms = 500.0
        mock_raw.error = None
        mock_docling_cls.return_value.convert_file.return_value = mock_raw

        mock_writer_cls.return_value.write_docling_dom.return_value = (
            "gs://rag-pipeline-dev/trace-abc/03-docling-dom/DoclingDOM.json"
        )

        response = client.post(
            "/process",
            json={"trace_id": "trace-abc", "env": "dev", "source_track": "document"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-abc"
    assert "gcs_path" in data


@pytest.mark.unit
def test_process_returns_422_for_missing_source_track(client: TestClient) -> None:
    response = client.post(
        "/process",
        json={"trace_id": "trace-abc", "env": "dev"},
    )
    assert response.status_code == 422


@pytest.mark.unit
def test_process_returns_422_for_audio_track_in_b1(client: TestClient) -> None:
    """Audio track is not supported in B1 — returns 422 with NOT_IMPLEMENTED_YET."""
    with patch("foundry_unify.api.process.GCSArtifactReader") as mock_reader_cls:
        mock_meta = MagicMock()
        mock_meta.source_track = "audio"
        mock_reader_cls.return_value.download_document_metadata.return_value = mock_meta

        response = client.post(
            "/process",
            json={"trace_id": "trace-audio", "env": "dev", "source_track": "audio"},
        )

    assert response.status_code == 422
    assert "audio" in response.json()["detail"].lower()


@pytest.mark.unit
def test_process_returns_200_for_halted_document(client: TestClient) -> None:
    with (
        patch("foundry_unify.api.process.GCSArtifactReader") as mock_reader_cls,
        patch("foundry_unify.api.process.GCSArtifactWriter") as mock_writer_cls,
    ):
        mock_meta = MagicMock()
        mock_meta.source_track = "document"
        mock_meta.document_id = "doc-enc"
        mock_meta.processing_status = "halted"
        mock_meta.docling_params = None
        mock_meta.processing_recommendation = None
        mock_reader_cls.return_value.download_document_metadata.return_value = mock_meta
        mock_writer_cls.return_value.write_docling_dom.return_value = "gs://..."

        response = client.post(
            "/process",
            json={"trace_id": "trace-enc", "env": "dev", "source_track": "document"},
        )

    assert response.status_code == 200
    assert response.json()["processing_status"] == "halted"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_api_process.py -v
```

Expected: FAIL — `POST /process` route does not exist.

- [ ] **Step 3: Create the process endpoint**

Create `src/foundry_unify/api/process.py`:

```python
"""POST /process — Cloud Workflows entry point for Foundry Unify.

Receives {trace_id, env, source_track}, orchestrates OCR via docling-serve,
and writes DoclingDOM.json to GCS.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from foundry_unify.adapters.docling_serve_client import DoclingServeClient
from foundry_unify.adapters.gcs_client import GCSArtifactReader, GCSArtifactWriter
from foundry_unify.core.config import settings
from foundry_unify.core.exceptions import DoclingServiceError, GCSError, MissingSourceTrackError
from foundry_unify.pipeline.dom_assembler import DOMAssembler
from foundry_unify.pipeline.layout_postprocessor import LayoutPostprocessor
from foundry_unify.pipeline.tier_selector import ProcessingTier, TierSelector
from foundry_unify.utils.structured_logging import get_logger

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
    response_model=ProcessResponse,
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
            detail="audio track normalization is not implemented in B1 — coming in B2",
        )

    reader = GCSArtifactReader(
        bucket_template=settings.gcs_bucket_template,
    )
    writer = GCSArtifactWriter(
        bucket_template=settings.gcs_bucket_template,
    )

    try:
        metadata = reader.download_document_metadata(
            env=request.env, trace_id=request.trace_id
        )
    except GCSError as exc:
        log.error("gcs_read_failed", error=str(exc))
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
        gcs_path = writer.write_docling_dom(dom=dom, env=request.env, trace_id=request.trace_id)
        return ProcessResponse(
            trace_id=request.trace_id,
            document_id=metadata.document_id,
            processing_status="halted",
            processing_tier="standard",
            gcs_path=gcs_path,
        )

    docling_client = DoclingServeClient(
        base_url=settings.docling_serve_url,
        timeout=settings.docling_serve_timeout_seconds,
    )

    try:
        # B1: we send the whole-document file in one call.
        # Page images are referenced from GCS; for B1 we request JSON output only.
        import tempfile
        from pathlib import Path

        # #ASSUME: External Resources: for B1, we create a sentinel file to trigger
        # the docling API. Real page image download from GCS is wired in B2.
        # #VERIFY: Replace with actual GCS page image download before B1 gate.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 sentinel-for-b1")
            tmp_path = Path(tmp.name)

        raw = docling_client.convert_file(
            file_path=tmp_path,
            routing_params=metadata.docling_params,
        )
        tmp_path.unlink(missing_ok=True)
    except DoclingServiceError as exc:
        log.error("docling_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"docling-serve error: {exc}",
        ) from exc

    postprocessor = LayoutPostprocessor(
        confidence_threshold=settings.layout_confidence_threshold
    )
    pages = postprocessor.apply(raw.json_content.get("pages", []))
    # Patch processed pages back so DOMAssembler sees KI-002-corrected data
    import copy
    corrected_raw = copy.replace(raw, json_content={**raw.json_content, "pages": pages})

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
        log.error("gcs_write_failed", error=str(exc))
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


def _empty_raw_response() -> object:
    """Return a minimal DoclingRawResponse for halted documents."""
    from foundry_unify.adapters.docling_serve_client import DoclingRawResponse
    return DoclingRawResponse(
        success=False,
        json_content={},
        page_count=0,
        ocr_applied=False,
        processing_time_ms=0.0,
    )
```

> **Note on B1 sentinel file:** The `tempfile` workaround in Task 11 Step 3 is intentional. In B1, the GCS page-image download is not yet wired up. The sentinel PDF triggers the docling API code path for integration testing. Replace with real GCS image download before closing the B1 acceptance gate (see `#VERIFY` comment in the code).

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_api_process.py -v
```

Expected: All 4 tests PASS. (If `copy.replace` is unavailable on Python < 3.13, replace with a manual dataclass copy — see step below.)

**Fix for Python 3.10/3.11/3.12** — `copy.replace()` was added in 3.13. In `process.py`, replace the `copy.replace(raw, ...)` line with:

```python
from dataclasses import replace as dc_replace
corrected_raw = dc_replace(raw, json_content={**raw.json_content, "pages": pages})
```

- [ ] **Step 5: Register the process router in main.py**

In `src/foundry_unify/main.py`, add:

```python
from foundry_unify.api.process import router as process_router
```

And after `app.include_router(health_router)` add:

```python
app.include_router(process_router)
```

- [ ] **Step 6: Run all unit tests**

```bash
uv run pytest tests/unit/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/foundry_unify/api/process.py src/foundry_unify/main.py tests/unit/test_api_process.py
git commit -m "feat: add POST /process endpoint orchestrating OCR pipeline"
```

---

## Task 12: Integration Test Scaffold

**Files:**
- Create: `tests/integration/test_process_e2e.py`

- [ ] **Step 1: Create integration test harness**

Create `tests/integration/test_process_e2e.py`:

```python
"""Integration test harness for the POST /process endpoint.

These tests run against live docling-serve and GCS. They require:
  - FOUNDRY_UNIFY_DOCLING_SERVE_URL pointing to a reachable docling-serve instance
  - GCS credentials (ADC or GOOGLE_APPLICATION_CREDENTIALS)

Run with: uv run pytest -m integration tests/integration/

All 10 B1 acceptance criteria from PROJECT-PLAN.md Section B1 are tracked here.
Tests that require live infrastructure are marked skip_unless_live and skipped
in CI by default.
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
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_scanned_pdf_tables_recommends_vlm_assisted() -> None:
    """B1 acceptance: Scanned PDF with tables -> vlm_assisted tier recommended in output."""
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_handwritten_document_invokes_vlm_validated() -> None:
    """B1 acceptance: Handwritten document -> vlm_validated tier invoked and flagged."""
    pass


@pytest.mark.skip(reason="audio track not implemented in B1")
def test_audio_track_skips_ocr_and_normalizes_dom() -> None:
    """B1 acceptance: audio source_track -> OCR skipped, DOM normalized and written."""
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_watermarked_document_flags_watermark_as_parasitic() -> None:
    """B1 acceptance: Watermarked document -> watermark element flagged as is_parasitic."""
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_multi_page_document_all_pages_processed() -> None:
    """B1 acceptance: Multi-page document -> all pages present, reading order array present."""
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_corrupt_page_graceful_degradation() -> None:
    """B1 acceptance: Corrupt/partial-failure page -> layout_confidence=0, graceful."""
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_docling_routing_params_applied_to_convert_file() -> None:
    """B1 acceptance: DoclingRoutingParams.to_form_data() applied to /v1/convert/file."""
    pass


def test_missing_source_track_returns_422() -> None:
    """B1 acceptance: Missing source_track -> MISSING_SOURCE_TRACK 422 (unit-level)."""
    from fastapi.testclient import TestClient
    from foundry_unify.main import app

    client = TestClient(app)
    response = client.post("/process", json={"trace_id": "t", "env": "dev"})
    assert response.status_code == 422


@pytest.mark.skip(reason="audio track not implemented in B1")
def test_missing_docling_dom_in_audio_input_returns_422() -> None:
    """B1 acceptance: Missing docling_document in audio input -> MISSING_DOCLING_DOM 422."""
    pass


@pytest.mark.skip(reason="requires live docling-serve — run manually for B1 gate")
def test_get_health_returns_docling_serve_reachable() -> None:
    """B1 acceptance: GET /health/ready returns docling_serve: 'reachable' when up."""
    pass
```

- [ ] **Step 2: Run the integration marker (should collect but mostly skip)**

```bash
uv run pytest tests/integration/ -v --collect-only
```

Expected: 10 tests collected; 9 skipped, 1 (`test_missing_source_track_returns_422`) runnable.

```bash
uv run pytest tests/integration/test_process_e2e.py::test_missing_source_track_returns_422 -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_process_e2e.py
git commit -m "test: scaffold B1 integration test harness with 10 acceptance criteria"
```

---

## Task 13: Quality Gates and Final Polish

**Files:**
- Various (linting and type fixes only)

- [ ] **Step 1: Run full test suite with coverage**

```bash
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

Expected: Coverage >= 80%. If below, add targeted unit tests for any uncovered branches.

- [ ] **Step 2: Run Ruff linter and fix issues**

```bash
uv run ruff check . --fix
uv run ruff format .
```

Expected: Zero errors after fixes.

- [ ] **Step 3: Run BasedPyright type checker**

```bash
uv run basedpyright src/
```

Expected: Zero errors. Fix any type issues (common: `Any` imports, missing return types, Optional vs `| None`).

- [ ] **Step 4: Run Bandit security scanner**

```bash
uv run bandit -r src/
```

Expected: No HIGH or CRITICAL findings. The `# NOSONAR (S5332)` comment in the docling client suppresses the HTTP scheme warning for the private LAN service.

- [ ] **Step 5: Run pre-commit hooks**

```bash
pre-commit run --all-files
```

Expected: All hooks PASS, including `no-em-dash`.

- [ ] **Step 6: Final commit and summary**

```bash
git add -u
git commit -m "chore: pass all B1 quality gates (lint, types, coverage, security)"
```

---

## Self-Review: Spec Coverage Check

| B1 Deliverable | Task | Status |
|----------------|------|--------|
| `SourceTrackRouter` | Task 5 | Implemented |
| `GCSArtifactReader` | Task 9 | Implemented |
| `DoclingServeClient` | Task 4 | Implemented |
| `DoclingRoutingParams` form data | Task 3 | Implemented |
| `TierSelector` | Task 6 | Implemented |
| `LayoutPostprocessor` (KI-002) | Task 7 | Implemented |
| `DOMAssembler` | Task 8 | Implemented |
| `GCSArtifactWriter` | Task 9 | Implemented |
| `POST /process` endpoint | Task 11 | Implemented |
| `GET /health` docling-serve check | Task 10 | Implemented |
| Settings: docling_serve_url, timeout, threshold | Task 1 | Implemented |
| 80% unit test coverage | Task 13 | Gate |
| Integration test harness with 10 criteria | Task 12 | Scaffolded |

**Known gap flagged in plan:** The GCS page-image download in `POST /process` uses a sentinel PDF file in B1. The real image download must be wired before closing the B1 acceptance gate. The `#ASSUME` / `#VERIFY` comment in `process.py` marks this explicitly.

**Audio track in B1:** Detected and returns 422 `NOT_IMPLEMENTED_YET`. Full audio normalization (`AudioNormalizer`) is Phase B2.

---

## Execution

Plan saved. Two execution options:

**1. Subagent-Driven (recommended)** — Fresh subagent per task, two-stage review between tasks.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`.

Which approach?
