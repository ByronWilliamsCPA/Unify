# 01 - Dependencies and Supply Chain

State: lockfile present and dependency floors current; the visible risks are unpinned container base images, a Python lower bound nearing security EOL, and a heavy unused ML extra. No prior-tooling residue files.

## DEP-01 Container base images not digest-pinned

Severity: Medium. Effort: S (single-file edit, plus tracking digests).

`Dockerfile` pulls `python:3.12-slim` (two `FROM` lines) and `COPY --from=ghcr.io/astral-sh/uv:latest /uv`. The `uv:latest` tag is a moving target; `python:3.12-slim` is a rolling tag. Neither is digest-pinned, so two builds of the same commit can resolve different base layers.

Evidence: `Dockerfile` `FROM python:3.12-slim AS builder`, `FROM python:3.12-slim`, `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`.

Recommendation: Pin base images by digest (`python:3.12-slim@sha256:...`, `uv:<version>@sha256:...`) and let Renovate bump them.

## DEP-02 Python 3.10 lower bound nears security EOL

Severity: Medium. Effort: S.

`requires-python = ">=3.10,<3.15"`. CPython 3.10 reaches end of security support in October 2026 (about five months from this audit date, 2026-05-29). CI and the Dockerfile target 3.12, so the 3.10 floor is untested surface that will be unsupported soon.

Evidence: `pyproject.toml:12`; Dockerfile and `ci.yml:38` use `python-version: '3.12'`.

Recommendation: Raise the floor to `>=3.11` (or `>=3.12` to match what CI actually tests) before 3.10 EOL, or add 3.10 to the test matrix if support is intended.

## DEP-03 Heavyweight `ml` extra declared but unused

Severity: Low. Effort: S.

The `ml` optional extra pins `torch>=2.9.0`, `torchvision>=0.24.0`, `numpy>=1.24.0`, `scikit-learn>=1.3.0`, `tensorboard>=2.14.0`. No `import torch`, `import numpy`, or `sklearn` reference exists anywhere in `src/`. These are placeholder dependencies for the unbuilt OCR feature.

Evidence: `pyproject.toml:124-130`; `grep -rn "torch\|numpy\|sklearn" src/` returns nothing.

Recommendation: Defer the `ml` extra until code uses it, or comment it out so dependency-review and SBOM tooling does not track libraries the project does not run.

## DEP-04 Large commented documentation block inside the dependencies array

Severity: Low. Effort: S.

`dependencies` lists 5 runtime packages, then roughly 45 lines of commented version-compatibility notes (backport examples, PEP 594 removals, free-threaded mode). This is template guidance shipped inside the declarative array, not project state.

Evidence: `pyproject.toml:28-74`.

Recommendation: Move the commentary to `docs/PYTHON_COMPATIBILITY.md` (which already exists) and keep the array to actual dependencies.

## Lockfile and residue

`uv.lock` is present (about 946 KB) and `pyproject.toml` uses standard PEP 621 layout, so the project is reproducible in principle; frozen-consistency was not re-verified because `uv lock --check` was out of scope for a read-only run. No migration residue: no `requirements*.txt`, `setup.py`, `setup.cfg`, `poetry.lock`, or `Pipfile`. The CHANGELOG mention of "Poetry" is a docs issue, recorded under DOC-01, not a residue file.

## Machine-readable findings

```json
[
  {"id": "DEP-01", "title": "Container base images not digest-pinned", "domain": "dependencies", "severity": "Medium", "effort": "S", "files": ["Dockerfile"], "evidence": "Dockerfile: FROM python:3.12-slim (x2); COPY --from=ghcr.io/astral-sh/uv:latest", "recommendation": "Pin base images by sha256 digest and let Renovate bump them.", "cve": ""},
  {"id": "DEP-02", "title": "Python 3.10 lower bound nears security EOL (Oct 2026)", "domain": "dependencies", "severity": "Medium", "effort": "S", "files": ["pyproject.toml"], "evidence": "pyproject.toml:12 requires-python = \">=3.10,<3.15\"; CI/Dockerfile target 3.12", "recommendation": "Raise floor to >=3.11/>=3.12 before 3.10 EOL or add 3.10 to the test matrix.", "cve": ""},
  {"id": "DEP-03", "title": "Heavyweight ml extra declared but unused", "domain": "dependencies", "severity": "Low", "effort": "S", "files": ["pyproject.toml"], "evidence": "pyproject.toml:124-130 (torch/torchvision/numpy/sklearn/tensorboard); no imports in src/", "recommendation": "Defer or comment out the ml extra until code uses it.", "cve": ""},
  {"id": "DEP-04", "title": "Commented doc block inside dependencies array", "domain": "dependencies", "severity": "Low", "effort": "S", "files": ["pyproject.toml"], "evidence": "pyproject.toml:28-74 ~45 lines of commented compatibility notes", "recommendation": "Move commentary to docs/PYTHON_COMPATIBILITY.md.", "cve": ""}
]
```
