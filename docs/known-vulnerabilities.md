---
title: "Known Vulnerabilities"
schema_type: common
status: published
owner: core-maintainer
purpose: "Track accepted dependency vulnerabilities that cannot be immediately resolved."
tags:
  - security
  - dependencies
---

> **Purpose**: Document dependency vulnerabilities that `pip-audit` reports but
> cannot be immediately fixed. Every entry under Accepted Vulnerabilities must
> correspond to an ID listed in `[tool.pip-audit].ignore-vuln` in
> `pyproject.toml`; resolved entries are kept under Resolved for history.
> Review quarterly; no entry ages past 60 days without reassessment. The
> OpenSSF release gate blocks releases for any vulnerability older than 60 days
> regardless of status.

## Accepted Vulnerabilities

### PYSEC-2026-3740 / GHSA-8mgp-746c-j5xp - `nltk` path traversal, no fix released

- **Package**: `nltk` 3.10.3
- **Aliases**: PYSEC-2026-3740, CVE-2026-81726, GHSA-8mgp-746c-j5xp
- **Severity**: High (CVSS 8.3)
- **Status**: Accepted. No fixed release exists; dev-only, never at runtime.
- **First documented**: 2026-09-03
- **Last re-verified**: 2026-10-02 (still no fixed release; 3.10.3 remains the
  newest on PyPI and the OSV range is unchanged)
- **Reassess by**: 2026-11-02

**Description**: NLTK model-artifact APIs bypass path sanitization and can touch
files outside the allowed roots.

**Why accepted**: There is nothing to upgrade to. The GHSA record's affected
range is `{"introduced": "0"}` to `{"last_affected": "3.10.3"}`, with no
`fixed` event, and 3.10.3 is simultaneously the version this lockfile pins and
the newest release on PyPI. Upstream has not shipped a remediated version.

**Conflicting OSV records**: OSV holds two records for this one advisory, and
they disagree. Re-verified 2026-10-02:

| Record | Affected range | Reading |
| --- | --- | --- |
| `GHSA-8mgp-746c-j5xp` | introduced `0`, `last_affected` `3.10.3` | 3.10.3 affected, no fix |
| `PYSEC-2026-3740` | introduced `0`, `fixed` `3.10.3` | 3.10.3 already fixed |

PyPI sides with the GHSA record: it reports 3.10.3 as still affected, with
`fixed_in` empty. This waiver therefore follows GHSA and PyPI. If PYSEC is
ever corrected to match, or a release above 3.10.3 appears, the waiver is
obsolete.

The exposure is limited to development environments. `nltk` is not a direct
dependency and is not imported anywhere in `src/`; it arrives only as a
transitive dependency of `safety`, which is declared in the `dev` and
`supply-chain` extras:

```text
nltk v3.10.3
└── safety v3.8.1
    ├── foundry-unify v0.1.0 (extra: dev)
    └── foundry-unify v0.1.0 (extra: supply-chain)
```

The runtime distribution never installs it, and no project code calls the
affected model-artifact APIs.

**Suppressions**: three, all keyed to this same advisory and both paired with
this entry:

- `[tool.pip-audit].ignore-vuln` in `pyproject.toml`, keyed on the PYSEC alias.
  pip-audit 2.10.1 does not read this table itself, but the org reusable
  workflow (`ByronWilliamsCPA/.github` `python-ci.yml`, "Dependency
  vulnerability scan" step) reads it and passes each id as `--ignore-vuln`
  to `uv run --frozen pip-audit --skip-editable`, against an environment synced
  with `--all-extras`. So the table is a live gate input for CI. Running
  pip-audit by hand requires passing `--ignore-vuln PYSEC-2026-3740`
  explicitly.
- `[[IgnoredVulns]]` in `osv-scanner.toml`, keyed on the GHSA alias, because
  osv-scanner matches on the GHSA id it reports.
- `allow-ghsas` in `.github/workflows/dependency-review.yml`, keyed on the GHSA
  alias. `fail-on-severity` stays at `high`; only this one id is waived, so
  every other high or critical advisory still blocks the PR. The action
  reports vulnerabilities only on dependencies a PR adds or changes (a version
  bump counts), so without it any PR that changes nltk's locked version, a
  lock refresh included, fails on an advisory with no fix available.

**Remediation plan**: Remove all three suppressions as soon as `nltk` publishes a
release above 3.10.3, or as soon as `safety` stops depending on `nltk`.
Re-check both OSV records at each quarterly review:

```bash
for id in GHSA-8mgp-746c-j5xp PYSEC-2026-3740; do
  echo "== $id"
  curl -s "https://api.osv.dev/v1/vulns/$id" | jq '.affected[].ranges'
done
```

## Resolved

Entries below are kept for history. They no longer correspond to any
`ignore-vuln` id.

### PYSEC-2022-42969 - `py` ReDoS in `py.path.svnwc` (resolved 2026-09-03)

- **Package**: `py` 1.11.0
- **Status**: Resolved. No longer an accepted vulnerability.
- **Resolution**: OSV withdrew the advisory on 2026-06-09 as disputed. The
  paired `[tool.pip-audit].ignore-vuln` entry and the `osv-scanner.toml`
  ignores (CVE-2022-42969, PYSEC-2022-42969, GHSA-w596-4wvx-j9j6) were removed
  in the same change, because osv-scanner exits non-zero on ignore entries that
  no longer match anything.
