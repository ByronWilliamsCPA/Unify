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

### PYSEC-2022-42969 - `py` ReDoS in `py.path.svnwc`

- **Package**: `py` 1.11.0
- **Severity**: Medium (regular-expression denial of service)
- **Status**: Accepted (no fix available)
- **First documented**: 2026-05-28
- **Reassess by**: 2026-07-27

**Description**: The `py` library is vulnerable to a ReDoS in the Subversion
path handling (`py.path.svnwc`) when parsing crafted SVN command output.

**Why accepted**: `py` is an unmaintained transitive dependency pulled in by
`interrogate` (docstring-coverage tooling). No fixed release of `py` exists.
The vulnerable code path (`py.path.svnwc`) handles Subversion working copies
and is never exercised by this project or by `interrogate`'s docstring checks.
The dependency is dev-only and never ships in the runtime distribution.

**Remediation plan**: Drop the dependency when `interrogate` removes its `py`
requirement, or replace `interrogate` with a tool that does not depend on `py`.
Re-checked each quarter against the `interrogate` dependency tree.
