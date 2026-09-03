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

### PYSEC-2026-3740 / GHSA-8mgp-746c-j5xp - `nltk` path traversal, no fix released

- **Package**: `nltk` 3.10.3
- **Aliases**: PYSEC-2026-3740, CVE-2026-81726, GHSA-8mgp-746c-j5xp
- **Severity**: High (CVSS 8.3)
- **Status**: Accepted. No fixed release exists; dev-only, never at runtime.
- **First documented**: 2026-09-03
- **Reassess by**: 2026-11-02

**Description**: NLTK model-artifact APIs bypass path sanitization and can touch
files outside the allowed roots.

**Why accepted**: There is nothing to upgrade to. The OSV record's affected
range is `{"introduced": "0"}` to `{"last_affected": "3.10.3"}`, with no
`fixed` event, and 3.10.3 is simultaneously the version this lockfile pins and
the newest release on PyPI. Upstream has not shipped a remediated version.

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

**Suppressions**: two, both keyed to this same advisory and both paired with
this entry:

- `[tool.pip-audit].ignore-vuln` in `pyproject.toml`, keyed on the PYSEC alias.
  Note that pip-audit 2.10.1 does not read this table; it honours only the
  `--ignore-vuln` CLI flag. pip-audit is currently a dev dependency and is not
  invoked by any workflow, so the table records the accepted risk rather than
  suppressing a live gate. Anything that later wires pip-audit into CI must
  pass `--ignore-vuln PYSEC-2026-3740` explicitly.
- `[[IgnoredVulns]]` in `osv-scanner.toml`, keyed on the GHSA alias, because
  osv-scanner matches on the GHSA id it reports.

**Remediation plan**: Remove both suppressions as soon as `nltk` publishes a
release above 3.10.3, or as soon as `safety` stops depending on `nltk`.
Re-check against the OSV API at each quarterly review:

```bash
curl -s https://api.osv.dev/v1/vulns/GHSA-8mgp-746c-j5xp | jq '.affected[].ranges'
```

### PYSEC-2022-42969 - `py` ReDoS in `py.path.svnwc` (resolved 2026-09-03)

- **Package**: `py` 1.11.0
- **Status**: Resolved. No longer an accepted vulnerability.
- **Resolution**: OSV withdrew the advisory on 2026-06-09 as disputed. The
  paired `[tool.pip-audit].ignore-vuln` entry and the `osv-scanner.toml`
  ignores (CVE-2022-42969, PYSEC-2022-42969, GHSA-w596-4wvx-j9j6) were removed
  in the same change, because osv-scanner exits non-zero on ignore entries that
  no longer match anything.
