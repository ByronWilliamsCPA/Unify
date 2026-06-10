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
> **Project Created**: __PROJECT_CREATION_DATE__

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

### Phantom CLI tests reference a non-existent `cli` module

- **Priority**: High
- **Category**: Tooling / CI/CD
- **Discovered**: 2026-05-28

**Issue**: `tests/test_example.py` ships a `TestCLI` class (12 tests) that imports
`foundry_unify.cli`, but the template generates no `cli` module and no
`[project.scripts]` console entry point. Every CLI test fails with
`ModuleNotFoundError: No module named '<package>.cli'`, and the dead code drags
total coverage well below the enforced 80% gate.

**Context**: Discovered while bringing CI to green. The org reusable CI workflow
never ran tests (it was failing at `startup_failure` for unrelated input-schema
reasons), so the broken CLI tests had been masked since project creation.

**Suggested Fix**: Either (a) gate the CLI scaffolding behind a cookiecutter
option (`include_cli`) that generates both the `cli` module and its tests
together, or (b) drop the CLI tests from the default `test_example.py` so
service-style projects without a CLI start green.

**Affected Files**: `{{cookiecutter.package_name}}/tests/test_example.py`,
`pyproject.toml` (`[project.scripts]`)

### Initial reusable-workflow callers pass inputs the org workflows no longer accept

- **Priority**: Critical
- **Category**: CI/CD
- **Discovered**: 2026-05-28

**Issue**: The generated `.github/workflows/ci.yml` passes
`enable-sonarcloud`, `sonarcloud-organization`, `sonarcloud-project-key`,
`enable-codecov`, and a `secrets:` block to `python-ci.yml@main`, and
`security-analysis.yml` passes `run-safety`. The org reusable workflows removed
these inputs/secrets, so every run fails at `startup_failure` (workflow-call
validation) on a freshly generated project.

**Context**: All CI was red from project creation; the failure mode (no logs,
parse-time rejection) made it look like an infra outage rather than a stale
caller contract.

**Suggested Fix**: Pin the caller workflows to the same org-workflow SHA the
template was validated against, and remove inputs/secrets the current org
workflows do not declare. Add a template CI smoke test that calls the org
workflows to catch contract drift.

**Affected Files**: `.github/workflows/ci.yml`,
`.github/workflows/security-analysis.yml`

---

### ADR template fails the template's own front matter validator

- **Priority**: Medium
- **Category**: Tooling
- **Discovered**: 2026-06-09

**Issue**: `docs/ADRs/adr-template.md` ships with `schema_type: adr`, but the
front matter contract in `tools/frontmatter_contract/models.py` only defines
`common`, `script`, `knowledge`, and `planning`. The `validate-front-matter`
pre-commit hook therefore fails on a freshly generated project the first time
any commit stages a file under `docs/`.

**Context**: Discovered while committing an unrelated docs change; the hook
uses `pass_filenames: false` and scans the whole `docs/` tree, so the
pre-existing template defect blocked the commit.

**Suggested Fix**: Either add an `AdrFM` schema to the contract (the template
already carries `component` and `source`, so it could subclass `PlanningFM`)
or ship the ADR template with `schema_type: planning`. Note the template also
uses ADR-vocabulary `status: proposed`, which the common schema rejects
(allowed: `draft`, `in-review`, `published`); a dedicated `AdrFM` schema
should carry the ADR status vocabulary (proposed/accepted/deprecated/
superseded). Also consider making the validator respect gitignored paths so
local-only notes under `docs/` do not fail validation.

**Affected Files**: `docs/ADRs/adr-template.md`,
`tools/frontmatter_contract/models.py`, `tools/validate_front_matter.py`

---

## Submitting Feedback

Once you've collected feedback, you can:

1. **Create an issue** in the [cookiecutter-python-template repository](https://github.com/ByronWilliamsCPA/cookiecutter-python-template/issues)
2. **Submit a PR** if you have fixes for the template
3. **Share this file** with the template maintainers

When submitting, reference this project as the source of the feedback.
