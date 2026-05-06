---
schema_type: adr
title: "ADR-001: Use docling-serve HTTP API for Docling integration"
description: "Integrate with Docling via the docling-serve REST API rather than importing Docling as a Python library."
tags:
  - architecture
  - decisions
  - adr
  - docling
  - ocr
status: published
owner: core-maintainer
component: OCR-Integration
source: "foundry-unify-team-handoff.md Section 7"
purpose: "Document the decision to use the deployed docling-serve HTTP service rather than local Docling library import."
---

**Decision Date:** 2026-05-05
**Deciders:** Byron Williams
**Affected Teams:** foundry-unify
**Implementation Target:** Phase B1

---

## Context

### Problem Statement

foundry-unify must run OCR and layout analysis via Docling. Docling can be
integrated in two ways: imported as a Python library (direct), or called via
the `docling-serve` REST API (remote). The choice determines where GPU
resources live, who owns model loading, what the container footprint looks
like, and what the failure mode is when Docling is unavailable.

This decision is expensive to reverse: switching from HTTP to library import
(or vice versa) after Phase B1 means rewriting the OCR adapter, changing
the deployment topology, and re-testing every tier.

### Current State

A `docling-serve` instance is already deployed and operational on the homelab
network at `http://192.168.1.209:5001`. It supports:

- Standard Docling pipeline: `POST /v1/convert/file`
- VLM-augmented pipeline: separate Docker Compose service with
  `ibm-granite/granite-docling-258M`
- GCS-sync variant for artifact handoff

A working REST client already exists in the upstream repo:
`image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py`

This client handles file upload, routing params as form data, response
parsing, and timeout configuration. It is copy-ready.

### Requirements

- **Must have:** GPU-accelerated Docling processing without requiring GPU in
  the foundry-unify service container
- **Must have:** Standard and VLM pipeline switchable without service restart
- **Must have:** foundry-unify container image stays lean (no Docling model weights)
- **Should have:** Consistent behaviour with how docling-serve is used in
  the upstream foundry-prepare-doc testing environment
- **Nice to have:** Shared infrastructure with other pipeline services that
  may also need Docling

---

## Decision

> **We will integrate with Docling via the docling-serve HTTP API** using a
> thin REST client (adapted from the existing `docling_client.py`), calling
> `POST /v1/convert/file` with `DoclingRoutingParams` applied as form data.

### Why This Decision

1. **Infrastructure already exists.** docling-serve is deployed and stable.
   Building library integration would duplicate infrastructure that is already
   working.

2. **GPU stays with docling-serve, not with this service.** foundry-unify's
   container does not need a GPU. The service is I/O-heavy (GCS reads/writes)
   and CPU-light. Bundling Docling with its GPU dependencies would bloat the
   image and require GPU scheduling for a container that does not need it.

3. **VLM and standard modes are switchable at the infrastructure layer.**
   The VLM pipeline (granite-docling-258M) runs as a separate Docker Compose
   service. Switching tiers at runtime is a routing decision, not a code
   change. Library integration would require loading two different model
   configurations in the same process.

4. **Copy-ready client lowers Phase B1 risk.** The upstream repo provides a
   working client. Adapting it is a day of work. Implementing local Docling
   integration from scratch, including model loading and batch management,
   is weeks of work with high uncertainty.

5. **Consistent with how the pipeline tests Docling.** foundry-prepare-doc
   tested Docling via docling-serve during development. The HTTP interface
   is already validated against the document types and edge cases this
   pipeline sees.

### How It Works

1. `GCSArtifactReader` downloads `DocumentMetadata.json` and corrected
   page images from `01-preprocessed/`.

2. `DoclingServeClient` calls `POST /v1/convert/file` with:
   - Page images as multipart form data
   - `DoclingRoutingParams.to_cli_args()` applied as form fields
   - Timeout: 300 seconds (default; configurable)

3. Response is parsed to extract Docling's JSON output (DoclingDocument).

4. `LayoutPostprocessor` applies KI-002/KI-003 mitigations to the raw
   layout detections.

5. `DOMAssembler` converts the processed Docling output to `DoclingDOM.json`.

```python
# Simplified call flow (Phase B1)
client = DoclingServeClient(base_url=settings.docling_serve_url)
routing_args = metadata.docling_params.to_cli_args()

result = await client.convert_file(
    file_path=page_image_path,
    routing_args=routing_args,
    timeout=settings.docling_serve_timeout_seconds,
)

dom_page = assembler.build_page(result, page_number=page_num)
```

**Endpoint health check:** `GET /health` is called at service startup and
surfaced via foundry-unify's own `GET /health` response. If docling-serve
is unreachable, foundry-unify reports `docling_serve: unreachable` but
remains running; Cloud Workflows retries handle transient failures.

---

## Consequences

### Positive Consequences

1. **Lean container image.** No Docling weights or GPU dependencies bundled;
   image stays small and fast to build.
2. **Tier switching is operational, not a code change.** Standard vs VLM
   pipeline is a URL routing decision managed in deployment config.
3. **Phase B1 implementation risk is low.** Copy-ready client exists.
4. **Separation of concerns.** Docling version upgrades, model swaps, and
   GPU resource management are docling-serve's responsibility.

### Negative Consequences

1. **Network latency per request.** Each page conversion adds an HTTP
   round-trip. Mitigated by running docling-serve on the local homelab
   network (LAN latency, not internet latency) and by tuning
   `page_batch_size` in `DoclingRoutingParams`.
2. **docling-serve is a runtime dependency.** If it is down, foundry-unify
   cannot process documents. Cloud Workflows retry logic is the safety net.
3. **No direct Docling API access.** Advanced Docling features not exposed
   by docling-serve's REST API cannot be used without forking docling-serve
   or switching to library integration. This risk is low: docling-serve
   exposes the full Docling pipeline configuration surface.

### Neutral Consequences

1. The existing `docling_client.py` code must be copied into this repo
   and adapted to foundry-unify's settings system.
2. Integration tests require docling-serve to be running; CI must either
   run a docling-serve container or mock the HTTP interface.

---

## Alternatives Considered

### Alternative 1: Import Docling as a Python library (direct integration)

**Approach:** Add `docling` and its dependencies to `pyproject.toml`;
load models at service startup; call Docling pipeline functions directly.

**Advantages:**
- No network hop per request
- Full access to Docling internal API
- No dependency on external service availability

**Disadvantages:**
- foundry-unify container requires GPU and GPU scheduling
- Image size grows by several gigabytes (model weights)
- Docling model loading at service startup increases cold start time
- Two model configurations (standard + VLM) require complex in-process
  management
- Disconnects from the validated docling-serve deployment the pipeline
  already uses

**Why not chosen:** GPU in the service container violates the architecture
goal of lean, horizontally-scalable workers. Image size and cold start
penalties are unacceptable for a pipeline service.

---

### Alternative 2: Modal remote function for Docling (serverless GPU)

**Approach:** Wrap Docling in a Modal function; call it from foundry-unify
via Modal's Python SDK. GPU is provided by Modal on demand.

**Advantages:**
- No persistent docling-serve deployment to maintain
- GPU scales to zero when idle
- Model weights managed by Modal

**Disadvantages:**
- Modal cold start latency (5-30 seconds per invocation) is incompatible
  with <= 300 ms/page OCR target
- Adds Modal as a billable runtime dependency
- docling-serve is already deployed and operational; Modal adds no value

**Why not chosen:** Cold start latency is incompatible with the performance
target. docling-serve already solves the GPU access problem.

---

### Alternative 3: Embed docling-serve client in a shared library

**Approach:** Extract the HTTP client into a `foundry-common` shared library;
both foundry-prepare-doc and foundry-unify depend on it.

**Advantages:**
- Single source of truth for the docling-serve interface

**Disadvantages:**
- Introduces a shared library dependency before either service has stable
  interfaces; premature abstraction
- foundry-prepare-doc uses docling-serve for testing only, not production;
  the use cases diverge

**Why not chosen:** Premature. The two services have different use patterns.
Copy the client, stabilize the interface, extract to shared library later
only if duplication becomes a maintenance burden.

---

## Implementation

### Phase B1 Implementation Steps

1. Copy `docling_client.py` from `image_detection` repo into
   `src/foundry_unify/adapters/docling_serve_client.py`
2. Adapt to foundry-unify's `Settings` class (URL, timeout from env)
3. Add `docling_serve_url` and `docling_serve_timeout_seconds` to `config.py`
4. Wire `DoclingServeClient` into `DocumentPipeline`
5. Add health check probe to `GET /health` endpoint
6. Add integration test: mock docling-serve HTTP server; assert correct
   routing params applied

### CI Considerations

For unit tests: mock the HTTP client with `httpx.MockTransport` or `responses`.

For integration tests: spin up docling-serve as a Docker service in the
CI environment, or run integration tests against the live homelab instance
(gated by `pytest -m integration`).

---

## References

### Related Documents

- [Project Vision and Scope](../project-vision.md)
- [Technical Specification](../tech-spec.md)
- [Development Roadmap](../roadmap.md)

### External References

- [docling-serve GitHub](https://github.com/DS4SD/docling-serve)
- [docling-serve API: POST /v1/convert/file](http://192.168.1.209:5001/docs)
- [DOCLING-API-CONTRACT.md](homelab-infra/docs/planning/contracts/DOCLING-API-CONTRACT.md)

### Implementation References

- [Reference HTTP client](../../../../image_detection/src/image_preprocessing_detector/text_extraction/docling_client.py)
- [DoclingRoutingParams schema](../../../../image_detection/src/image_preprocessing_detector/schema.py#L755)
- [Handoff doc Section 7: Infrastructure](../../../../image_detection/docs/development/RAG%20Pipeline/foundry-unify-team-handoff.md)

---

**Last Updated:** 2026-05-05
**Next Review:** On demand (revisit if docling-serve REST API proves insufficient for Phase B3 specialist routing)
