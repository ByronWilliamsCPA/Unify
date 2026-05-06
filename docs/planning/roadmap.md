---
title: "Foundry Unify - Development Roadmap"
schema_type: planning
status: published
owner: core-maintainer
purpose: "Document the phased implementation plan and milestones."
tags:
  - planning
  - roadmap
component: Strategy
source: "Handoff doc: foundry-unify-team-handoff.md + unify-f-nf.md"
---

**Version:** 1.0.0 | **Status:** Published | **Last Updated:** 2026-05-05

---

## TL;DR

Four implementation phases (B1 through B4) aligned to the F/NF requirements doc.
Phase B1 is the current target: document track, standard tier, born-digital PDFs,
`DoclingDOM.json` written to GCS. Audio track and specialist OCR routing follow
in B2 and B3. VLM tiers and production hardening are B4.

---

## Phase Overview

| Phase | Name | Key deliverable | Estimated duration |
| ----- | ---- | --------------- | ------------------ |
| Phase 0 | Foundation | Repo, CI/CD, dev environment | Complete (template) |
| Phase B1 | Layout and Basic OCR | DoclingDOM.json for standard-tier documents | 3-4 weeks |
| Phase B2 | Parasitic Content and Advanced Reading Order | Audio track + reading order confidence | 2-3 weeks |
| Phase B3 | Tables, Structured Regions, Specialist Routing | Full OCR specialist dispatch | 3-4 weeks |
| Phase B4 | Tier Routing, Optimization, Hardening | VLM tiers + observability + integration tests | 3-4 weeks |

---

## Phase 0: Foundation (Complete)

Repository scaffolded from cookiecutter-python-template. All tooling operational.

**Already done:**

- Python 3.12 with UV package manager
- Ruff linting + BasedPyright strict type checking
- pytest with 80% coverage enforcement
- Docker + docker-compose
- GitHub Actions CI: tests, linting, security scans
- Pre-commit hooks (ruff, bandit, detect-secrets, no-em-dash)
- MkDocs documentation site

**Definition of done:** pre-commit passes, CI green, `uv run pytest` executes.

---

## Phase B1: Layout and Basic OCR (Start Here)

**Goal:** End-to-end document processing for the `standard` tier. A born-digital PDF
enters; a valid `DoclingDOM.json` exits to GCS. No VLM, no specialist routing.

### B1 Deliverables

- [ ] `SourceTrackRouter`: reads `source_track`; raises `MISSING_SOURCE_TRACK` if absent
- [ ] `GCSArtifactReader`: downloads `DocumentMetadata.json` + corrected page images
- [ ] `DoclingServeClient`: wraps `POST /v1/convert/file` (adapt from `docling_client.py`)
- [ ] `DoclingRoutingParams` integration: calls `docling_params.to_cli_args()` to build request
- [ ] `TierSelector`: reads `processing_recommendation.tier`; routes to standard Docling pipeline
- [ ] `LayoutPostprocessor`: applies KI-002 per-class confidence threshold mitigation
- [ ] `DOMAssembler`: builds `DoclingDOM.json` from Docling response
- [ ] `GCSArtifactWriter`: writes to `03-docling-dom/DoclingDOM.json`
- [ ] FastAPI service: `POST /process`, `GET /health`
- [ ] Structured logging with `trace_id` and `document_id` in every log line
- [ ] 80% unit test coverage; integration test harness scaffolded

### Format routing (B1 scope)

- Born-digital PDF, clean text layer: skip OCR, extract text layer
- Born-digital PDF, degraded: force OCR via `ocr_force: true`
- Scanned PDF (`image_only`): full OCR on corrected images
- Encrypted / halted: emit `DoclingDOM.json` with `processing_status: halted`

### B1 success criteria (gate for Phase B2)

All ten integration tests from handoff Section 14 must pass:

- [ ] Born-digital PDF -> `standard` tier -> DoclingDOM written to GCS
- [ ] Scanned PDF with tables -> `vlm_assisted` tier recommended (flagged in output)
- [ ] Watermarked document -> watermark element flagged, excluded from chunk output
- [ ] Multi-page document -> all pages processed, reading order correct
- [ ] Corrupt/partial-failure page -> graceful degradation, `layout_confidence` flagged low
- [ ] `DoclingRoutingParams.to_cli_args()` applied correctly to Docling configuration
- [ ] Missing `source_track` -> `MISSING_SOURCE_TRACK` error
- [ ] Missing `docling_document` in audio input -> `MISSING_DOCLING_DOM` error
- [ ] Handwritten document -> `vlm_validated` tier invoked (flagged in output)

**Performance target:** layout detection <= 100 ms/page on GPU, <= 300 ms acceptable.

---

## Phase B2: Parasitic Content and Advanced Reading Order

**Goal:** Correct reading order across complex layouts; flag parasitic elements;
normalize audio track DOM to the same `DoclingDOM.json` schema.

### B2 Deliverables

- [ ] `ParasiticDetector`: detects and flags page headers, footers, page numbers, watermarks,
  stamps, signatures across pages
- [ ] Parasitic element handling:

  - `watermark`: skip OCR entirely
  - `stamp`: OCR for metadata only
  - `page_header` / `page_footer`: OCR for metadata only; exclude from RAG chunks
  - `signature`: flag for review; do not OCR

- [ ] `ReadingOrderGraph`: spatial graph construction with column-aware traversal
- [ ] `reading_order_confidence` float per page (signals fallback chunking in foundry-chunk)
- [ ] Cross-page coherence: ordered sequence allows foundry-chunk to reconstruct document-wide flow
- [ ] `AudioNormalizer`: DOM passthrough + schema normalization for audio track

  - Speaker turns -> `SectionItem` with `speaker_id`, `speaker_label`
  - Utterances -> `TextItem` with `start_ms`, `end_ms`, `confidence`, `playback_url`
  - Summary -> `SectionItem` with `is_summary: true` at DOM top
  - Low SNR warning flag added to DoclingDOM if `snr_db` below threshold

- [ ] KI-003 mitigation: VLM inspection on Picture elements; override if VLM returns text

### B2 success criteria

- [ ] Audio input (`source_track: "audio"`) -> OCR skipped, DOM normalized and written to GCS
- Reading order pairwise F1 >= 0.85
- Audio track produces valid `DoclingDOM.json` (schema identical to document track)
- All parasitic element types flagged and excluded from `pages[].elements[]` for chunk output

---

## Phase B3: Tables, Structured Regions, Specialist Routing

**Goal:** Full specialist OCR dispatch. TableFormer, StructEqTable, Texify, UniMERNet,
TrOCR routing based on `specialist_routing` recommendations from Prepare-Doc.

### B3 Deliverables

- [ ] `SpecialistRouter`: maps element type + table/formula classifier to OCR engine
- [ ] TableFormer integration (simple_grid, financial tables)
- [ ] StructEqTable integration (merged_header, nested_rows, scientific tables)
- [ ] Texify integration (block equations, multi-line formulas)
- [ ] UniMERNet integration (matrix, handwritten math)
- [ ] TrOCR integration (handwriting)
- [ ] `ocr_engine_fallback = true` flag when specialist unavailable; logs clearly
- [ ] Figure-caption linking
- [ ] Footnote linking
- [ ] ONNX model registry integration: load five Prepare-Doc classifiers from GCS
  (`gs://image_detection_b/models/phase9/`)

  - `doclayout_yolo_extended` (17 classes)
  - `handwriting_classifier`
  - `table_type_classifier`
  - `formula_complexity_classifier`
  - `parasitic_detector`

- [ ] `full` (GPU) and `light` (CPU) model variants switchable via config

### B3 success criteria

- Table structure TEDS >= 0.90 on evaluation set
- OCR WER improvement >= 10% relative over baseline single-engine OCR
- Specialist fallback tested and confirmed safe

---

## Phase B4: Tier Routing, Optimization, Hardening

**Goal:** VLM tiers operational; production-grade observability; integration tested
against both upstream tracks.

### B4 Deliverables

- [ ] `vlm_assisted` tier: Docling + `ibm-granite/granite-docling-258M` VLM on flagged regions
- [ ] `vlm_validated` tier: Docling and VLM in parallel; cross-validated results
- [ ] Batch processing mode (many pages) and streaming mode (page-by-page)
- [ ] Prometheus metrics: layout latency, OCR latency, throughput per worker
- [ ] Debug overlay images: bounding boxes + labels + reading order indices (gated by config)
- [ ] Load testing: >= 3-5 pages/second sustained throughput per worker
- [ ] Layout mAP@0.50 >= 0.82 measured on DocLayNet evaluation set
- [ ] Full integration tests against live docling-serve and GCS staging environment
- [ ] Graceful degradation confirmed: layout failure -> full-page OCR + `layout_confidence = 0`

### B4 success criteria

- All Phase B1-B3 integration tests still pass
- `vlm_assisted` and `vlm_validated` tiers produce valid `DoclingDOM.json`
- Throughput target met under sustained load
- No high/critical findings in `pip-audit` or `bandit`

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| KI-002 mitigation insufficient | Medium | HIGH | Ship per-class threshold first; gate B3 on KI-002 validated |
| docling-serve VLM mode unstable | Medium | Medium | B4 only; degrade to standard tier if unavailable |
| Specialist OCR engines not reachable | Low | Medium | `ocr_engine_fallback` flag; logged clearly; no hard failure |
| Audio track DOM schema changes in Prepare-Audio | Low | Medium | Pin to contract version; raise GitHub issue if upstream changes |
| GCS latency spikes | Low | Low | Timeout config; Cloud Workflows retries handle transient failures |

---

## Definition of Done (All Phases)

- All deliverable checkboxes ticked
- Phase-specific success criteria met
- `uv run pytest --cov=src --cov-fail-under=80` passes
- `uv run ruff check .` passes with zero errors
- `uv run basedpyright src/` passes with zero errors
- `uv run bandit -r src` reports no high/critical findings
- `pre-commit run --all-files` passes
- Planning docs updated to reflect any scope changes

---

## Related Documents

| Document | Location |
| -------- | -------- |
| Project Vision and Scope | `docs/planning/project-vision.md` |
| Technical Specification | `docs/planning/tech-spec.md` |
| ADR-001: Docling HTTP integration | `docs/planning/adr/adr-001-docling-serve-http-integration.md` |
| F/NF requirements (source) | `image_detection/docs/_archived/cross-project/unify-f-nf.md` |
| Integration test checklist | `image_detection/docs/development/RAG Pipeline/foundry-unify-team-handoff.md` Section 14 |
