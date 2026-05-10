---
schema_type: common
title: "cookiecutter-python-template Defect Report"
status: published
owner: core-maintainer
tags:
  - template
  - compliance
  - documentation
  - analysis
purpose: "Tracks template-origin defects found in a freshly generated project for feedback to the template maintainers."
---

**Source project:** ByronWilliamsCPA/Unify (foundry_unify)
**Template version:** 0.1.0 (via cruft, `.cruft.json` commit ref)
**Discovered:** 2026-05-05, via full compliance audit across 8 domain agents
**Reporter:** Byron Williams / byronawilliams@gmail.com
**Template repo:** https://github.com/ByronWilliamsCPA/cookiecutter-python-template

This document captures every template-origin defect found during a compliance audit of a
freshly generated project. All items below are reproducible by generating a new project from
the template with the same context values — they are not developer errors.

Issues are grouped by priority and each includes the specific template file that needs
changing, the cookiecutter variable involved, and the concrete fix.

---

## Critical — Breaks the generated project immediately

---

### C-01: Dockerfile CMD references a module that the template does not generate

**Category:** Containerization
**Affected template file:** `{{cookiecutter.project_slug}}/Dockerfile` (line ~83)
**Cookiecutter variable:** `{{cookiecutter.project_slug}}`

**Issue:**
```dockerfile
CMD ["uvicorn", "{{cookiecutter.project_slug}}.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
No `main.py` is generated under `src/{{cookiecutter.project_slug}}/`. The container fails
to start with a `ModuleNotFoundError` on first deployment.

**Suggested fix:**
Either generate `src/{{cookiecutter.project_slug}}/main.py` with a minimal FastAPI app:
```python
from fastapi import FastAPI
from {{cookiecutter.project_slug}}.api.health import health_router

app = FastAPI(title="{{ cookiecutter.project_name }}")
app.include_router(health_router)
```
Or update the CMD to use a hook/entrypoint that is actually generated, or make the CMD
conditional on an `include_api` cookiecutter option.

---

### C-02: REUSE.toml annotates ODbL-1.0 but LICENSES/ODbL-1.0.txt is not generated

**Category:** Licensing / REUSE compliance
**Affected template file:** `{{cookiecutter.project_slug}}/REUSE.toml`,
`{{cookiecutter.project_slug}}/LICENSES/`

**Issue:**
`REUSE.toml` contains:
```toml
[[annotations]]
path = ["data/**", "models/**"]
SPDX-License-Identifier = "ODbL-1.0"
```
The `LICENSES/` directory does not include `ODbL-1.0.txt`. Running `reuse lint` fails
immediately with "Missing license file". The REUSE compliance workflow therefore cannot
pass, blocking the `reuse.yml` CI job on first push.

**Suggested fix:**
Add `LICENSES/ODbL-1.0.txt` to the template (full text of the Open Database License 1.0,
available at https://opendatacommons.org/licenses/odbl/1-0/). Alternatively, replace the
`ODbL-1.0` annotation with `CC0-1.0` (already present) if the template assumes data
directories will only hold placeholder files.

---

### C-03: sonar.organization uses `github_username` (personal) not `github_org`

**Category:** CI / SonarCloud configuration
**Affected template files:**
- `{{cookiecutter.project_slug}}/sonar-project.properties` (line 7)
- `{{cookiecutter.project_slug}}/.github/workflows/sonarcloud.yml` (line ~131)

**Issue:**
Both files emit `sonar.organization={{ cookiecutter.github_username }}`. When the project
belongs to a GitHub organization (not a personal account), this sends analysis to the wrong
SonarCloud org — causing silent failures or a 403 from the SonarCloud API. In this
project's case, the personal username `williaby` was used instead of the org
`byronwilliamscpa`, meaning no SonarCloud analysis has ever succeeded.

**Suggested fix:**
Add a separate `github_org` (or `sonarcloud_organization`) cookiecutter variable. Use it in
both files:
```
sonar.organization={{ cookiecutter.github_org | lower }}
```
Also add a `github_org` variable to `cookiecutter.json` with a default that prompts the
user to enter their org slug separately from their personal username.

---

### C-04: `semantic_release.template_dir` references a directory the template does not generate

**Category:** Release management
**Affected template file:** `{{cookiecutter.project_slug}}/pyproject.toml` (line ~749)

**Issue:**
```toml
[tool.semantic_release.changelog]
template_dir = "templates"
```
No `templates/` directory is generated. The first `semantic-release` run (whether local or
in CI) fails with a FileNotFoundError before producing any release.

**Suggested fix:**
Either generate a minimal `templates/` directory with a `CHANGELOG.md.j2` file, or remove
the `template_dir` setting entirely to fall back to the built-in changelog template.

---

## High — Incorrect output that will confuse users or break workflows

---

### H-01: CHANGELOG comparison links reference wrong owner and repo slug

**Category:** Documentation / Release management
**Affected template file:** `{{cookiecutter.project_slug}}/CHANGELOG.md` (last 2 lines)

**Issue:**
Generated links use `github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}`:
```
[Unreleased]: https://github.com/williaby/foundry_unify/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/williaby/foundry_unify/releases/tag/v0.1.0
```
Two bugs:
1. Uses personal `github_username` instead of `github_org`
2. Uses `project_slug` (underscored) instead of the actual GitHub `repo_name` (which may
   differ — `Unify` vs `foundry_unify`)

**Suggested fix:**
Add a `github_repo_name` variable (separate from `project_slug`) and use `github_org`:
```
[Unreleased]: https://github.com/{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}/compare/v0.1.0...HEAD
```

---

### H-02: README badge URLs use package slug not the GitHub repo name

**Category:** Documentation
**Affected template file:** `{{cookiecutter.project_slug}}/README.md` (badges section,
lines ~4-18)

**Issue:**
All CI/coverage/security badge URLs use `{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}`.
When the GitHub repo name differs from the package slug (common for org repos), all badges
return 404. In this project: badges reference `ByronWilliamsCPA/foundry_unify` but the
actual repo is `ByronWilliamsCPA/Unify`.

**Suggested fix:**
Use `{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}` in all badge URLs.
Apply same fix to the Scorecard badge, Codecov badge, and PyPI badge URLs.

---

### H-03: CHANGELOG [0.1.0] entry describes Poetry toolchain, not UV

**Category:** Documentation
**Affected template file:** `{{cookiecutter.project_slug}}/CHANGELOG.md`

**Issue:**
The generated 0.1.0 changelog entry reads:
> "Initial project structure with Poetry package management"
> "Poetry dependency management with lock file"

This project uses UV. Every generated project will have a false changelog entry on day one.

**Suggested fix:**
Replace with UV-accurate language:
> "Initial project structure with UV package management"
> "UV dependency management with `uv.lock` for reproducible installs"

---

### H-04: REUSE.toml copyright year is hardcoded to 2025, not interpolated from cookiecutter

**Category:** Licensing
**Affected template file:** `{{cookiecutter.project_slug}}/REUSE.toml`

**Issue:**
All `SPDX-FileCopyrightText` entries are hardcoded to `"2025 {{ cookiecutter.author_name }}"`.
Projects generated in 2026 or later will have incorrect copyright years. The `.cruft.json`
context captures `copyright_year` correctly (2026), but `REUSE.toml` ignores it.

**Suggested fix:**
Use the `copyright_year` cookiecutter variable:
```toml
SPDX-FileCopyrightText = "{{ cookiecutter.copyright_year }} {{ cookiecutter.author_name }}"
```
Apply same fix to `mkdocs.yml` copyright field (same hardcoded 2025 defect).

---

### H-05: `safety` dependency included despite pip-audit being the standard replacement

**Category:** Toolchain
**Affected template file:** `{{cookiecutter.project_slug}}/pyproject.toml`

**Issue:**
`safety>=3.7.0` appears in both the `dev` optional group and a `supply-chain` optional
group. The project's own standards (and the global CLAUDE.md) state that `safety` has been
replaced by `pip-audit`. Having both installed creates confusion about which tool is
authoritative and flags a manifest violation (TOOL-004).

**Suggested fix:**
Remove `safety` from all optional dependency groups. It is superseded by `pip-audit` which
is already present.

---

### H-06: `.gitignore` missing required entries for compliance tooling artifacts

**Category:** Configuration
**Affected template file:** `{{cookiecutter.project_slug}}/.gitignore`

**Issue:**
Two entries required by the compliance manifest are absent:
- `.worktrees/` — git worktree directories created during parallel development
- `docs/compliance-reports/` — output directory for compliance audit reports

Without these, developers will accidentally commit generated artifacts on first use.

**Suggested fix:**
Add to the generated `.gitignore`:
```
# Git worktrees
.worktrees/

# Compliance audit output
docs/compliance-reports/
```

---

### H-07: All pre-commit `rev:` fields use mutable version tags, not SHA pins

**Category:** Security / Supply chain
**Affected template file:** `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`

**Issue:**
All 7 repo blocks use mutable version tags (e.g. `rev: v4.5.0`, `rev: 1.7.10`). The
compliance manifest requires all `rev:` fields to be 40-character SHA pins. Unpinned
pre-commit hooks are a supply chain risk and also fail PC-012 on every generated project.

**Suggested fix:**
Resolve each tag to a SHA at template creation time (or in a post-generate hook) and embed
the SHA. Include the mutable tag as a comment:
```yaml
rev: "a1b2c3d4e5f6..."  # v4.5.0
```
Alternatively, add a `cookiecutter-post-generate` hook that runs `pre-commit autoupdate`
with SHA pinning, or document the pinning step as a mandatory setup step.

---

### H-08: Required pre-commit hooks absent: `detect-secrets`, `no-em-dash`, `commitizen`

**Category:** Security / Code quality
**Affected template file:** `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`

**Issue:**
Three hooks required by the manifest are absent:
- `detect-secrets` (PC-005, not override-eligible) — prevents credential commits
- `no-em-dash` (PC-011, not override-eligible) — enforces global writing standard
- `commitizen` (PC-008) — the existing `conventional-pre-commit` hook is not equivalent

**Suggested fix:**
Add all three repo blocks to the generated `.pre-commit-config.yaml`. For `detect-secrets`,
also generate an initial `.secrets.baseline` file (via a post-generate hook running
`detect-secrets scan > .secrets.baseline`).

---

### H-09: `dependabot.yml` pip ecosystem cannot resolve `uv.lock`

**Category:** CI / Dependency management
**Affected template file:** `{{cookiecutter.project_slug}}/.github/dependabot.yml`

**Issue:**
Generated `dependabot.yml` configures `package-ecosystem: "pip"`. Dependabot's pip
ecosystem reads `requirements.txt`, not `uv.lock`. The dependency update workflow is
therefore non-functional from day one. Additionally, `renovate.json` is also generated,
creating a duplicate update tool conflict (CI-021).

**Suggested fix:**
Remove `dependabot.yml` entirely — `renovate.json` (already generated) handles Python
dependency updates via `uv.lock`. If Dependabot is preferred, add native `uv` ecosystem
support when Dependabot adds it. In the meantime, the `github-actions` ecosystem entry in
`dependabot.yml` is still functional and can be kept if desired, but the `pip` entry should
be removed.

---

### H-10: `sonarcloud.yml` quality gate step has `continue-on-error: true`

**Category:** CI / Security gate
**Affected template file:** `{{cookiecutter.project_slug}}/.github/workflows/sonarcloud.yml`

**Issue:**
The `sonarsource/sonarqube-quality-gate-action` step has `continue-on-error: true`,
allowing the quality gate to fail silently without blocking the workflow. This defeats the
purpose of having a quality gate.

**Suggested fix:**
Remove `continue-on-error: true` from the quality gate step. If non-blocking reporting is
needed, restructure using `if: failure()` in a subsequent reporting step rather than
suppressing the failure.

---

### H-11: `pyproject.toml` is missing a `[project.urls]` table

**Category:** Package metadata
**Affected template file:** `{{cookiecutter.project_slug}}/pyproject.toml`

**Issue:**
No `[project.urls]` table is generated. PyPI uses this table to display repository,
documentation, and issue tracker links on the package page. Every generated package will
have an empty links section on PyPI.

**Suggested fix:**
Add a `[project.urls]` table using the `github_org` and `github_repo_name` variables:
```toml
[project.urls]
Homepage = "https://github.com/{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}"
Repository = "https://github.com/{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}"
Documentation = "https://{{ cookiecutter.github_repo_name | lower }}.readthedocs.io"
"Bug Tracker" = "https://github.com/{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}/issues"
```

---

### H-12: `pyproject.toml` classifiers list only one Python version despite a multi-version matrix

**Category:** Package metadata
**Affected template file:** `{{cookiecutter.project_slug}}/pyproject.toml`

**Issue:**
Generated classifiers include only `"Programming Language :: Python :: {{ cookiecutter.python_version }}"`.
The `requires-python = ">=3.10,<3.15"` field spans five minor versions, but none of the
others appear in classifiers. PyPI filters by classifier, so users searching for 3.10 or
3.11 support will not find the package.

**Suggested fix:**
Either generate classifiers for each version in the supported range (expandable via a
cookiecutter choice variable for `min_python_version`) or add all currently supported minor
versions statically. Minimum addition: `3 :: Only` and the two to three most common
versions in the range.

---

### H-13: `README.md` contains unresolved `YourModule` placeholder

**Category:** Documentation
**Affected template files:** `{{cookiecutter.project_slug}}/README.md`,
`{{cookiecutter.project_slug}}/CONTRIBUTING.md`

**Issue:**
Code examples in both files reference `from your_package import YourModule` — a generic
placeholder that was never replaced with a real exported symbol. Every generated project
ships with non-functional usage examples.

**Suggested fix:**
Replace `YourModule` with `{{ cookiecutter.project_slug | title }}` or a more descriptive
example using an actual generated class (e.g., the `Settings` class from
`{{cookiecutter.project_slug}}.core.config` which is always generated). Alternatively,
remove the import example and replace with a CLI invocation example if the package is a
service rather than a library.

---

### H-14: `mkdocs.yml` copyright year hardcoded to 2025

**Category:** Documentation configuration
**Affected template file:** `{{cookiecutter.project_slug}}/mkdocs.yml`

**Issue:**
`copyright: Copyright &copy; 2025 {{ cookiecutter.author_name }}` — same defect as REUSE.toml.
Projects generated after 2025 show a stale copyright year in all documentation pages.

**Suggested fix:**
```yaml
copyright: "Copyright &copy; {{ cookiecutter.copyright_year }} {{ cookiecutter.author_name }}"
```

---

### H-15: `mkdocs.yml` `repo_name` uses package slug not GitHub repo name

**Category:** Documentation configuration
**Affected template file:** `{{cookiecutter.project_slug}}/mkdocs.yml`

**Issue:**
`repo_name: {{ cookiecutter.github_org }}/{{ cookiecutter.project_slug }}` uses the
Python package slug (underscored) instead of the GitHub repo name. When these differ, the
Material theme displays a broken label and the "Edit on GitHub" link resolves to a
non-existent repo path.

**Suggested fix:**
```yaml
repo_url: "https://github.com/{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}"
repo_name: "{{ cookiecutter.github_org }}/{{ cookiecutter.github_repo_name }}"
```

---

### H-16: `.infisical.json` committed with empty `workspaceId`

**Category:** Secrets management
**Affected template file:** `{{cookiecutter.project_slug}}/.infisical.json`

**Issue:**
```json
{ "workspaceId": "" }
```
A committed `.infisical.json` with an empty `workspaceId` is non-functional — the Infisical
CLI will refuse to inject secrets. Committing this file also pollutes git history with an
artifact that should be machine-local (initialized by `infisical init`).

**Suggested fix:**
Add `.infisical.json` to the generated `.gitignore` and document the `infisical init` step
in `README.md` under "Local development setup". If the workspace ID is always known at
project creation time, make it a cookiecutter variable.

---

## Medium — Quality and completeness gaps

---

### M-01: Dockerfile copies `uv:latest` — non-reproducible builds

**Category:** Containerization
**Affected template file:** `{{cookiecutter.project_slug}}/Dockerfile`

**Issue:**
```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```
`:latest` resolves to a different binary on every build, silently breaking reproducibility.

**Suggested fix:**
Pin to a specific version tag (e.g. `uv:0.6.14`) and update via Renovate. The version
should ideally be a cookiecutter variable or specified in `pyproject.toml` so it can be
kept in sync with the local uv version.

---

### M-02: Dockerfile base image uses floating `python:3.12-slim` tag

**Category:** Containerization
**Affected template file:** `{{cookiecutter.project_slug}}/Dockerfile`

**Issue:**
`FROM python:3.12-slim` is a mutable tag. Patch releases update the underlying image
without changing the tag. Production builds become non-reproducible and vulnerability fixes
in the base image are silently applied (or not) depending on cache state.

**Suggested fix:**
Pin by digest in the template:
```dockerfile
FROM python:{{ cookiecutter.python_version }}-slim@sha256:<current-digest>
```
Or generate a `Makefile`/`Taskfile` target that resolves and updates the digest, and
document the pinning update process in `CONTRIBUTING.md`.

---

### M-03: `docker-compose.yml` uses deprecated top-level `version:` key

**Category:** Containerization
**Affected template files:** `{{cookiecutter.project_slug}}/docker-compose.yml`,
`{{cookiecutter.project_slug}}/docker-compose.prod.yml`

**Issue:**
```yaml
version: '3.9'
```
Docker Compose v2 (the current GA release) ignores this key and emits a deprecation
warning. The Compose specification no longer requires it.

**Suggested fix:**
Remove the `version:` key from both files entirely.

---

### M-04: `pyproject.toml` keywords field is empty

**Category:** Package metadata
**Affected template file:** `{{cookiecutter.project_slug}}/pyproject.toml`

**Issue:**
```toml
keywords = []
```
Empty keywords reduces PyPI discoverability.

**Suggested fix:**
Either prompt for keywords as a cookiecutter variable, or populate from the project
description using a Jinja2 split, or simply remove the line so PyPI omits the field rather
than showing it empty.

---

### M-05: README pytest coverage commands inconsistent with `src/` layout

**Category:** Documentation
**Affected template files:** `{{cookiecutter.project_slug}}/README.md`,
`{{cookiecutter.project_slug}}/CONTRIBUTING.md`

**Issue:**
Multiple places show `--cov={{ cookiecutter.project_slug }}` (no `src/` prefix). The
generated `pyproject.toml` `addopts` uses `--cov=src/{{ cookiecutter.project_slug }}`.
Running the README commands produces a coverage report with zero coverage.

**Suggested fix:**
Update all coverage command examples in README and CONTRIBUTING to use
`--cov=src/{{ cookiecutter.project_slug }}`, or rely on the configured `addopts` and
document that `uv run pytest` without flags is sufficient.

---

### M-06: `docs/template_feedback.md` retains `__PROJECT_CREATION_DATE__` placeholder

**Category:** Documentation
**Affected template file:** `{{cookiecutter.project_slug}}/docs/template_feedback.md`

**Issue:**
```
**Project Created**: __PROJECT_CREATION_DATE__
```
This placeholder is never resolved by cookiecutter, leaving every generated project with a
literal `__PROJECT_CREATION_DATE__` string in the file.

**Suggested fix:**
Replace with `{{ cookiecutter.project_creation_date }}` and add `project_creation_date` to
`cookiecutter.json` with a default that uses the current date (ideally via a
pre-generate hook using `datetime.now().strftime('%Y-%m-%d')`).

---

### M-07: `CHANGELOG.md` initial release date is "TBD"

**Category:** Documentation
**Affected template file:** `{{cookiecutter.project_slug}}/CHANGELOG.md`

**Issue:**
```markdown
## [0.1.0] - TBD
```
Projects are immediately committed with a non-date changelog entry, confusing changelog
tooling and readers.

**Suggested fix:**
Replace `TBD` with `{{ cookiecutter.copyright_year }}-{{ cookiecutter.project_creation_month_day }}`
or use a pre-generate hook to set the date. The simplest approach: replace `TBD` with the
value of a `project_creation_date` variable (same fix as M-06).

---

### M-08: Required project files absent from generated output

**Category:** Structure / Compliance
**Affected template:** Missing generated files

**Issue:**
Three files required by the compliance manifest are not generated:
- `docs/known-vulnerabilities.md` — required for pip-audit gap tracking
- `AGENTS.md` (at project root) — required for agent catalog reference
- `GEMINI.md` (at project root) — required for Gemini CLI project context

**Suggested fix:**
Add minimal generated versions of all three. `docs/known-vulnerabilities.md` should use
a standard template structure (header + empty table + instructions). `AGENTS.md` and
`GEMINI.md` can be minimal stubs that link to the global catalog.

---

### M-09: `CLAUDE.md` references `safety check` (removed tool)

**Category:** Documentation / Toolchain
**Affected template file:** `{{cookiecutter.project_slug}}/CLAUDE.md`

**Issue:**
Two occurrences of `safety check` appear in the generated `CLAUDE.md` (in the security
suggestions section and the pre-commit checklist). `safety` has been replaced by `pip-audit`
as the standard dependency scanner and is no longer in the generated dev dependencies.

**Suggested fix:**
Replace both occurrences with `uv run pip-audit`.

---

### M-10: `CLAUDE.md` missing Model Selection section

**Category:** Developer tooling
**Affected template file:** `{{cookiecutter.project_slug}}/CLAUDE.md`

**Issue:**
The global CLAUDE.md standard requires a "Model Selection" section mapping task types to
Claude model tiers (Opus/Sonnet/Haiku). This section is absent from the generated project
`CLAUDE.md`.

**Suggested fix:**
Add a `## Model Selection` section with the standard three-row table to the generated
`CLAUDE.md`. The content is identical for all projects.

---

### M-11: `.claude/settings.json` not generated

**Category:** Developer tooling
**Affected template:** Missing generated file

**Issue:**
The compliance standard (CLAUDE-005) requires `.claude/settings.json` with a permissions
block. The template generates `.claude/settings.local.json.example` but not
`settings.json`.

**Suggested fix:**
Generate `.claude/settings.json` with a minimal stub:
```json
{
  "permissions": {
    "allow": []
  }
}
```
Populate `allow` entries based on which tools the project is expected to use (can be driven
by cookiecutter options like `include_docker`, `include_database`, etc.).

---

### M-12: `.qlty/qlty.toml` missing required `[plugins]` block

**Category:** Toolchain / Code quality
**Affected template file:** `{{cookiecutter.project_slug}}/.qlty/qlty.toml`

**Issue:**
The generated `.qlty/qlty.toml` uses `config_version = "0"` with `[smells]` blocks but
has no `[plugins]` section. The manifest requires `[plugins] enabled = [...]` to explicitly
declare which tools Qlty runs.

**Suggested fix:**
Add to the generated `qlty.toml`:
```toml
[plugins]
enabled = ["ruff", "basedpyright", "bandit"]
```

---

## Low — Polish and minor corrections

---

### L-01: `README.md` references `.claude/claude.md` (lowercase) instead of `CLAUDE.md`

**Category:** Documentation
**Affected template file:** `{{cookiecutter.project_slug}}/README.md`

**Issue:**
The "Claude Code Standards" section references `.claude/claude.md` (a subtree path and
lowercase name). The actual file is `CLAUDE.md` at the project root.

**Suggested fix:**
Update the README reference to `CLAUDE.md` (project root, uppercase).

---

### L-02: `tests/integration/` directory contains no tests

**Category:** Testing
**Affected template:** `{{cookiecutter.project_slug}}/tests/integration/__init__.py`

**Issue:**
The integration directory is created but contains only a docstring placeholder. The CI
`run-integration-tests: true` option passes vacuously. Coverage thresholds are met only by
unit tests, giving a false impression of integrated test coverage.

**Suggested fix:**
Generate at minimum one smoke-test in `tests/integration/test_smoke.py` that imports the
package and verifies the module loads without error:
```python
def test_package_importable() -> None:
    import {{ cookiecutter.project_slug }}
    assert {{ cookiecutter.project_slug }}.__version__
```

---

### L-03: `docs/planning/README.md` status table uses wrong date format

**Category:** Documentation
**Affected template file:** `{{cookiecutter.project_slug}}/docs/planning/README.md`

**Issue:**
The status table lists planning documents as "Awaiting Generation" — a state that is only
valid before `/plan` is run. This is accurate at generation time but looks like a stale
placeholder on day one.

**Suggested fix:**
Document in the template README that the status will be "Awaiting Generation" until the
project planning skill is run, and provide the command to do so prominently.

---

## Variable / Context Gaps (proposed new cookiecutter.json entries)

The following variables are referenced inconsistently or should be added to the template:

| Variable | Current state | Suggested addition |
|---|---|---|
| `github_repo_name` | Missing — project uses `project_slug` everywhere | Add; default to `project_slug` but allow override |
| `github_org` | Missing — template uses `github_username` for org contexts | Add; separate from personal username |
| `sonarcloud_organization` | Present but defaults to `github_username` | Default to `github_org` instead |
| `copyright_year` | Present in cruft context but not used in REUSE.toml or mkdocs.yml | Wire up to template variables |
| `project_creation_date` | Missing | Add via pre-generate hook (auto-set, not prompted) |

---

## Summary Counts

| Priority | Count |
|---|---|
| Critical | 4 |
| High | 16 |
| Medium | 12 |
| Low | 3 |
| **Total** | **35** |

All 35 items were found in a single freshly generated project without any application code
written. Every item is reproducible by generating a new project from the same template.
