# 00 - Holistic Legacy and Architecture Audit: Final Report

Generated: 2026-05-29 (UTC). Commit: 6c1b9a3. Repository: ByronWilliamsCPA/Unify (Foundry Unify).

## Repo map

- Language / build: Python, uv-managed, PEP 621 `pyproject.toml` + `uv.lock` (about 946 KB). Build backend hatchling. `requires-python = ">=3.10,<3.15"`; CI and Dockerfile target 3.12.
- Size: 167 tracked files. 31 Python files, about 7,187 Python LOC total. Application code in `src/foundry_unify/` is 12 files, 1,886 LOC. Tests are 1,822 LOC across 3 test files (104 test functions). The rest is tooling, config, scripts, and docs.
- Tests / CI: pytest (+cov, asyncio, xdist, randomly, hypothesis). 17 GitHub Actions workflows, most delegating to org reusable workflows `ByronWilliamsCPA/.github`. Static analysis: Ruff, BasedPyright, Bandit, Semgrep, SonarCloud, CodeQL, Trivy, OSV, vulture, interrogate, darglint. Pre-commit with trufflehog, bandit, ruff, conventional-commits, and more.
- Largest / most-churned: churn is meaningless here. The repo has 3 commits (initial template import 2026-05-05, two CI cleanups). Nothing has accumulated history.
- Migration residue: none. No `requirements*.txt`, `setup.py`, `setup.cfg`, `poetry.lock`, or `Pipfile`. The only "residue" is documentation: `CHANGELOG.md` still says "Poetry package management".
- Template provenance: instantiated from cookiecutter-python-template via cruft. `.cruft.json` has `commit: null`, so cruft cannot compute updates against a base revision.

This is a freshly scaffolded template, not a running product. The described product (OCR orchestration and layout analysis) has zero domain code. The audit below judges it as scaffolding: most findings are configuration and packaging defects that will bite the moment someone tries to run or ship it, not accumulated legacy debt.

## Code quality: direct assessment

The Python that exists is clean. The full Ruff ruleset (a wide PyStrict-aligned selection: E, W, F, I, N, D, UP, ANN, B, SIM, S, BLE, EM, PTH, and more) passes with zero violations. No legacy typing generics, no `%`/`.format` logging, no `os.path`, no commented-out code flagged by ERA, zero TODO/FIXME/HACK/XXX markers. The five `type: ignore`/`pyright: ignore` uses are each scoped with an error code and a real reason. `middleware/security.py` (520 LOC) is a genuine implementation, not a stub.

The weakness is not style, it is honesty of behavior. Two pieces of code present themselves as functional while doing nothing: `readiness()` always returns HTTP 200 because its checks dict is never populated (`all([])` is `True`), and a test asserts `assert True` after exercising a logging path. `utils/financial.py` is a one-line empty module carried over from the template into a project that has no financial domain. The code that exists is well formed; some of it is theater.

## Architecture: direct assessment

The module layering is sound: `core` depends on nothing internal, `middleware`/`api` depend inward, `utils` stands alone, no circular imports. The structure works against maintainers in two specific ways, both packaging faults rather than design faults.

First, the import boundary is wrong. `api/health.py` and the `middleware` package import `fastapi`/`starlette` at module top level, but those live in the optional `api` extra, not core `dependencies`. The exact usage CLAUDE.md documents (`from foundry_unify.middleware import ...`) raises `ModuleNotFoundError` on a default install. A web service whose web framework is optional has its dependency direction inverted.

Second, there is no entrypoint. `Dockerfile` and `docker-compose.yml` launch `uvicorn foundry_unify.main:app`, but `main.py` does not exist, and the image is built with `uv sync --no-dev`, which excludes the `api` extra, so `uvicorn` is not installed either. The container builds and then fails on `docker run`. These two faults compound: even if `main.py` existed, the runtime image could not import it.

Everything else (the empty product, the unwritten planning docs and ADRs) is expected for a 3-commit template and is flagged at Medium so it lands on the roadmap rather than being mistaken for finished work.

## Cross-cutting themes

1. Two-source configuration drift. The same setting is declared in multiple places that disagree. SonarCloud organization is `ByronWilliamsCPA` in `ci.yml` but `williaby` in `sonar-project.properties` and `sonarcloud.yml`. The same `python-ci.yml` is pinned `@main` in one workflow and `@SHA` in another. SonarCloud is configured twice (org workflow plus standalone). When a value lives in two files, one of them is wrong, and here both kinds of error are present.

2. Moving references in the supply chain. Twelve org reusable-workflow calls use `@main`, a third-party action uses `@master`, base images use rolling tags, and one CI job pipes a remote install script into a shell. The repo SHA-pins 25 of 30 direct actions, so the team knows the practice; it is applied inconsistently to the higher-leverage targets (reusable workflows that define the gates themselves).

3. Scaffolding documented as product. README, CLAUDE.md, and CHANGELOG describe an OCR service, a Poetry setup, and a CLI, none of which exist. The docs were written from the template's intent, not the repo's state.

4. No age stratification and no AI-pattern divergence to report. With 3 commits and one author, there are no old-versus-new strata and no competing implementation styles. This is a single-vintage codebase.

## Prioritized remediation backlog

Sorted by severity, then effort.

| ID | Finding | Domain | Severity | Effort | Files |
|----|---------|--------|----------|--------|-------|
| SEC-01 | Org reusable workflows pinned to moving @main | security | High | S | .github/workflows/ci.yml, security-analysis.yml, sbom.yml, release.yml |
| CI-01 | SonarCloud org mismatch (williaby vs ByronWilliamsCPA) | cicd | High | S | sonar-project.properties, .github/workflows/sonarcloud.yml, ci.yml |
| ARCH-01 | Core modules import optional api-extra deps (fastapi/starlette) | architecture | High | M | src/foundry_unify/middleware/__init__.py, security.py, api/health.py, pyproject.toml |
| ARCH-02 | No entrypoint; Dockerfile targets missing main:app and skips api extra | architecture | High | M | Dockerfile, docker-compose.yml, src/foundry_unify/ |
| DEP-01 | Container base images not digest-pinned | dependencies | Medium | S | Dockerfile |
| DEP-02 | Python 3.10 lower bound nears security EOL (Oct 2026) | dependencies | Medium | S | pyproject.toml |
| CQ-02 | Readiness probe always returns healthy | code-quality | Medium | S | src/foundry_unify/api/health.py |
| SEC-02 | sonarqube-quality-gate-action pinned to @master | security | Medium | S | .github/workflows/sonarcloud.yml |
| SEC-03 | uv installed via unpinned curl\|sh in CI | security | Medium | S | .github/workflows/sonarcloud.yml |
| CI-02 | Duplicate SonarCloud analysis | cicd | Medium | S | .github/workflows/ci.yml, sonarcloud.yml |
| CI-05 | Non-blocking SonarCloud quality gate | cicd | Medium | S | .github/workflows/sonarcloud.yml |
| ARCH-04 | Planning docs Awaiting Generation; no real ADRs | architecture | Medium | M | docs/planning/*.md, docs/ADRs/ |
| CI-03 | Full CI runs twice per PR | cicd | Medium | M | .github/workflows/ci.yml, pr-validation.yml |
| DOC-02 | README presents unbuilt OCR service as built | docs | Medium | M | README.md, CLAUDE.md |
| ARCH-03 | Stated OCR product has zero domain code | architecture | Medium | L | src/foundry_unify/ |
| DEP-03 | Heavyweight ml extra declared but unused | dependencies | Low | S | pyproject.toml |
| DEP-04 | Commented doc block inside dependencies array | dependencies | Low | S | pyproject.toml |
| CQ-01 | Non-asserting placeholder test (assert True) | code-quality | Low | S | tests/test_example.py |
| CQ-03 | Empty financial.py stub | legacy-code | Low | S | src/foundry_unify/utils/financial.py |
| SEC-04 | Some actions tag-pinned not SHA-pinned | security | Low | S | .github/workflows |
| SEC-05 | Weak placeholder password in .env.example | security | Low | S | .env.example |
| CI-04 | Same reusable workflow pinned @main and @SHA | cicd | Low | S | .github/workflows/ci.yml, pr-validation.yml |
| CI-06 | Obsolete docker-compose version attribute | cicd | Low | S | docker-compose.yml |
| CI-07 | Stale pre-commit pins; basedpyright not in pre-commit | cicd | Low | S | .pre-commit-config.yaml |
| CI-08 | pip cache on a uv-managed project | cicd | Low | S | .github/workflows/sonarcloud.yml |
| DOC-01 | CHANGELOG claims Poetry and a nonexistent CLI | docs | Low | S | CHANGELOG.md |
| DOC-03 | Malformed uv command in README | docs | Low | S | README.md |
| DOC-04 | CLAUDE.md structure lists empty financial.py, omits api/ | docs | Low | S | CLAUDE.md |
| DOC-05 | Planning docs and ADRs unwritten but linked | docs | Low | M | docs/planning/*.md, docs/ADRs/ |

## Resolved overlaps

The "core modules import optional deps" issue surfaced from both the dependencies and architecture angles; it is filed once as ARCH-01 (the better home, since the fix is dependency-direction, not version currency). The Dockerfile `--no-dev` install gap and the missing `main.py` are one deployment defect, filed as ARCH-02. The `@main` reusable-workflow pinning is both a supply-chain risk (SEC-01) and a CI reliability risk; it is filed once as SEC-01, and CI-04 covers only the narrower inconsistency between the two `python-ci.yml` pins. Secret scanning was raised as a possible gap (no detect-secrets baseline) but is covered by trufflehog and `detect-private-key` in pre-commit, so no finding was recorded.

## Verdict

Drifting, not at-risk. The code that exists is clean and the security tooling is extensive, but the repo cannot currently run (no entrypoint, web framework optional, container start fails) and its configuration contradicts itself in several places. None of this is hard to fix because none of it is entrenched; it is a young template that was documented and configured ahead of being wired up.

The three changes that move it most:

1. Make it runnable: add `foundry_unify/main.py` exposing `app`, move fastapi/starlette/uvicorn into core `dependencies`, and build the image with the API deps (ARCH-01, ARCH-02).
2. Fix the supply-chain pinning: SHA-pin the org reusable workflows and the Sonar/uv steps (SEC-01, SEC-02, SEC-03).
3. Reconcile the SonarCloud configuration into one path with one correct organization (CI-01, CI-02, CI-05).
