# 06 - Documentation and Developer Experience

State: docs describe a built OCR service and a Poetry/CLI setup that do not match the repo; onboarding commands include one that will not run.

## DOC-01 CHANGELOG claims Poetry, project uses uv

Severity: Low. Effort: S.

`CHANGELOG.md` lists "Initial project structure with Poetry package management". The project uses uv (`uv.lock`, `pyproject.toml` PEP 621, uv in CI and Dockerfile). No Poetry artifacts exist. The CHANGELOG also lists "CLI tool foundation", but there is no CLI module or `[project.scripts]` entry.

Evidence: `CHANGELOG.md:18` "Poetry package management"; `CHANGELOG.md` "CLI tool foundation"; no `poetry.lock`, no CLI in `src/`.

Recommendation: Replace "Poetry" with "uv" and drop the CLI line until a CLI exists.

## DOC-02 README presents an unbuilt service as built

Severity: Medium. Effort: M.

README and CLAUDE.md describe "OCR orchestration and layout analysis" with usage examples for middleware and correlation, but `src/` contains only scaffolding (no OCR, layout, or orchestration code). A new contributor following the README expects a working service and finds template stubs. The documented import `from foundry_unify.middleware import ...` also fails on a default install (see ARCH-01).

Evidence: `README.md` project description and usage sections; `src/foundry_unify/` has no domain module; CLAUDE.md "Correlation ID Patterns" examples import middleware that needs the `api` extra.

Recommendation: Add a clear "scaffolding / pre-alpha, no OCR yet" banner to README, and mark the documented API examples as requiring the `api` extra.

## DOC-03 Malformed uv command in README

Severity: Low. Effort: S.

README shows `uv sync --all-extras,ml`. That is not valid uv syntax; `--all-extras` takes no value and `,ml` is not parsed. The correct forms are `uv sync --all-extras` or `uv sync --extra ml`.

Evidence: `README.md:86` `uv sync --all-extras,ml`.

Recommendation: Replace with `uv sync --extra ml` (or `--all-extras`).

## DOC-04 CLAUDE.md structure lists a nonexistent/empty module and omits the API package

Severity: Low. Effort: S.

CLAUDE.md's "Project Structure" documents `utils/financial.py # Financial utilities (Decimal precision)`, but that file is a 1-line empty stub (see CQ-03). The same structure block omits the `api/` package and `api/health.py`, which do exist.

Evidence: CLAUDE.md "Project Structure" section; `src/foundry_unify/utils/financial.py:1`; `src/foundry_unify/api/health.py` not listed.

Recommendation: Update the structure block to match `src/` (drop or fill financial.py, add `api/`).

## DOC-05 Planning docs and ADRs unwritten

Severity: Low. Effort: M.

`docs/planning/project-vision.md`, `tech-spec.md`, and `roadmap.md` all read `Status: Awaiting Generation`. `docs/ADRs/` holds only a template. The README and CLAUDE.md link these as if populated. (Architectural impact is tracked under ARCH-04; the docs impact is the broken expectation set by the links.)

Evidence: `docs/planning/*.md:14` "Awaiting Generation"; `docs/ADRs/` = README.md + adr-template.md.

Recommendation: Generate the planning docs or mark the links as "to be written" so onboarding does not chase empty pages.

## Accurate areas

CONTRIBUTING.md, SECURITY.md, and the quick-start tooling commands (`uv sync --all-extras`, `uv run pytest`, `uv run ruff`) match the actual tooling. `mkdocs.yml` nav entries resolve to existing files. One line: the developer-tooling instructions are correct apart from DOC-03.

## Machine-readable findings

```json
[
  {"id": "DOC-01", "title": "CHANGELOG claims Poetry and a nonexistent CLI", "domain": "docs", "severity": "Low", "effort": "S", "files": ["CHANGELOG.md"], "evidence": "CHANGELOG.md:18 'Poetry package management'; 'CLI tool foundation' with no CLI in src", "recommendation": "Replace Poetry with uv and drop the CLI line until a CLI exists.", "cve": ""},
  {"id": "DOC-02", "title": "README presents unbuilt OCR service as built", "domain": "docs", "severity": "Medium", "effort": "M", "files": ["README.md", "CLAUDE.md"], "evidence": "README describes OCR service; src/ has only scaffolding; documented middleware import needs api extra", "recommendation": "Add a pre-alpha/scaffolding banner and mark API examples as needing the api extra.", "cve": ""},
  {"id": "DOC-03", "title": "Malformed uv command in README", "domain": "docs", "severity": "Low", "effort": "S", "files": ["README.md"], "evidence": "README.md:86 uv sync --all-extras,ml (invalid)", "recommendation": "Use uv sync --extra ml or --all-extras.", "cve": ""},
  {"id": "DOC-04", "title": "CLAUDE.md structure lists empty financial.py, omits api/", "domain": "docs", "severity": "Low", "effort": "S", "files": ["CLAUDE.md"], "evidence": "CLAUDE.md Project Structure lists financial.py (Decimal precision) which is empty; api/ not listed", "recommendation": "Update the structure block to match src/.", "cve": ""},
  {"id": "DOC-05", "title": "Planning docs and ADRs unwritten but linked", "domain": "docs", "severity": "Low", "effort": "M", "files": ["docs/planning/project-vision.md", "docs/planning/tech-spec.md", "docs/planning/roadmap.md", "docs/ADRs/"], "evidence": "planning/*.md:14 Awaiting Generation; ADRs only template", "recommendation": "Generate the docs or mark links as to-be-written.", "cve": ""}
]
```
