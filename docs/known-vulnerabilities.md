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

### `filelock` - 13 advisories fixed only in 4.x, capped by `safety`

- **Package**: `filelock` 3.32.7
- **Advisories**: CVE-2026-112907, CVE-2026-112908, CVE-2026-112909, CVE-2026-112910, CVE-2026-112911,
  CVE-2026-112912, CVE-2026-112913, CVE-2026-112915, CVE-2026-112935, CVE-2026-112936,
  CVE-2026-112938, CVE-2026-112939, CVE-2026-112940
  (GHSA aliases in `osv-scanner.toml`)
- **Status**: Accepted. Fixed versions (4.0.9, 4.2.1) are unreachable; scoped to the dev, supply-chain and ml extras.
- **First documented**: 2026-10-31
- **Reassess by**: 2026-11-30

**Why accepted**: `safety` (3.7.0 and later, including 3.8.1) requires
`filelock>=3.16.1,<4.0`, so `uv lock` cannot resolve a 4.x release while
`safety` is in the `dev` extra. `filelock` is not imported in `src/` and is
absent from the default runtime install. It is present in three optional
extras: `dev` and `supply-chain` (via `safety`, `nox` and `pre-commit`) and
`ml` (via `torch`, so an `ml` install has `filelock` without `safety`).

**Exposure caveat**: this waiver does not rest on "dev-only". Anyone deploying
with the `ml` extra carries `filelock` 3.32.7 and should treat these advisories
as live for that environment. Reassess whether the `ml` extra needs a tighter
control when the waiver is reviewed.

**Suppressions**: `[tool.pip-audit].ignore-vuln` in `pyproject.toml`
(CVE ids), `[[IgnoredVulns]]` in `osv-scanner.toml` (GHSA ids) and
`allow-ghsas` in `.github/workflows/dependency-review.yml`.

**Remediation plan**: Remove all suppressions once a `safety` release lifts
the cap (`uv lock --upgrade-package safety`) or `safety` is replaced.

## Resolved

Entries below are kept for history. They no longer correspond to any
`ignore-vuln` id.

### PYSEC-2026-3740 / GHSA-8mgp-746c-j5xp - `nltk` path traversal (resolved 2026-10-31)

- **Package**: `nltk` 3.10.3, upgraded to 3.10.4
- **Resolution**: nltk 3.10.4 is clean in OSV (it also fixes GHSA-j456-xh4h-cpf2).
  The pip-audit, osv-scanner and dependency-review waivers were removed in the
  same change, because osv-scanner exits non-zero on ignores that match nothing.

### PYSEC-2022-42969 - `py` ReDoS in `py.path.svnwc` (resolved 2026-09-03)

- **Package**: `py` 1.11.0
- **Status**: Resolved. No longer an accepted vulnerability.
- **Resolution**: OSV withdrew the advisory on 2026-06-09 as disputed. The
  paired `[tool.pip-audit].ignore-vuln` entry and the `osv-scanner.toml`
  ignores (CVE-2022-42969, PYSEC-2022-42969, GHSA-w596-4wvx-j9j6) were removed
  in the same change, because osv-scanner exits non-zero on ignore entries that
  no longer match anything.
