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
> cannot be immediately fixed. Every entry here must correspond to an ID listed
> in `[tool.pip-audit].ignore-vuln` in `pyproject.toml`. Review quarterly; no
> entry ages past 60 days without reassessment. The OpenSSF release gate blocks
> releases for any vulnerability older than 60 days regardless of status.

## Accepted Vulnerabilities

### PYSEC-2026-3740 - `nltk` advisory range stale upstream

- **Package**: `nltk` 3.10.3
- **Severity**: Medium
- **Status**: Accepted (already on the fixed release; advisory range is stale)
- **First documented**: 2026-09-03
- **Reassess by**: 2026-11-02

**Description**: `pip-audit` reports PYSEC-2026-3740 against `nltk` 3.10.3 and
lists no fix version.

**Why accepted**: The OSV record for PYSEC-2026-3740 sets the fixed version to
3.10.3, and 3.10.3 is both the version this project locks and the latest
release on PyPI. The affected range published to PyPI's advisory feed has not
been narrowed to match, so `pip-audit` still flags an already-remediated
release. `nltk` is a dev-only transitive dependency of `safety`; it is never
imported by this project and never ships in the runtime distribution.

**Remediation plan**: Drop this entry as soon as the upstream advisory range is
corrected, or as soon as `nltk` publishes a release above 3.10.3. Re-checked
against OSV each quarter.

### PYSEC-2022-42969 - `py` ReDoS in `py.path.svnwc` (resolved 2026-09-03)

- **Package**: `py` 1.11.0
- **Status**: Resolved. No longer an accepted vulnerability.
- **Resolution**: OSV withdrew the advisory on 2026-06-09 as disputed. The
  paired `[tool.pip-audit].ignore-vuln` entry and the `osv-scanner.toml`
  ignores (CVE-2022-42969, PYSEC-2022-42969, GHSA-w596-4wvx-j9j6) were removed
  in the same change, because osv-scanner exits non-zero on ignore entries that
  no longer match anything.
