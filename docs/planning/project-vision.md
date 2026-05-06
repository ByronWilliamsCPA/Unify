---
title: "Foundry Unify - Project Vision & Scope"
schema_type: planning
status: published
owner: core-maintainer
purpose: "Document the project vision, scope, and success criteria."
tags:
  - planning
  - scope
component: Strategy
source: "Handoff doc: foundry-unify-team-handoff.md + unify-f-nf.md"
---

**Version:** 1.0.0 | **Status:** Published | **Last Updated:** 2026-05-05

---

## TL;DR

foundry-unify is Stage 3 of the six-service Foundry RAG pipeline. It receives preprocessing
artifacts from two radically different upstream tracks (document OCR and audio transcription),
normalizes them through OCR orchestration via Docling, and writes a single `DoclingDOM.json`
artifact to GCS that foundry-chunk can consume without knowing which track produced it.

---

## Pipeline Position

```text
foundry-ingest
      │
      ├── audio/video ──► foundry-prepare-audio ──┐
      │                                            │
      └── documents ────► foundry-prepare-doc ─────┤
                                                   │
                                          foundry-unify   ← THIS SERVICE
                                                   │
                                          foundry-chunk
                                                   │
                                    per-application embedding
```

**GCS artifact paths:**

| Stage | Path | Direction |
| ------- | ------ | ----------- |
| Preprocessed documents | `01-preprocessed/` | Unify reads |
| Transcribed audio | `02-transcribed/` | Unify reads |
| **Docling DOM output** | **`03-docling-dom/`** | **Unify writes** |

---

## Problem Statement

The Foundry RAG pipeline ingests two fundamentally different content types: scanned and
digital documents (requiring OCR) and audio/video files (producing transcripts). Both
must feed the same downstream chunking and embedding pipeline. Without a unification
layer, foundry-chunk would need to understand two incompatible input schemas and two
different OCR strategies. That coupling is unacceptable in a microservice pipeline.

**Why it is important now:** foundry-prepare-doc is operational and delivering
`DocumentMetadata.json` with pre-computed `DoclingRoutingParams`. foundry-chunk is
designed around `DoclingDOM.json`. The missing link is foundry-unify.

---

## Core Capabilities (MVP = Phase B1)

1. **Source track detection** - Read `source_track` field; branch to document-OCR or
   audio-passthrough code path. Missing `source_track` is a hard error.

2. **Document-track OCR orchestration** - Apply pre-computed `DoclingRoutingParams`
   from `DocumentMetadata.json` to docling-serve HTTP API; process corrected page images.

3. **Three-tier processing** - Route to `standard`, `vlm_assisted`, or `vlm_validated`
   Docling pipeline based on `processing_recommendation.tier` from upstream.

4. **DoclingDOM assembly** - Assemble per-page layout elements, reading order, bounding
   boxes, OCR provenance, and quality signals into the canonical `DoclingDOM.json` schema.

5. **GCS write** - Persist output to
   `gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json`.

---

## Target Users

This is an internal pipeline service. Consumers are:

- **foundry-chunk** (downstream, reads `DoclingDOM.json`)
- **Pipeline operators** (monitoring, observability, debug overlays)
- **foundry-prepare-doc team** (upstream contract owners, raises GitHub issues here)

---

## Scope Definition

### In Scope

- Source track detection and routing
- Full OCR orchestration via docling-serve for document track
- DOM passthrough normalization for audio track (Phase B2)
- Three processing tiers: standard, vlm\_assisted, vlm\_validated
- Specialist OCR routing (TableFormer, StructEqTable, Texify, UniMERNet, TrOCR) (Phase B3)
- Parasitic element detection and flagging (watermarks, stamps, headers, footers)
- Per-page reading order with confidence scoring
- Writing `DoclingDOM.json` to GCS `03-docling-dom/`
- Graceful degradation with `layout_confidence` low signaling to foundry-chunk
- Prometheus metrics, structured logging, debug overlay images (Phase B4)

### Out of Scope

- Image quality assessment or pixel-space correction (owned by foundry-prepare-doc)
- DQS recalculation or `pre_ocr_risk` computation (upstream)
- OCR output fusion or hallucination filtering (downstream, foundry-chunk)
- RAG chunk creation or embedding (foundry-chunk / foundry-embed)
- Training or fine-tuning Docling layout models (separate MLOps concern)
- Direct ingestion of raw uploads (foundry-ingest responsibility)

---

## Key Architectural Constraint

The document track and audio track must produce **identical output schemas**. foundry-chunk
reads `DoclingDOM.json` and does not know which track produced it. This schema compatibility
is non-negotiable: any change to `DoclingDOM.json` structure must be coordinated with
foundry-chunk.

---

## Known Issues (Must Bake In from Day One)

Three characterized Docling model failures affect Phase B1. Mitigations must be
designed into layout detection, not bolted on later:

| Issue | Severity | Root cause | Phase B1 mitigation |
| ------- | ---------- | ----------- | --------------------- |
| KI-002: Multi-column text misclassified as `Table` | HIGH | Low-confidence Table detections | Per-class confidence threshold; TableFormer gatekeeper |
| KI-003: Dense text misclassified as `Picture` | MEDIUM | Dark/dense rendering confusion | VLM inspection on Picture elements |
| KI-008: KI-002 propagates through 5 Docling pipeline stages | HIGH | Downstream of KI-002 | Fix KI-002 first |

Full issue files: `docs/known_issues/KI-002-*.md`, `KI-003-*.md`, `KI-008-*.md` in
`image_detection` repo.

---

## Constraints

| Constraint | Detail |
| ----------- | -------- |
| Infrastructure | docling-serve already deployed at `http://192.168.1.209:5001`; use it |
| Upstream params | Use `DoclingRoutingParams.to_cli_args()`; do not re-derive Docling config |
| Image corrections | Corrected page images arrive pipeline-ready; do NOT re-apply corrections |
| External calls | No external network calls except to configured docling-serve and GCS |
| Privacy | No page images or text logged at INFO level; only hashed/redacted IDs |
| Python | 3.12, UV package manager |

---

## Success Metrics

| Phase | Metric | Target |
| ------- | -------- | -------- |
| B1 | Layout mAP@0.50 (DocLayNet classes) | ≥ 0.82 |
| B1 | `DoclingDOM.json` written to GCS for standard-tier documents | 100% of born-digital PDFs |
| B2 | Reading order pairwise F1 | ≥ 0.85 |
| B3 | Table structure TEDS | ≥ 0.90 |
| B3 | OCR WER improvement over baseline | ≥ 10% relative |
| All | Layout detection latency (GPU) | ≤ 100 ms/page (≤ 300 ms acceptable) |
| All | OCR latency (average complexity) | ≤ 300 ms/page (≤ 800 ms acceptable) |
| All | Throughput per worker | ≥ 3–5 pages/second |

Phase B1 gate: all 10 integration tests in handoff Section 14 pass, including
born-digital PDF standard-tier and audio track passthrough.

---

## Reference Documents

| Document | Location |
| --------- | --------- |
| Team handoff (full context) | `image_detection/docs/development/RAG Pipeline/foundry-unify-team-handoff.md` |
| Prepare-Doc → Unify contract | `image_detection/docs/development/RAG Pipeline/prepare-doc-unify-contract.md` |
| Prepare-Audio → Unify contract | `image_detection/docs/development/RAG Pipeline/prepare-audio-unify-contract.md` |
| Unify → Chunk contract | `image_detection/docs/development/RAG Pipeline/chunk-embed-contract.md` |
| F/NF requirements | `image_detection/docs/_archived/cross-project/unify-f-nf.md` |
| DocumentMetadata schema | `image_detection/src/image_preprocessing_detector/schema.py` |
| Docling HTTP client (copy-ready) | `image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py` |
| DOCLING-API-CONTRACT.md | `homelab-infra/docs/planning/contracts/DOCLING-API-CONTRACT.md` (private) |
