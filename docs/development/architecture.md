---
title: "Architecture"
schema_type: common
status: published
owner: core-maintainer
purpose: "Architecture documentation for Foundry Unify."
tags:
  - development
  - architecture
---

This document describes the architecture and design decisions for Foundry Unify.

## Pipeline Context

Unify is stage 3 of the five-repository Foundry pipeline. See the
[Pipeline Level 0](../architecture/pipeline-level-0.md) page for the pipeline and the
[Level 1 architecture](../architecture/diagrams/level-1/index.md) page for the planned design, phase plan, and build
status.

## Summary

Unify (package `foundry_unify`) is designed as a layered, Protocol-based service. It takes Prepare-Doc's
`DocumentMetadata.json` and corrected pages, or Prepare-Audio's `TranscriptMetadata.json`, runs OCR through
docling-serve for documents, and writes one `DoclingDOM.json` for Chunk. The approved design is the
[Foundry Unify design spec](https://github.com/williaby/image-preprocessing-detector/blob/main/docs/superpowers/specs/2026-05-05-foundry-unify-design.md). Today `src/foundry_unify/` contains only template infrastructure: `core/`
(settings, exceptions), `middleware/` (security, correlation), `api/health.py` (not mounted), and `utils/` (logging).
The OCR orchestration layers are not built.

## Design Principles

### 1. Type Safety

All code is fully typed with BasedPyright strict mode validation.

### 2. Structured Logging

Uses structlog for structured, JSON-formatted logs in production.

### 3. Configuration Management

Pydantic Settings for type-safe configuration from environment variables.

## Dependencies

See `pyproject.toml` for the complete dependency list.

## Architecture Decision Records

See the [ADRs directory](../ADRs/README.md) for documented architecture decisions.
