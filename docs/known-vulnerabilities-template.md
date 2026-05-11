---
title: "Known Vulnerability Entry Template"
schema_type: common
status: published
owner: core-maintainer
purpose: "Template for documenting vulnerabilities that cannot be immediately resolved."
tags:
  - security
  - compliance
---

Copy the block below for each new vulnerability entry in `docs/known-vulnerabilities.md`.

---

### {CVE-ID} -- {package-name} ({SEVERITY})

| Field | Value |
|-------|-------|
| **CVE** | {CVE-ID} |
| **Severity** | {CRITICAL / HIGH / MEDIUM / LOW} |
| **Package** | {package-name} {installed-version} |
| **Image / Source** | {python:3.12-slim / pypi / etc.} |
| **Scanner** | {Trivy / pip-audit / Bandit / etc.} |
| **Documented** | {YYYY-MM-DD} |
| **Review by** | {YYYY-MM-DD -- must be within 60 days of documented date} |
| **Fixed version** | {version string, or "None available"} |

**Description**: {One sentence from the CVE advisory.}

**Why not fixed**: {Explain why the vulnerability cannot be resolved immediately.
Common reasons: no upstream fix, transitive dependency, base image constraint.}

**Mitigation**: {What compensating controls reduce risk? If none, state "None."}

**Suppressed in**: {`.trivyignore` / `pip-audit` baseline / inline `# noqa` with tracking ref}
