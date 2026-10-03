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

### Required-check workflows lack `on: merge_group`, deadlocking a merge queue

- **Priority**: High
- **Category**: CI/CD
- **Discovered**: 2026-10-02

**Issue**: The generated `ci.yml`, `pr-validation.yml`, `reuse.yml` and
`security-analysis.yml` trigger only on `pull_request` and `push`. When a branch
ruleset requires those checks and enables the merge queue, the queue creates a
`gh-readonly-queue/...` ref and waits for the required checks to report on it.
No workflow runs for the `merge_group` event, so the checks never report and the
queued PR stalls until it times out. With no bypass actor configured, nothing
can unstick it. `pr-validation.yml` also keys its concurrency group on
`github.event.pull_request.number`, which is null under `merge_group`, so every
merge-group run would share one group and cancel the others.

**Context**: Found while preparing the fleet keystone PR (#45) for a merge
queue. The fix added `merge_group:` to all four workflows and changed the
concurrency group to `pr-validation-${{ github.event.pull_request.number ||
github.ref }}`.

**Suggested Fix**: Ship `merge_group:` in the `on:` block of every workflow whose
job is a required status check, and make any concurrency group that references
`github.event.pull_request.*` fall back to `github.ref`. Add a template lint that
fails when a required-check workflow omits `merge_group`.

**Affected Files**: `.github/workflows/ci.yml`,
`.github/workflows/pr-validation.yml`, `.github/workflows/reuse.yml`,
`.github/workflows/security-analysis.yml`

### Pre-commit ruff rev and Dockerfile digests go stale; Renovate does not manage them

- **Priority**: Medium
- **Category**: Tooling / CI/CD
- **Discovered**: 2026-10-02

**Issue**: The template pins `astral-sh/ruff-pre-commit` to an arbitrary old
`rev` (v0.9.0 here) that is unrelated to the ruff version resolved in `uv.lock`.
The two drift apart, so the pre-commit hook and CI disagree about which rules
exist: v0.9.0 still raised A005 for submodules named after stdlib modules, a
rule ruff has since narrowed, and pre-commit failed on code that `ruff check`
accepted. Nothing updates the hook rev afterwards, because the shipped
`renovate.json` sets `enabledManagers` to `["pep621", "github-actions"]`, which
excludes the `pre-commit` and `dockerfile` managers. The pre-commit hook revs
and the Dockerfile base-image digests therefore go stale with no PR ever
opened.

**Context**: Found while aligning the toolchain on the fleet keystone PR (#45):
the hook rev had to be bumped by hand to match `uv.lock`, and the Chainguard
base-image digests in the Dockerfile were already out of date.

**Suggested Fix**: Add `pre-commit` and `dockerfile` to `enabledManagers` in
`renovate.json` (with digest pinning for Docker images), and add a CI or
pre-commit check that fails when the ruff-pre-commit `rev` differs from the ruff
version in `uv.lock`. Initialize the hook rev to the same ruff version as the
generated lockfile.

**Affected Files**: `renovate.json`, `.pre-commit-config.yaml`, `Dockerfile`

### Shipped `osv-scanner.toml` carries an ignore for a withdrawn advisory

- **Priority**: Medium
- **Category**: Security / CI/CD
- **Discovered**: 2026-10-02

**Issue**: The template's `osv-scanner.toml` ships `[[IgnoredVulns]]` entries
for CVE-2022-42969, PYSEC-2022-42969 and GHSA-w596-4wvx-j9j6 (the disputed `py`
ReDoS via interrogate). OSV later withdrew that advisory, and osv-scanner exits
non-zero on ignore entries that no longer match anything ("has unused
ignores"), so the scan fails on a freshly generated project through no fault of
the project's dependencies. The matching `[tool.pip-audit].ignore-vuln` entry
had the same problem.

**Context**: Found when the OSV scan failed on the fleet keystone PR (#45) with
no dependency change. The fix removed all three ignores and the pip-audit entry
and recorded the history in `docs/known-vulnerabilities.md`.

**Suggested Fix**: Ship `osv-scanner.toml` and `[tool.pip-audit].ignore-vuln`
with no pre-populated advisory ignores, only the commented format example.
Document that every ignore needs a matching `docs/known-vulnerabilities.md`
entry and must be removed when the advisory is withdrawn or fixed; consider a
scheduled job that runs osv-scanner and flags unused ignores early.

**Affected Files**: `osv-scanner.toml`, `pyproject.toml`
(`[tool.pip-audit]`), `docs/known-vulnerabilities.md`

---

### `REUSE.toml` does not annotate `.mcp.json`

- **Priority**: Low
- **Category**: Licensing / Tooling
- **Discovered**: 2026-10-03

**Issue**: The template's `REUSE.toml` CC0-1.0 config block covers `*.toml`,
`*.yml`, `*.yaml` and named dotfiles, but not `.mcp.json`. Adding the standard
Claude Code project MCP config makes `reuse lint` fail, which blocks the
required "Check REUSE Compliance" check.

**Context**: Found when PR #41 added `.mcp.json` (context7 and sonarqube
servers) and the REUSE check failed with no other change.

**Suggested Fix**: Add `".mcp.json"` to the CC0-1.0 config path list in the
template's `REUSE.toml`, or ship the `.mcp.json` the fleet standard expects so
the annotation and the file arrive together.

**Affected Files**: `REUSE.toml`

---

### Template ships a duplicate `python-ci.yml` call and a gate job coupled to it

- **Priority**: High
- **Category**: CI/CD
- **Discovered**: 2026-10-03

**Issue**: The template's `pr-validation.yml` calls the org-level
`python-ci.yml` reusable through a `core-validation` job, and `ci.yml` calls the
same reusable through its `ci` job. Every pull request therefore runs the full
Python CI (quality, unit, integration, security tests, coverage, LLM
governance, matrix) twice. The `Dependency & Standards Validation` gate in
`pr-validation.yml` lists `core-validation` in `needs:` and its only `exit 1`
keys off that job's result, so removing the duplicate job also removes the
gate's only failure path unless the gate is rewritten at the same time.

**Context**: Found while removing the duplicate call in PR #46. Review showed
that dropping `core-validation` left a required check that could never fail,
and that the header comment overstated enforcement.

**Suggested Fix**: Call `python-ci.yml` from `ci.yml` only. Keep
`pr-validation.yml` for supplementary checks (dead code, link check) and have
its gate job exit 1 unless every job in `needs:` reports `success` (same
pattern as the `CI Gate` job in `ci.yml`), so the gate fails closed on infra
failure, cancellation or skip. Do not let a vulture crash pass as "no dead
code": treat exit codes of 2 or more as failures.

**Affected Files**: `.github/workflows/pr-validation.yml`,
`.github/workflows/ci.yml`

---

## Submitting Feedback

Once you've collected feedback, you can:

1. **Create an issue** in the [cookiecutter-python-template repository](https://github.com/ByronWilliamsCPA/cookiecutter-python-template/issues)
2. **Submit a PR** if you have fixes for the template
3. **Share this file** with the template maintainers

When submitting, reference this project as the source of the feedback.
