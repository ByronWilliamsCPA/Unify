---
title: "Template Feedback"
schema_type: common
status: published
owner: core-maintainer
purpose: "Document template issues for upstream fixes."
tags:
  - feedback
  - template
---

> **Purpose**: Document issues discovered in this project that should be addressed in the [cookiecutter-python-template](https://github.com/ByronWilliamsCPA/cookiecutter-python-template).
>
> **Generated From**: cookiecutter-python-template v0.1.0
> **Project Created**: 2026-05-05

---

## How to Use This File

When working on this project, if you discover any issue that originates from the template itself (not project-specific), add it here with the following format:

```markdown
### [Short Title]

- **Priority**: Critical / High / Medium / Low
- **Category**: [Configuration / Documentation / Tooling / Structure / CI/CD / Security / Other]
- **Discovered**: YYYY-MM-DD

**Issue**: [Clear description of what's wrong or missing]

**Context**: [How was this discovered? What were you trying to do?]

**Suggested Fix**: [What should the template do differently?]

**Affected Files**: [List template files that need changes]
```

---

## Feedback Items

<!-- Add your feedback below this line -->

### C-01: Dockerfile CMD References Non-Existent main.py

- **Priority**: Critical
- **Category**: Structure
- **Discovered**: 2026-05-05

**Issue**: The generated Dockerfile contains `CMD ["uvicorn", "foundry_unify.main:app", ...]` but no `src/foundry_unify/main.py` file is generated. The container cannot start.

**Context**: Discovered during compliance audit when checking container startup behavior.

**Suggested Fix**: Generate a minimal `src/${project_slug}/main.py` with a basic FastAPI app skeleton, or update the CMD to reference an actual generated entry point.

**Affected Files**: `{{cookiecutter.project_slug}}/Dockerfile`, requires new file `src/{{cookiecutter.project_slug}}/main.py`

---

### C-02: ODbL-1.0.txt Missing from LICENSES/

- **Priority**: Critical
- **Category**: Configuration
- **Discovered**: 2026-05-05

**Issue**: `REUSE.toml` references `ODbL-1.0` for data/ and models/ paths but `LICENSES/ODbL-1.0.txt` is not generated. REUSE lint fails with "Missing license file".

**Context**: Discovered when running `reuse lint` during compliance audit.

**Suggested Fix**: Add `LICENSES/ODbL-1.0.txt` to the template. Fetch from SPDX: https://raw.githubusercontent.com/spdx/license-list-data/main/text/ODbL-1.0.txt

**Affected Files**: `{{cookiecutter.project_slug}}/REUSE.toml`, requires new file `LICENSES/ODbL-1.0.txt`

---

### C-03: sonar.organization Uses github_username Not github_org

- **Priority**: Critical
- **Category**: Configuration
- **Discovered**: 2026-05-05

**Issue**: Both `sonar-project.properties` and `.github/workflows/sonarcloud.yml` use `{{cookiecutter.github_username}}` for `sonar.organization`, but SonarCloud organizations must match the GitHub org slug (e.g., `byronwilliamscpa`), not the personal username (e.g., `williaby`).

**Context**: Discovered during compliance audit; SonarCloud returned project-not-found errors.

**Suggested Fix**: Add a `github_org` or `sonarcloud_organization` variable to cookiecutter.json, separate from `github_username`. Default it to `github_username` for backwards compat. Use it in all sonar.organization references.

**Affected Files**: `sonar-project.properties`, `.github/workflows/sonarcloud.yml`

---

### C-04: semantic_release template_dir References Non-Existent templates/ Directory

- **Priority**: Critical
- **Category**: Configuration
- **Discovered**: 2026-05-05

**Issue**: `pyproject.toml` under `[tool.semantic_release.changelog]` sets `template_dir = "templates"` but no `templates/` directory is generated. python-semantic-release raises FileNotFoundError on release runs.

**Context**: Discovered during compliance audit static analysis of pyproject.toml.

**Suggested Fix**: Either generate a minimal `templates/` directory with a default changelog template, or remove `template_dir` from the generated `pyproject.toml` to use semantic-release defaults.

**Affected Files**: `{{cookiecutter.project_slug}}/pyproject.toml`

---

### H-01: CHANGELOG.md Contains Wrong Org and Repo Slug in Links

- **Priority**: High
- **Category**: Documentation
- **Discovered**: 2026-05-05

**Issue**: Footer links in the generated `CHANGELOG.md` use `https://github.com/{{cookiecutter.github_username}}/{{cookiecutter.project_slug}}` instead of `https://github.com/{{cookiecutter.github_org}}/{{cookiecutter.repo_name}}`. This breaks when the repo name differs from the project slug (e.g., repo is `Unify`, slug is `foundry_unify`).

**Context**: Discovered during compliance audit; links 404.

**Suggested Fix**: Introduce `github_org` and `github_repo_name` cookiecutter variables. Use `github_repo_name` (not `project_slug`) for all GitHub URLs.

**Affected Files**: `CHANGELOG.md`

---

### H-02: CHANGELOG.md References Poetry Instead of UV

- **Priority**: High
- **Category**: Documentation
- **Discovered**: 2026-05-05

**Issue**: The generated CHANGELOG.md v0.1.0 entry mentions "Poetry package management" but the project uses UV.

**Context**: Template appears to have been originally designed for Poetry and incompletely migrated to UV.

**Suggested Fix**: Update all CHANGELOG.md content references to use UV terminology.

**Affected Files**: `CHANGELOG.md`

---

### H-03: All README Badge URLs Reference project_slug Not github_repo_name

- **Priority**: High
- **Category**: Documentation
- **Discovered**: 2026-05-05

**Issue**: All GitHub Actions badges in README.md use `{{cookiecutter.github_username}}/{{cookiecutter.project_slug}}` which produces incorrect URLs when the actual repository name differs from the Python package slug.

**Context**: Discovered during compliance audit; all badges showed 404.

**Suggested Fix**: Use `{{cookiecutter.github_org}}/{{cookiecutter.github_repo_name}}` in badge URLs.

**Affected Files**: `README.md`

---

### H-04: REUSE.toml Copyright Year is Static 2025

- **Priority**: High
- **Category**: Configuration
- **Discovered**: 2026-05-05

**Issue**: All `SPDX-FileCopyrightText` entries in the generated `REUSE.toml` are hardcoded to `2025 {{cookiecutter.author_name}}`. Projects created in 2026+ will have incorrect copyright years.

**Context**: Discovered during compliance audit; project was created in 2026 but copyright shows 2025.

**Suggested Fix**: Add a `project_creation_year` cookiecutter variable (or use a pre-generate hook to set it from `datetime.now().year`). Use it in REUSE.toml.

**Affected Files**: `REUSE.toml`

---

### H-05: Dependabot.yml Conflicts With Renovate

- **Priority**: High
- **Category**: CI/CD
- **Discovered**: 2026-05-05

**Issue**: The template generates both `.github/dependabot.yml` and `renovate.json`. Running both causes duplicate PRs. Dependabot also cannot parse `uv.lock` files, so its pip entries are effectively useless.

**Context**: Discovered during compliance audit when checking CI-021.

**Suggested Fix**: Remove `.github/dependabot.yml` from the template if `renovate.json` is generated. Add a cookiecutter choice variable (`dependency_manager: [renovate, dependabot]`) if both should remain supported.

**Affected Files**: `.github/dependabot.yml`, `renovate.json`

---

### M-01: pre-commit-config.yaml Uses Mutable Tag Revs

- **Priority**: Medium
- **Category**: Security
- **Discovered**: 2026-05-05

**Issue**: All 7 `rev:` fields in the generated `.pre-commit-config.yaml` use mutable version tags (e.g., `v4.5.0`) rather than SHA pins. This violates the Scorecard Pinned-Dependencies check.

**Context**: Discovered during OpenSSF Scorecard compliance check.

**Suggested Fix**: Pre-compute SHA pins for all hooks and embed them in the template at generation time. Alternatively, add a post-generate hook that runs `pre-commit autoupdate --freeze` to pin SHAs.

**Affected Files**: `.pre-commit-config.yaml`

---

### M-02: GitHub Actions Uses Mutable Refs Not SHA Pins

- **Priority**: Medium
- **Category**: Security
- **Discovered**: 2026-05-05

**Issue**: All 19 `uses:` references in generated workflow files use version tags or branch names (e.g., `@v4`, `@main`) instead of full commit SHAs. This fails the OpenSSF Scorecard Pinned-Dependencies check.

**Context**: Discovered during CI-005 compliance check.

**Suggested Fix**: Pre-compute SHA pins for all actions at template generation time. Add a post-generate hook that uses `pip install pin-github-action && pin-github-action .github/workflows/` to pin all SHAs automatically.

**Affected Files**: All `.github/workflows/*.yml` files

---

### M-03: pyproject.toml classifiers Lists Only Python 3.12

- **Priority**: Medium
- **Category**: Configuration
- **Discovered**: 2026-05-05

**Issue**: The generated `pyproject.toml` only lists `Programming Language :: Python :: 3.12` in classifiers despite `requires-python = ">=3.10,<3.15"`. This misrepresents supported versions on PyPI.

**Context**: Discovered during TOOL-* compliance checks.

**Suggested Fix**: Generate classifiers for the full Python version range matching `requires-python`. Use a cookiecutter post-generate hook or a TOML template loop to generate all supported versions.

**Affected Files**: `pyproject.toml`

---

### M-04: detect-secrets Baseline Not Generated

- **Priority**: Medium
- **Category**: Security
- **Discovered**: 2026-05-05

**Issue**: The `detect-secrets` pre-commit hook is missing from the generated `.pre-commit-config.yaml`, and no `.secrets.baseline` file is generated.

**Context**: Discovered during PC-005 compliance check.

**Suggested Fix**: Add `detect-secrets` to `.pre-commit-config.yaml` and add a post-generate hook that runs `detect-secrets scan > .secrets.baseline` to initialize the baseline.

**Affected Files**: `.pre-commit-config.yaml`, requires new file `.secrets.baseline`

---

### L-01: REUSE.toml References Non-Existent poetry.lock and requirements/

- **Priority**: Low
- **Category**: Configuration
- **Discovered**: 2026-05-05

**Issue**: The generated `REUSE.toml` includes `"poetry.lock"` and `"requirements/**/*.txt"` in its path annotations, but these files are never generated (project uses UV). This causes REUSE lint warnings about annotating non-existent paths.

**Context**: Discovered during REUSE lint during compliance audit.

**Suggested Fix**: Remove `poetry.lock` and `requirements/**/*.txt` from the generated REUSE.toml. Add `uv.lock` instead.

**Affected Files**: `REUSE.toml`


---

## Submitting Feedback

Once you've collected feedback, you can:

1. **Create an issue** in the [cookiecutter-python-template repository](https://github.com/ByronWilliamsCPA/cookiecutter-python-template/issues)
2. **Submit a PR** if you have fixes for the template
3. **Share this file** with the template maintainers

When submitting, reference this project as the source of the feedback.
