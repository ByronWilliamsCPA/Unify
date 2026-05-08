---
title: "Foundry Unify - Technical Specification"
schema_type: planning
status: published
owner: core-maintainer
purpose: "Document the technical architecture and implementation details."
tags:
  - planning
  - architecture
component: Development-Tools
source: "Handoff doc: foundry-unify-team-handoff.md + prepare-doc-unify-contract.md"
---

**Version:** 1.0.0 | **Status:** Published | **Last Updated:** 2026-05-05

---

## TL;DR

foundry-unify exposes a FastAPI service that accepts a pipeline trigger (trace ID + env),
reads upstream artifacts from GCS, routes to either a full Docling OCR pipeline
(document track) or a DOM passthrough normalizer (audio track), and writes
`DoclingDOM.json` back to GCS. The docling-serve HTTP API is the only external
dependency beyond GCS.

---

## Technology Stack

| Layer | Technology | Version | Notes |
| ------- | ---------- | ------- | ----- |
| Language | Python | 3.12 | UV package manager |
| API framework | FastAPI | >=0.120.1 | Async, Cloud Workflows compatible |
| Data validation | Pydantic v2 | >=2.0.0 | Strict mode; all I/O schemas modeled |
| Settings | pydantic-settings | >=2.0.0 | `.env` files, env vars |
| Logging | structlog | >=23.1.0 | JSON logs, correlation ID injection |
| GCS client | google-cloud-storage | latest | Read upstream artifacts, write DoclingDOM |
| HTTP client | httpx or requests | project choice | docling-serve REST calls |
| Type checking | BasedPyright | >=1.18.0 | Strict mode |
| Linting | Ruff | >=0.9.0 | 88-char line length, PyStrict-aligned |
| Containerization | Docker | latest | docker-compose for local dev |
| Testing | pytest + pytest-cov | >=7.4.0 | 80% coverage minimum |

**External dependencies (runtime):**

| Service | Endpoint | Purpose |
| ------- | -------- | ------- |
| docling-serve | `http://192.168.1.209:5001` | OCR orchestration via `/v1/convert/file` |
| GCS | `gs://rag-pipeline-{env}/` | Artifact storage |

---

## Component Architecture

```text
                        ┌─────────────────────────────────────────────┐
                        │              foundry-unify                  │
                        │                                             │
  Cloud Workflows ─────►│  POST /process                              │
  (trace_id, env)       │       │                                     │
                        │       ▼                                     │
                        │  GCSArtifactReader                          │
                        │  reads DocumentMetadata.json or             │
                        │  TranscriptMetadata.json from GCS           │
                        │       │                                     │
                        │       ▼                                     │
                        │  SourceTrackRouter                          │
                        │  reads source_track field                   │
                        │       │                                     │
                        │    ┌──┴───────────────────┐                │
                        │    │ document              │ audio          │
                        │    ▼                       ▼                │
                        │  DocumentPipeline    AudioNormalizer        │
                        │  ┌─────────────┐    (Phase B2)             │
                        │  │TierSelector │    DOM passthrough +       │
                        │  │standard/    │    schema normalization    │
                        │  │vlm_assisted/│                            │
                        │  │vlm_validated│                            │
                        │  └──────┬──────┘                            │
                        │         │                                   │
                        │  DoclingServeClient                         │
                        │  POST /v1/convert/file                      │◄── docling-serve
                        │  (DoclingRoutingParams applied)             │    192.168.1.209:5001
                        │         │                                   │
                        │  LayoutPostprocessor                        │
                        │  KI-002/KI-003 mitigations                  │
                        │  confidence thresholding                    │
                        │         │                                   │
                        │  DOMAssembler                               │
                        │  builds DoclingDOM.json                     │
                        │         │                                   │
                        │  GCSArtifactWriter                          │
                        │  writes 03-docling-dom/DoclingDOM.json      │
                        └─────────────────────────────────────────────┘
```

---

## Data Model

### Input: DocumentMetadata.json (document track)

Key fields Unify consumes from `01-preprocessed/`:

```python
# Canonical schema: image_detection/src/image_preprocessing_detector/schema.py
class DocumentMetadata:  # line 1249
    document_id: str
    trace_id: str
    source_track: Literal["document"]
    pdf_type: PDFType           # image_only | born_digital | hybrid
    processing_recommendation: ProcessingRecommendation
    quality_assessment: QualityAssessment
    pages: list[PageMetadata]
    docling_params: DoclingRoutingParams  # line 755, pre-computed Docling flags

class DoclingRoutingParams:  # line 755
    pipeline: Literal["standard", "vlm", "legacy"]
    vlm_model: str | None
    ocr_enabled: bool
    ocr_force: bool
    ocr_engine: Literal["auto", "rapidocr", "tesseract"]
    ocr_lang: str | None
    psm: int | None
    tables_enabled: bool
    table_mode: Literal["fast", "accurate"]
    enrich_code: bool
    enrich_formula: bool
    page_batch_size: int

    def to_cli_args(self) -> list[str]: ...  # Converts to docling-serve form params
```

#### to_cli_args() -> form-data mapping

`to_cli_args()` returns a flat list of CLI flag strings. Each flag becomes a
separate `options` form field in the multipart POST to `/v1/convert/file`:

```http
POST /v1/convert/file HTTP/1.1
Content-Type: multipart/form-data; boundary=----boundary

------boundary
Content-Disposition: form-data; name="files"; filename="page_001.png"
Content-Type: image/png

<binary image data>
------boundary
Content-Disposition: form-data; name="options"

--ocr-enabled
------boundary
Content-Disposition: form-data; name="options"

--tables-enabled
------boundary
Content-Disposition: form-data; name="options"

--table-mode=accurate
------boundary--
```

Each string from `to_cli_args()` is posted as its own `options` field. The
docling-serve server reassembles the list and parses it as CLI arguments to
the Docling pipeline.

### Input: TranscriptMetadata.json (audio track)

Key fields Unify consumes from `02-transcribed/`:

```python
class TranscriptMetadata:
    source_track: Literal["audio"]     # MUST be "audio"; absence = hard error
    document_id: str
    trace_id: str
    docling_document: dict             # Pre-assembled Docling DOM; use as-is
    transcription: TranscriptionData   # full_text absence = EMPTY_TRANSCRIPT error
    audio_quality: AudioQuality        # snr_db below threshold adds warning flag
```

### Output: DoclingDOM.json

Written to `gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json`.
Schema is identical for document-track and audio-track outputs:

```python
class DoclingDOM:
    document_id: str
    trace_id: str
    source_track: Literal["document", "audio"]
    metadata: ProcessingMetadata        # processing_tier, ocr_engines used
    pages: list[PageDOM]

class PageDOM:
    page_number: int
    elements: list[LayoutElement]
    reading_order: list[str]            # element_id sequence
    reading_order_confidence: float     # low values trigger fallback chunking in Chunk

class LayoutElement:
    element_id: str
    element_type: ElementType           # Title | SectionHeader | Text | Table | Figure | ...
    bbox_coco: list[float]              # [x, y, width, height]
    text: str | None
    ocr_engine_provenance: str | None   # which engine produced this text
    detector_confidence: float
    is_parasitic: bool                  # watermark / stamp / header / footer
    attributes: dict                    # element-type-specific metadata
```

---

## API Specification

### POST /process

Trigger pipeline processing for a single document.

```text
Request:
  Content-Type: application/json
  Body: { "trace_id": "...", "env": "dev|staging|prod" }

Response 200:
  { "trace_id": "...", "status": "complete", "output_path": "gs://..." }

Response 422:
  { "error": "MISSING_SOURCE_TRACK", "trace_id": "..." }

Response 500:
  { "error": "DOCLING_SERVE_UNAVAILABLE", "trace_id": "...", "detail": "..." }
```

### GET /health

```text
Response 200: { "status": "ok", "docling_serve": "reachable|unreachable" }
```

---

## Format Routing (Document Track)

Not all documents need OCR. Route based on `pdf_type` from `DocumentMetadata`:

| Document class | `pdf_type` | `ocr_enabled` | Action |
| -------------- | ---------- | ------------- | ------ |
| Born-digital, clean text | `born_digital` | `false` | Extract text layer directly |
| Born-digital, degraded | `born_digital` | `true` (ocr_force) | Force OCR |
| Scanned PDF | `image_only` | `true` | Full OCR on corrected images |
| Hybrid PDF | `hybrid` | per-page | Route per `page_type_map` |
| Native formats (DOCX, MD, HTML) | n/a | `false` | Route to Docling directly |
| Encrypted, halted | `image_only` + `halted` | n/a | Emit `processing_status: halted` |

All routing parameters are pre-computed in `DoclingRoutingParams`. Use
`docling_params.to_cli_args()` to convert to docling-serve form data.

---

## Processing Tiers

| Tier | Docling pipeline | VLM | When |
| ---- | ---------------- | --- | ---- |
| `standard` | `StandardPipeline` | No | DQS < 0.3, born-digital, simple layout |
| `vlm_assisted` | Docling + Granite VLM | On flagged regions | 0.3 <= DQS < 0.6 |
| `vlm_validated` | Docling + VLM in parallel | Cross-validated | DQS >= 0.6, handwriting, degraded |

VLM model: `ibm-granite/granite-docling-258M` (available via docling-serve VLM mode).

---

## Specialist OCR Routing (Phase B3)

| Element type | Engine | Selection |
| ------------ | ------ | --------- |
| `table` (simple_grid, financial) | `tableformer` | Default for grids |
| `table` (merged_header, nested, scientific) | `structeqtable` | Complex cells |
| `formula` (block, multi-line) | `texify` | Block-level math |
| `formula` (matrix, handwritten) | `unimernet` | Complex / handwritten |
| `formula` (simple inline) | `granite-docling` | Inline within text |
| `handwriting` | `trocr` | Default |
| `code_block` | `docling-standard` | Preserve formatting |

---

## Error Handling

| Error code | Trigger | Behavior |
| ---------- | ------- | -------- |
| `MISSING_SOURCE_TRACK` | `source_track` absent in TranscriptMetadata | Hard reject; 422 |
| `MISSING_DOCLING_DOM` | `docling_document` absent in audio input | Hard reject; 422 |
| `EMPTY_TRANSCRIPT` | `transcription.full_text` absent | Hard reject; 422 |
| `LAYOUT_DETECTION_FAILED` | Docling layout model fails | Degrade to full-page OCR; set `layout_confidence = 0` |
| `SPECIALIST_UNAVAILABLE` | Specialist OCR engine not reachable | Fallback to base engine; set `ocr_engine_fallback = true` |
| `DOCLING_SERVE_UNAVAILABLE` | docling-serve health check fails | 500; let Cloud Workflows retry |
| `AUDIO_QUALITY_LOW` | `snr_db` below threshold | Add quality warning to DoclingDOM; continue |

All errors include `trace_id` in the response body. Per-page failures degrade
gracefully; per-document failures reject with a structured error code.

---

## Known Issue Mitigations (Bake In from Day One)

### KI-002: Multi-column text misclassified as Table (HIGH)

Mitigation priority order:

1. **(Phase B1)** Per-class confidence threshold: reclassify Table detections below 0.5 confidence
2. **(Phase B3)** TableFormer gatekeeper: reclassify `TABLE -> TEXT` if no rows/cols detected
3. **(Phase B3)** Geometric heuristic: column-width uniformity check as last resort

### KI-003: Dense text/dark rendering misclassified as Picture (MEDIUM)

Mitigation **(Phase B4)**: VLM inspection on Picture elements; override to Text if VLM returns text. Requires `vlm_assisted` tier, which arrives in Phase B4.

### KI-008: KI-002 propagates through 5 Docling pipeline stages (HIGH)

Dependent on KI-002 fix. No additional mitigation needed if KI-002 is resolved.

---

## Security

- No external network calls except to configured docling-serve endpoint and GCS
- No page images or text content logged at INFO level; only hashed/redacted IDs
- Debug overlay images gated behind explicit config flag; excluded from default logs
- GCS access uses service account credentials; no static keys in code
- Dependencies scanned via `uv run pip-audit` on every CI run

---

## Observability

- **Structured JSON logs** via structlog with `trace_id`, `document_id`, `correlation_id`
- **Per-page metrics** logged: layout model version, OCR engine(s), latency breakdown
- **Prometheus metrics** (Phase B4): layout latency, OCR latency, throughput per worker
- **Debug overlays** (Phase B4): optional bounding box + reading order annotated images

---

## Configuration

```python
# src/foundry_unify/core/config.py
class Settings(BaseSettings):
    # GCS
    gcs_bucket_template: str = "rag-pipeline-{env}"
    gcs_credentials_path: str | None = None

    # docling-serve
    docling_serve_url: str = "http://192.168.1.209:5001"
    docling_serve_timeout_seconds: int = 300

    # Processing
    layout_confidence_threshold: float = 0.5
    table_confidence_threshold: float = 0.5

    # Observability
    log_level: str = "INFO"
    json_logs: bool = True
    debug_overlays_enabled: bool = False

    class Config:
        env_file = ".env"
```

---

## Reference

| File | Purpose |
| ---- | ------- |
| `image_detection/src/image_preprocessing_detector/schema.py:1249` | `DocumentMetadata` Pydantic class |
| `image_detection/src/image_preprocessing_detector/schema.py:755` | `DoclingRoutingParams` Pydantic class |
| `image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py` | HTTP client (copy-ready) |
| `image_detection/src/image_preprocessing_detector/routing/docling_router.py` | Routing logic reference |
| `docs/planning/adr/adr-001-docling-serve-http-integration.md` | Docling integration decision |
