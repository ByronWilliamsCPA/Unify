---
schema_type: planning
title: "Foundry Unify - Project Plan"
description: "Current-state assessment and sprint plan for Foundry Unify"
tags:
  - planning
  - roadmap
  - sprint
status: draft
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Track real project status and define the next sprint"
component: "Strategy"
---

**Last reviewed**: 2026-10-01
**Goal**: OCR orchestration and layout analysis service for the Foundry RAG pipeline.

## 1. Current state (verified 2026-10-01)

| Area | Status | Evidence |
|------|--------|----------|
| Scaffolding (config, logging, exceptions, correlation + security middleware, health router) | Done | `src/foundry_unify/`, 195 tests pass, 99.6% coverage |
| CI/CD, release, supply-chain (SLSA, SBOM, Renovate, QLTY, Sonar) | Done, still churning | PRs #7 to #33 merged; PRs #35 to #48 open |
| **OCR orchestration / layout analysis (the product)** | **Not started** | No OCR code, no engine adapters, no pipeline |
| Runnable application | **Missing** | No `FastAPI()` app factory or entry point; health router and middleware are not mounted anywhere |
| Planning docs | **Placeholders** | `project-vision.md`, `tech-spec.md`, `roadmap.md` say "Awaiting Generation"; `adr/` is empty; no ADRs |
| `docs/project/roadmap.md` | Stale | Generic "Additional features (TBD)" phases |
| `CHANGELOG.md` | Stale | Describes Poetry and a CLI that don't exist; version still "0.1.0 - TBD" |

The project is a well-hardened template with no product code yet. Recent work (about 25 merged and open PRs) is almost entirely CI and dependency plumbing.

## 2. Findings that affect planning

1. **Planning docs block everything.** Nothing defines inputs, outputs, OCR engines, or the interface to the Foundry RAG pipeline. Implementation without them risks rework.
2. **Heavy, unused dependencies.** `pyproject.toml` pulls `torch`, `torchvision`, `scikit-learn`, `tensorboard`, `sqlalchemy`, and `alembic` as runtime dependencies. None are imported. They bloat the image and the CVE surface (PR #48 is bumping 25 locked packages). Decide which engines need them and move the rest to optional extras.
3. **Python version drift.** CLAUDE.md says 3.12, `pyproject.toml` allows `>=3.10,<3.15`, and the local environment resolved to 3.11. Pin one target.
4. **Open PR backlog (13).** Mix of Renovate (#36, #37, #38), CI fixes (#42 to #47), and tooling (#35, #39, #41). Several likely overlap (#45, #46, #44 all touch CI gates on main). Triage before new feature work.
5. **Security middleware limits.** Rate limiter is in-memory (not multi-replica safe). The module-level `settings` has only logging fields; there is no config for OCR engines, storage, or auth.
6. **Docs drift.** README badges and links use `foundry_unify` repo paths; the repository is `ByronWilliamsCPA/Unify`.

## 3. Recommended roadmap

| Phase | Theme | Exit criteria |
|-------|-------|---------------|
| 0 | Foundation cleanup (this sprint's first half) | Backlog triaged, planning docs generated, ADRs written |
| 1 | Walking skeleton | App factory mounts middleware and health; `POST /v1/documents` accepts a PDF/image and returns a job id; one OCR engine adapter behind an interface |
| 2 | Orchestration | Multi-engine routing and fallback, layout analysis output schema, async job queue, persistence |
| 3 | Integration and hardening | Foundry RAG contract tests, auth, distributed rate limiting, performance targets, deployment guide |

## 4. Next sprint (Sprint 1: "Decide and de-risk", about 2 weeks)

**Sprint goal**: Close the planning gap and leave the repo with a runnable service skeleton and a clean PR queue.

### Must have

1. **Triage the PR backlog** (S). Merge or close #44 to #48 and #35/#42/#43 in dependency order; merge Renovate #36/#38 once green; hold #37 (major action bumps) for a separate review. Branch: `chore/pr-backlog-triage`.
2. **Generate planning docs** (M). Run `/plan` to produce vision, tech-spec, roadmap, and ADRs. Required decisions: OCR engine(s) and licensing, sync vs async job model, storage, auth, layout output schema, RAG pipeline contract. Branch: `docs/planning-foundation`.
3. **Dependency diet** (S). Move unused `torch`, `torchvision`, `scikit-learn`, `tensorboard`, `sqlalchemy`, `alembic` to extras until used; pin Python target. Branch: `chore/trim-dependencies`.
4. **App factory and entry point** (M). `foundry_unify.main:create_app()` mounting correlation and security middleware and the health router; `uvicorn` run command; Dockerfile `CMD`; integration test via `TestClient`. Branch: `feat/app-factory`.

### Should have

5. **Settings expansion** (S). Add engine, storage, and limits fields to `Settings`, with validation tests. Branch: `feat/settings-expansion`.
6. **Refresh stale docs** (S). Fix CHANGELOG (remove Poetry/CLI claims), `docs/project/roadmap.md`, README links. Branch: `docs/refresh-stale-docs`.

### Could have

7. **OCR engine interface spike** (M). `OcrEngine` protocol plus a stub engine, with contract tests; no real engine yet. Branch: `feat/ocr-engine-interface`.

### Definition of done

`ruff check`, `basedpyright src/`, `bandit -r src`, and `pytest` (80% minimum) pass; CI green; planning docs have no "Awaiting Generation" banners.

### Risks

| Risk | Mitigation |
|------|------------|
| OCR engine choice slips and blocks Phase 1 | Time-box ADR to day 3; the interface spike (item 7) keeps work unblocked |
| Large ML dependencies resurface in image size | Keep them in extras; measure image size in CI |
| More CI churn consumes the sprint | Cap item 1 at 2 days; no new workflow changes without a failing check |

## 5. Open questions for the owner

- Which OCR engines are in scope (for example Tesseract, PaddleOCR, cloud APIs), and are there licensing or data-residency limits?
- Is the service synchronous (request/response) or job-based with callbacks?
- What does the Foundry RAG pipeline expect as input (markdown, JSON blocks with bounding boxes, both)?
- Is 3.12 the firm target?
