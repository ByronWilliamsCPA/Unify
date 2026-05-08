---
title: "Foundry Unify - Project Plan"
schema_type: planning
status: published
owner: core-maintainer
purpose: "Synthesized project plan: phase branches, acceptance criteria, quality gates."
tags:
  - planning
  - project-plan
component: Strategy
---

**Version:** 1.0.0 | **Status:** Published | **Last Updated:** 2026-05-05

---

## Developer Quick-Start

Phase 0 (foundation) is complete. **Start on Phase B1.**

```bash
# Create your working branch
git checkout main && git pull origin main
git checkout -b feat/phase-b1-layout-ocr

# Verify tooling
uv run pytest           # should pass (template tests)
pre-commit run --all-files   # should pass

# Reference client to copy
cp <image_detection>/src/image_preprocessing_detector/text_extraction/docling_client.py \
   src/foundry_unify/adapters/docling_serve_client.py
```

First deliverable: `DoclingServeClient` wrapping `POST /v1/convert/file` wired into
a FastAPI `POST /process` endpoint that reads from GCS and writes `DoclingDOM.json`.

---

## Executive Summary

foundry-unify is Stage 3 of the six-service Foundry RAG pipeline. It receives
preprocessing artifacts from two upstream tracks (document OCR via foundry-prepare-doc,
audio transcription via foundry-prepare-audio), orchestrates OCR using the docling-serve
HTTP API, and writes a canonical `DoclingDOM.json` artifact to GCS for foundry-chunk.

The service is the unification layer that insulates foundry-chunk from knowing which
upstream track produced the content. Both tracks emit identical `DoclingDOM.json`
schemas. foundry-chunk reads that schema without caring about provenance.

The four implementation phases (B1 through B4) build incrementally: standard-tier
document OCR first, then audio passthrough and parasitic content, then specialist OCR
routing, and finally VLM tiers with production observability.

---

## Pipeline Position

```text
foundry-ingest
      |
      +-- audio/video --> foundry-prepare-audio --+
      |                                           |
      +-- documents   --> foundry-prepare-doc  ---+
                                                  |
                                         foundry-unify   <-- THIS SERVICE
                                                  |
                                         foundry-chunk
                                                  |
                                   per-application embedding
```

| Stage | GCS path | Direction |
|-------|----------|-----------|
| Preprocessed documents | `01-preprocessed/` | Unify reads |
| Transcribed audio | `02-transcribed/` | Unify reads |
| Docling DOM output | `03-docling-dom/` | Unify writes |

---

## Scope

### In Scope

- Source track detection and routing (document vs audio)
- Full OCR orchestration via docling-serve for the document track
- DOM passthrough normalization for the audio track (Phase B2)
- Three processing tiers: `standard`, `vlm_assisted`, `vlm_validated`
- Specialist OCR routing: TableFormer, StructEqTable, Texify, UniMERNet, TrOCR (Phase B3)
- Parasitic element detection and flagging: watermarks, stamps, headers, footers
- Per-page reading order with confidence scoring
- Writing `DoclingDOM.json` to GCS `03-docling-dom/`
- Graceful degradation with `layout_confidence = 0` signaling to foundry-chunk
- Prometheus metrics, structured logging, debug overlay images (Phase B4)

### Out of Scope

- Image quality assessment or pixel-space correction (owned by foundry-prepare-doc)
- DQS recalculation or `pre_ocr_risk` computation (upstream)
- OCR output fusion or hallucination filtering (downstream, foundry-chunk)
- RAG chunk creation or embedding (foundry-chunk / foundry-embed)
- Training or fine-tuning Docling layout models (separate MLOps concern)
- Direct ingestion of raw uploads (foundry-ingest responsibility)

---

## Architecture Overview

### Key Architectural Decisions

**ADR-001: Docling integration via docling-serve HTTP API (not Python library)**

Decision date: 2026-05-05. See `docs/planning/adr/adr-001-docling-serve-http-integration.md`
for the full record.

Rationale summary:
- docling-serve is already deployed and stable at `http://192.168.1.209:5001`
- GPU stays with docling-serve; foundry-unify container requires no GPU
- Standard vs VLM tier switching is a URL routing decision, not a code change
- A copy-ready HTTP client exists in `image_detection/src/.../docling_client.py`
- Phase B1 implementation risk is minimal compared to library integration

Consequences:
- Each page conversion adds one HTTP round-trip (mitigated by LAN latency)
- docling-serve is a runtime dependency; Cloud Workflows retry logic handles downtime
- Docling version upgrades are docling-serve's responsibility, not this service's

### Component Architecture

```text
                    +---------------------------------------------+
                    |             foundry-unify                   |
                    |                                             |
Cloud Workflows --> | POST /process                               |
(trace_id, env)     |      |                                      |
                    |      v                                      |
                    | GCSArtifactReader                           |
                    | reads DocumentMetadata.json or              |
                    | TranscriptMetadata.json from GCS            |
                    |      |                                      |
                    |      v                                      |
                    | SourceTrackRouter                           |
                    | reads source_track field                    |
                    |      |                                      |
                    |   +--+---------------------+               |
                    |   | document               | audio         |
                    |   v                        v               |
                    | DocumentPipeline     AudioNormalizer        |
                    | +-----------+        (Phase B2)            |
                    | |TierSelector|       DOM passthrough +      |
                    | |standard / |       schema normalization    |
                    | |vlm_assisted                               |
                    | |vlm_valid  |                               |
                    | +----+------+                               |
                    |      |                                      |
                    | DoclingServeClient                          |
                    | POST /v1/convert/file                       | <-- docling-serve
                    | (DoclingRoutingParams applied)              |     192.168.1.209:5001
                    |      |                                      |
                    | LayoutPostprocessor                         |
                    | KI-002/KI-003 mitigations                   |
                    | confidence thresholding                     |
                    |      |                                      |
                    | DOMAssembler                                |
                    | builds DoclingDOM.json                      |
                    |      |                                      |
                    | GCSArtifactWriter                           |
                    | writes 03-docling-dom/DoclingDOM.json       |
                    +---------------------------------------------+
```

### Schema Compatibility Constraint

The document track and audio track must produce identical `DoclingDOM.json` output
schemas. foundry-chunk reads that schema without knowing which track produced it.
Any `DoclingDOM.json` schema change must be coordinated with the foundry-chunk team.
This constraint is non-negotiable.

---

## Technology Stack

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
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

**Runtime external dependencies:**

| Service | Endpoint | Purpose |
|---------|----------|---------|
| docling-serve | `http://192.168.1.209:5001` | OCR orchestration via `/v1/convert/file` |
| GCS | `gs://rag-pipeline-{env}/` | Artifact storage (read upstream, write DOM) |

---

## Phased Development

### Phase 0: Foundation (Complete)

**Branch:** N/A - delivered by cookiecutter template on `main`

The repository scaffold is complete. All tooling is operational.

**What is already done:**

- Python 3.12 with UV package manager
- Ruff linting + BasedPyright strict type checking configured
- pytest with 80% coverage enforcement
- Docker + docker-compose
- GitHub Actions CI: tests, linting, security scans
- Pre-commit hooks: ruff, bandit, detect-secrets, no-em-dash
- MkDocs documentation site
- FastAPI skeleton with correlation middleware and structured logging

**Definition of done (met):** `pre-commit run --all-files` passes; CI is green;
`uv run pytest` executes without error.

---

### Phase B1: Layout and Basic OCR

**Branch:** `feat/phase-b1-layout-ocr`
**Duration estimate:** 3-4 weeks
**ADR reference:** ADR-001 (docling-serve HTTP integration)
**Depends on:** Phase 0 (complete)

**Goal:** End-to-end document processing for the `standard` tier. A born-digital PDF
enters via `POST /process`; a valid `DoclingDOM.json` exits to GCS. No VLM, no
specialist routing.

#### Create the branch

```bash
git checkout main && git pull origin main
git checkout -b feat/phase-b1-layout-ocr
```

#### Deliverables

- [ ] `SourceTrackRouter`: reads `source_track` field; raises `MISSING_SOURCE_TRACK` (422) if absent
- [ ] `GCSArtifactReader`: downloads `DocumentMetadata.json` + corrected page images from `01-preprocessed/`
- [ ] `DoclingServeClient`: wraps `POST /v1/convert/file` (adapt from `docling_client.py` in image_detection repo)
- [ ] `DoclingRoutingParams` integration: calls `metadata.docling_params.to_cli_args()` to build multipart form request
- [ ] `TierSelector`: reads `processing_recommendation.tier`; routes to standard Docling pipeline for `standard` tier
- [ ] `LayoutPostprocessor`: applies KI-002 per-class confidence threshold mitigation (reclassify Table detections below 0.5)
- [ ] `DOMAssembler`: converts Docling JSON response to `DoclingDOM.json` schema
- [ ] `GCSArtifactWriter`: writes to `gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json`
- [ ] FastAPI endpoints: `POST /process` and `GET /health` (health includes docling-serve reachability)
- [ ] Structured logging via structlog: `trace_id` and `document_id` present in every log line
- [ ] Settings: `docling_serve_url`, `docling_serve_timeout_seconds`, `layout_confidence_threshold` in `config.py`
- [ ] 80% unit test coverage; integration test harness scaffolded with `pytest -m integration` marker

#### Format routing in scope for B1

| Document class | `pdf_type` | Action |
|----------------|------------|--------|
| Born-digital, clean text | `born_digital` | Extract text layer directly (no OCR) |
| Born-digital, degraded | `born_digital` + `ocr_force: true` | Force OCR via docling-serve |
| Scanned PDF | `image_only` | Full OCR on corrected images |
| Encrypted / halted | `image_only` + `halted` | Emit `processing_status: halted`; no OCR |

#### Acceptance Criteria (gate for Phase B2)

All ten integration tests from handoff Section 14 must pass:

- [ ] Born-digital PDF -> `standard` tier -> DoclingDOM written to GCS; `source_track: "document"` in output
- [ ] Scanned PDF with tables -> `vlm_assisted` tier recommended; flagged in output metadata
- [ ] Watermarked document -> watermark element flagged as `is_parasitic: true`; excluded from chunk output
- [ ] Multi-page document -> all pages processed; reading order array present for each page
- [ ] Corrupt/partial-failure page -> graceful degradation; `reading_order_confidence` low; `layout_confidence = 0` set
- [ ] `DoclingRoutingParams.to_cli_args()` applied correctly as form data to `/v1/convert/file`
- [ ] Missing `source_track` in input -> `MISSING_SOURCE_TRACK` error returned with 422
- [ ] Missing `docling_document` in audio input -> `MISSING_DOCLING_DOM` error returned with 422
- [ ] Handwritten document -> `vlm_validated` tier invoked and flagged in output
- [ ] `GET /health` returns `docling_serve: "reachable"` when docling-serve is up

#### Quality Gates

| Gate | Threshold | Command |
|------|-----------|---------|
| Unit test coverage | >= 80% line coverage | `uv run pytest --cov=src --cov-fail-under=80` |
| Ruff lint | Zero errors | `uv run ruff check .` |
| BasedPyright | Zero errors (strict mode) | `uv run basedpyright src/` |
| Bandit | No HIGH or CRITICAL findings | `uv run bandit -r src` |
| Pre-commit | All hooks pass | `pre-commit run --all-files` |

**Performance target:** layout detection <= 100 ms/page on GPU (300 ms acceptable upper bound).

#### Known Issues to Mitigate in B1

- **KI-002** (HIGH): Multi-column text misclassified as `Table`. Mitigation: per-class
  confidence threshold in `LayoutPostprocessor`; reclassify Table detections below 0.5
  confidence to Text. This must ship with B1, not be bolted on later.
- **KI-008** (HIGH): Propagates from KI-002 through five Docling pipeline stages.
  Resolved by KI-002 fix; no additional mitigation.

---

### Phase B2: Parasitic Content and Advanced Reading Order

**Branch:** `feat/phase-b2-parasitic-reading-order`
**Duration estimate:** 2-3 weeks
**Depends on:** Phase B1 complete and all B1 acceptance criteria met

**Goal:** Correct reading order across complex layouts; flag and exclude parasitic elements;
normalize audio track DOM to the same `DoclingDOM.json` schema.

#### Deliverables

- [ ] `ParasiticDetector`: detects and flags headers, footers, page numbers, watermarks, stamps, signatures
- [ ] Parasitic element handling rules:
  - `watermark`: skip OCR entirely
  - `stamp`: OCR for metadata only
  - `page_header` / `page_footer`: OCR for metadata only; `is_parasitic: true`; excluded from RAG chunks
  - `signature`: flag for review; do not OCR
- [ ] `ReadingOrderGraph`: spatial graph construction with column-aware traversal
- [ ] `reading_order_confidence` float per page (signals fallback chunking in foundry-chunk when low)
- [ ] Cross-page coherence: ordered sequence allows foundry-chunk to reconstruct document-wide flow
- [ ] `AudioNormalizer`: DOM passthrough + schema normalization for audio track
  - Speaker turns -> `SectionItem` with `speaker_id`, `speaker_label`
  - Utterances -> `TextItem` with `start_ms`, `end_ms`, `confidence`, `playback_url`
  - Summary -> `SectionItem` with `is_summary: true` at DOM top
  - Low SNR warning flag added to `DoclingDOM` metadata if `snr_db` below threshold
- [ ] KI-003 mitigation: VLM inspection on `Picture` elements; override classification to `Text` if VLM returns text

#### Acceptance Criteria

- [ ] Audio input (`source_track: "audio"`) -> OCR skipped; DOM normalized; written to GCS
- [ ] `DoclingDOM.json` from audio track passes schema validation against document-track schema
- [ ] Reading order pairwise F1 >= 0.85 on evaluation set
- [ ] All parasitic element types flagged with `is_parasitic: true` and excluded from `pages[].elements[]` for chunk output
- [ ] `reading_order_confidence` present on every page in output

#### Quality Gates

Same as Phase B1 plus:

| Gate | Threshold | Command |
|------|-----------|---------|
| Unit test coverage | >= 80% | `uv run pytest --cov=src --cov-fail-under=80` |
| B1 integration tests | All still pass | `uv run pytest -m integration` |
| Audio track schema | Identical to document track | Schema validation test |

---

### Phase B3: Tables, Structured Regions, Specialist Routing

**Branch:** `feat/phase-b3-specialist-routing`
**Duration estimate:** 3-4 weeks
**Depends on:** Phase B2 complete and all B2 acceptance criteria met

**Goal:** Full specialist OCR dispatch. TableFormer, StructEqTable, Texify, UniMERNet,
and TrOCR routing based on `specialist_routing` recommendations from foundry-prepare-doc.

#### Deliverables

- [ ] `SpecialistRouter`: maps element type + classifier output to OCR engine
- [ ] TableFormer integration: `table` elements with `simple_grid` or `financial` classification
- [ ] StructEqTable integration: `table` elements with `merged_header`, `nested_rows`, or `scientific` classification
- [ ] Texify integration: `formula` elements with `block` or `multi_line` classification
- [ ] UniMERNet integration: `formula` elements with `matrix` or `handwritten` classification
- [ ] TrOCR integration: `handwriting` elements
- [ ] `ocr_engine_fallback: true` flag on elements where specialist engine is unreachable; logs the fallback clearly
- [ ] Figure-caption linking: `Figure` elements linked to their caption `Text` elements in DOM
- [ ] Footnote linking: footnote markers in body text linked to footnote `Text` elements
- [ ] ONNX model registry: load five Prepare-Doc classifiers from GCS at `gs://image_detection_b/models/phase9/`
  - `doclayout_yolo_extended` (17 classes)
  - `handwriting_classifier`
  - `table_type_classifier`
  - `formula_complexity_classifier`
  - `parasitic_detector`
- [ ] `full` (GPU) and `light` (CPU) model variants switchable via `MODEL_VARIANT` config setting
- [ ] KI-002 B3 mitigations: TableFormer gatekeeper (reclassify TABLE -> TEXT if no rows/cols detected); geometric heuristic fallback

#### Specialist OCR Routing Table

| Element type | Classifier output | Engine |
|--------------|-------------------|--------|
| `table` | `simple_grid`, `financial` | TableFormer |
| `table` | `merged_header`, `nested`, `scientific` | StructEqTable |
| `formula` | `block`, `multi_line` | Texify |
| `formula` | `matrix`, `handwritten` | UniMERNet |
| `formula` | `simple_inline` | granite-docling (via docling-serve) |
| `handwriting` | any | TrOCR |
| `code_block` | any | docling-standard |

#### Acceptance Criteria

- [ ] Table structure TEDS >= 0.90 on evaluation set
- [ ] OCR WER improvement >= 10% relative over baseline single-engine OCR
- [ ] Specialist engine fallback exercised in tests; confirmed safe (no hard failure)
- [ ] All B1 and B2 integration tests still pass

#### Quality Gates

Same as Phase B2 plus:

| Gate | Threshold | Command |
|------|-----------|---------|
| Unit test coverage | >= 80% | `uv run pytest --cov=src --cov-fail-under=80` |
| ONNX model load | All five models loadable from GCS | Integration test |
| Specialist fallback | `ocr_engine_fallback` path tested | Unit test per engine |

---

### Phase B4: Tier Routing, Optimization, Hardening

**Branch:** `feat/phase-b4-vlm-observability`
**Duration estimate:** 3-4 weeks
**Depends on:** Phase B3 complete and all B3 acceptance criteria met

**Goal:** VLM tiers fully operational; production-grade observability; load tested;
full integration test suite passes against live docling-serve and GCS staging.

#### Deliverables

- [ ] `vlm_assisted` tier: Docling + `ibm-granite/granite-docling-258M` VLM on flagged regions
- [ ] `vlm_validated` tier: Docling and VLM run in parallel; results cross-validated
- [ ] Batch processing mode (many pages) and streaming mode (page-by-page)
- [ ] Prometheus metrics: layout latency, OCR latency, throughput per worker
- [ ] Debug overlay images: bounding boxes + labels + reading order indices (gated by `debug_overlays_enabled` config flag)
- [ ] Load testing: >= 3-5 pages/second sustained throughput per worker under load
- [ ] Layout mAP@0.50 >= 0.82 measured on DocLayNet evaluation set
- [ ] Full integration tests against live docling-serve and GCS staging environment
- [ ] Graceful degradation confirmed: layout detection failure -> full-page OCR + `layout_confidence = 0`
- [ ] KI-003 final mitigation: VLM inspection on `Picture` elements with text override (requires `vlm_assisted` tier)

#### Acceptance Criteria

- [ ] All Phase B1, B2, B3 integration tests still pass
- [ ] `vlm_assisted` tier produces valid `DoclingDOM.json` with VLM provenance in `ocr_engine_provenance`
- [ ] `vlm_validated` tier produces valid `DoclingDOM.json`; cross-validation disagreements logged
- [ ] Throughput target (>= 3 pages/second per worker) met under 10-minute sustained load test
- [ ] Layout mAP@0.50 >= 0.82 confirmed on DocLayNet evaluation set
- [ ] No HIGH or CRITICAL findings in `pip-audit` or `bandit` at release
- [ ] Prometheus metrics endpoint reachable; latency and throughput histograms populated

#### Quality Gates

| Gate | Threshold | Command |
|------|-----------|---------|
| Unit test coverage | >= 80% | `uv run pytest --cov=src --cov-fail-under=80` |
| Full integration suite | All pass | `uv run pytest -m integration` |
| Load test | >= 3 pages/second sustained | Load test script (to be authored in B4) |
| pip-audit | No HIGH/CRITICAL | `uv run pip-audit` |
| Bandit | No HIGH/CRITICAL | `uv run bandit -r src` |
| Pre-commit | All hooks pass | `pre-commit run --all-files` |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| KI-002 confidence threshold insufficient | Medium | HIGH | Ship threshold in B1; validate on real corpus before closing B1 gate; B3 TableFormer gatekeeper is second line of defense |
| KI-008 propagation not fully resolved by KI-002 fix | Medium | HIGH | Integration tests must cover multi-column document class explicitly |
| docling-serve VLM mode unstable in B4 | Medium | Medium | B4 only; degrade gracefully to `standard` tier if VLM endpoint unavailable |
| Specialist OCR engines not reachable | Low | Medium | `ocr_engine_fallback` flag; fallback to base engine; no hard failure |
| Audio track DOM schema changes in foundry-prepare-audio | Low | Medium | Pin to contract version; raise GitHub issue if upstream changes; AudioNormalizer version-gates schema |
| GCS latency spikes during batch processing | Low | Low | Timeout config per operation; Cloud Workflows retry logic handles transient failures |
| DoclingDOM schema change coordination failure | Low | HIGH | Any schema change requires explicit sign-off from foundry-chunk team before merge |

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| B1 | Layout mAP@0.50 (DocLayNet classes) | >= 0.82 |
| B1 | `DoclingDOM.json` written to GCS for standard-tier documents | 100% of born-digital PDFs |
| B2 | Reading order pairwise F1 | >= 0.85 |
| B3 | Table structure TEDS | >= 0.90 |
| B3 | OCR WER improvement over baseline | >= 10% relative |
| All | Layout detection latency (GPU) | <= 100 ms/page (300 ms acceptable) |
| All | OCR latency (average complexity) | <= 300 ms/page (800 ms acceptable) |
| All | Throughput per worker | >= 3-5 pages/second |

Phase B1 gate: all 10 integration tests from handoff Section 14 pass, including
born-digital PDF standard-tier and audio track passthrough.

---

## Definition of Done (All Phases)

The following must be met before any phase is considered closed:

- All deliverable checkboxes ticked
- Phase-specific acceptance criteria met and verified
- `uv run pytest --cov=src --cov-fail-under=80` passes
- `uv run ruff check .` passes with zero errors
- `uv run basedpyright src/` passes with zero errors
- `uv run bandit -r src` reports no HIGH or CRITICAL findings
- `pre-commit run --all-files` passes
- Planning docs updated to reflect any scope changes discovered during the phase

---

## Phase 0 Environment Setup Checklist

Complete these before starting Phase B1 work:

- [ ] Clone repo and run `uv sync --all-extras`
- [ ] Run `uv run pre-commit install` to activate hooks
- [ ] Confirm `uv run pytest` passes (template tests)
- [ ] Confirm `pre-commit run --all-files` passes
- [ ] Verify access to docling-serve: `curl http://192.168.1.209:5001/health`
- [ ] Verify GCS credentials configured (service account key or ADC)
- [ ] Copy `docling_client.py` from image_detection repo to `src/foundry_unify/adapters/docling_serve_client.py`
- [ ] Read `DocumentMetadata` schema: `image_detection/src/image_preprocessing_detector/schema.py:1249`
- [ ] Read `DoclingRoutingParams` schema: `image_detection/src/image_preprocessing_detector/schema.py:755`
- [ ] Read team handoff Section 14 for the 10 integration test cases
- [ ] Read `DOCLING-API-CONTRACT.md` in `homelab-infra/docs/planning/contracts/`
- [ ] Create feature branch: `git checkout -b feat/phase-b1-layout-ocr`

---

## Reference Documents

| Document | Location |
|----------|----------|
| Project Vision and Scope | `docs/planning/project-vision.md` |
| Technical Specification | `docs/planning/tech-spec.md` |
| Development Roadmap | `docs/planning/roadmap.md` |
| ADR-001: Docling HTTP integration | `docs/planning/adr/adr-001-docling-serve-http-integration.md` |
| Team handoff (full context) | `image_detection/docs/development/RAG Pipeline/foundry-unify-team-handoff.md` |
| Prepare-Doc -> Unify contract | `image_detection/docs/development/RAG Pipeline/prepare-doc-unify-contract.md` |
| Prepare-Audio -> Unify contract | `image_detection/docs/development/RAG Pipeline/prepare-audio-unify-contract.md` |
| Unify -> Chunk contract | `image_detection/docs/development/RAG Pipeline/chunk-embed-contract.md` |
| F/NF requirements | `image_detection/docs/_archived/cross-project/unify-f-nf.md` |
| DocumentMetadata schema | `image_detection/src/image_preprocessing_detector/schema.py:1249` |
| DoclingRoutingParams schema | `image_detection/src/image_preprocessing_detector/schema.py:755` |
| Reference HTTP client | `image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py` |
| Known issue: KI-002 | `image_detection/docs/known_issues/KI-002-*.md` |
| Known issue: KI-003 | `image_detection/docs/known_issues/KI-003-*.md` |
| Known issue: KI-008 | `image_detection/docs/known_issues/KI-008-*.md` |

---

**Last Updated:** 2026-05-05
**Generated by:** Project Plan Synthesizer
**Source documents:** project-vision.md v1.0.0, tech-spec.md v1.0.0, roadmap.md v1.0.0, ADR-001 v1.0.0
