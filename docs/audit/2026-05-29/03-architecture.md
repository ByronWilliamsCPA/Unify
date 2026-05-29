# 03 - Architecture and Structure

State: clean module layering with one packaging defect that breaks the documented import path, no application entrypoint despite container config that assumes one, and a product (OCR) with zero domain implementation.

## ARCH-01 Core modules import optional-extra dependencies

Severity: High. Effort: M.

`src/foundry_unify/api/health.py`, `middleware/security.py`, and `middleware/correlation.py` import `fastapi` and `starlette` at module top level. Those packages are declared only in the `api` optional extra (`pyproject.toml:134-139`), not in core `dependencies` (`pyproject.toml:23-27`, which lists only pydantic, pydantic-settings, python-dotenv, structlog, rich). `middleware/__init__.py` re-exports from `security.py`, so the exact call shown in CLAUDE.md, `from foundry_unify.middleware import CorrelationMiddleware, add_security_middleware`, raises `ModuleNotFoundError: starlette` in a default `pip install foundry-unify`.

Evidence: `pyproject.toml:23-27` vs `pyproject.toml:134-139`; `src/foundry_unify/middleware/__init__.py:23-28`; `api/health.py:20`; `middleware/security.py:28-32`.

Recommendation: Move fastapi/starlette/uvicorn into core `dependencies` (the service is a web API), or guard the imports and make `middleware`/`api` import-safe without the extra.

## ARCH-02 No application entrypoint; container cannot start

Severity: High. Effort: M.

`Dockerfile` ends with `CMD ["uvicorn", "foundry_unify.main:app", ...]` and `docker-compose.yml` builds from it, but there is no `src/foundry_unify/main.py` and no `app` object anywhere. Two compounding faults: (1) the target module does not exist, and (2) the builder runs `uv sync --frozen --no-dev`, which installs core deps only and excludes the `api` extra, so `uvicorn` is not even present in the runtime image. The image builds and then fails on `docker run`.

Evidence: `Dockerfile` `CMD ["uvicorn", "foundry_unify.main:app", "--host", "0.0.0.0", "--port", "8000"]`; `Dockerfile` `RUN uv sync --frozen --no-dev`; `ls src/foundry_unify/main.py` -> not found; `docker-compose.yml:10-16` builds the same image.

Recommendation: Add `main.py` exposing `app` (FastAPI instance mounting the health router and security middleware) and change the builder to `uv sync --frozen --no-dev --extra api`.

## ARCH-03 Stated product has no domain code

Severity: Medium. Effort: L.

The project is described as "OCR orchestration and layout analysis service for the Foundry RAG pipeline" (pyproject description, README, CLAUDE.md). All 1,886 LOC in `src/` are template scaffolding: config, exception hierarchy, correlation/security middleware, logging, health endpoints, and an empty financial stub. There is no OCR, layout, or orchestration module. This is expected for a freshly instantiated template (3 commits), but README and CLAUDE.md present the structure as built.

Evidence: `src/foundry_unify/` tree (12 files, none OCR-related); `git rev-list --count HEAD` = 3.

Recommendation: Treat this repo as scaffolding, not product. Track the gap in the roadmap (see ARCH-04) and align README maturity claims (DOC-02).

## ARCH-04 Planning docs are placeholders; no ADRs

Severity: Medium. Effort: M.

`docs/planning/project-vision.md`, `tech-spec.md`, and `roadmap.md` each carry `> **Status**: Awaiting Generation` and are 48-59 lines of template. `docs/ADRs/` and `docs/planning/adr/` contain only `README.md` and `adr-template.md`. Decisions already encoded in the repo (uv over Poetry, BasedPyright over Mypy, FastAPI/starlette stack, structlog) have no ADR.

Evidence: `docs/planning/project-vision.md:14`, `tech-spec.md:14`, `roadmap.md:14`; `ls docs/ADRs/` = README.md, adr-template.md.

Recommendation: Generate the planning docs and write ADRs for the stack choices before domain code lands, so the OCR design has a recorded rationale.

## Module boundaries: clean

Import graph is acyclic. `core` (config, exceptions) depends on nothing internal; `middleware` and `api` depend inward; `utils` is standalone. `middleware/security.py` (520 LOC) is a real implementation (SecurityHeaders with CSP/HSTS/X-Frame-Options, RateLimit, SSRFPrevention), not a stub. No circular imports, no layering inversion. One line: structure is sound aside from the packaging defects above.

## Machine-readable findings

```json
[
  {"id": "ARCH-01", "title": "Core modules import optional api-extra deps (fastapi/starlette)", "domain": "architecture", "severity": "High", "effort": "M", "files": ["src/foundry_unify/middleware/__init__.py", "src/foundry_unify/middleware/security.py", "src/foundry_unify/api/health.py", "pyproject.toml"], "evidence": "pyproject.toml:23-27 vs 134-139; middleware/__init__.py:23-28 re-exports starlette-importing module", "recommendation": "Move fastapi/starlette/uvicorn to core dependencies or guard imports so middleware/api are import-safe.", "cve": ""},
  {"id": "ARCH-02", "title": "No application entrypoint; Dockerfile/compose target missing main:app and skip api extra", "domain": "architecture", "severity": "High", "effort": "M", "files": ["Dockerfile", "docker-compose.yml", "src/foundry_unify/"], "evidence": "Dockerfile CMD uvicorn foundry_unify.main:app; no main.py; RUN uv sync --frozen --no-dev (api extra excluded)", "recommendation": "Add main.py exposing app and build with --extra api.", "cve": ""},
  {"id": "ARCH-03", "title": "Stated OCR product has zero domain code", "domain": "architecture", "severity": "Medium", "effort": "L", "files": ["src/foundry_unify/"], "evidence": "All 1886 src LOC are template scaffolding; no OCR/layout module; 3 commits", "recommendation": "Treat as scaffolding; track the gap in roadmap and align README maturity claims.", "cve": ""},
  {"id": "ARCH-04", "title": "Planning docs are Awaiting Generation; no real ADRs", "domain": "architecture", "severity": "Medium", "effort": "M", "files": ["docs/planning/project-vision.md", "docs/planning/tech-spec.md", "docs/planning/roadmap.md", "docs/ADRs/"], "evidence": "project-vision.md:14 / tech-spec.md:14 / roadmap.md:14 Status: Awaiting Generation; ADRs only templates", "recommendation": "Generate planning docs and write ADRs for uv/BasedPyright/FastAPI/structlog choices.", "cve": ""}
]
```
