---
title: "Known Vulnerabilities"
schema_type: common
status: published
owner: core-maintainer
purpose: "Documented vulnerabilities that cannot be immediately resolved, tracked per project policy."
tags:
  - security
  - compliance
---

Vulnerabilities that cannot be immediately resolved are documented here per project policy.
Each entry must be reviewed within 60 days. No entry may age past 60 days without reassessment.
The OpenSSF release gate blocks releases for any vulnerability older than 60 days.

> **Policy reference**: See `CLAUDE.md` section "Unfixed CVEs" for full policy details.

---

## Active Entries

### CVE-2026-33845 -- libgnutls30t64 (CRITICAL)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-33845 |
| **Severity** | CRITICAL |
| **Package** | libgnutls30t64 3.8.9-3+deb13u2 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: GnuTLS Denial of Service via DTLS zero-length record handling.

**Why not fixed**: No patched version exists in the Debian Trixie repository as of documentation date. The `python:3.12-slim` base image cannot be changed without moving away from official Python images.

**Mitigation**: This service does not expose DTLS endpoints. The vulnerability requires a network attacker to send crafted DTLS packets. Exposure is limited by network-level controls.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-7598 -- libssh2-1t64 (CRITICAL)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-7598 |
| **Severity** | CRITICAL |
| **Package** | libssh2-1t64 1.11.1-1 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: Integer overflow in libssh2 via large username or password values.

**Why not fixed**: No patched version exists in the Debian Trixie repository as of documentation date.

**Mitigation**: This service does not use SSH client functionality. libssh2 is a transitive dependency of curl; the vulnerable code path (authentication with oversized credentials) is not exercised.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-4878 -- libcap2 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-4878 |
| **Severity** | HIGH |
| **Package** | libcap2 1:2.75-10+b8 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: Privilege escalation via TOCTOU (time-of-check time-of-use) race condition in libcap.

**Why not fixed**: No patched version exists in Debian Trixie as of documentation date.

**Mitigation**: Container runs as non-root user (uid 1000, `appuser`). Privilege escalation path is significantly constrained by the existing security posture.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-33846 -- libgnutls30t64 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-33846 |
| **Severity** | HIGH |
| **Package** | libgnutls30t64 3.8.9-3+deb13u2 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: GnuTLS Denial of Service via heap buffer overflow.

**Why not fixed**: No patched version available. Same package as CVE-2026-33845.

**Mitigation**: Same as CVE-2026-33845 -- no DTLS exposure.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-3833 -- libgnutls30t64 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-3833 |
| **Severity** | HIGH |
| **Package** | libgnutls30t64 3.8.9-3+deb13u2 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: GnuTLS policy bypass due to case-sensitive certificate name comparison.

**Why not fixed**: No patched version available. Same package as CVE-2026-33845.

**Mitigation**: TLS certificate validation in application code uses the standard Python `ssl` module, which wraps OpenSSL rather than GnuTLS directly.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-42010 -- libgnutls30t64 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-42010 |
| **Severity** | HIGH |
| **Package** | libgnutls30t64 3.8.9-3+deb13u2 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: GnuTLS authentication bypass via NUL character in certificate subject.

**Why not fixed**: No patched version available. Same package as CVE-2026-33845.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-42011 -- libgnutls30t64 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-42011 |
| **Severity** | HIGH |
| **Package** | libgnutls30t64 3.8.9-3+deb13u2 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: GnuTLS security bypass due to incorrect name handling in certificate validation.

**Why not fixed**: No patched version available. Same package as CVE-2026-33845.

**Suppressed in**: `.trivyignore`

---

### CVE-2025-69720 -- ncurses (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2025-69720 |
| **Severity** | HIGH |
| **Packages** | libncursesw6, libtinfo6, ncurses-base (6.5+20250216-2) |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: ncurses buffer overflow vulnerability that may lead to arbitrary code execution.

**Why not fixed**: No patched version exists in Debian Trixie as of documentation date. ncurses is a transitive dependency of the Python interpreter itself.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-27135 -- libnghttp2-14 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-27135 |
| **Severity** | HIGH |
| **Package** | libnghttp2-14 1.64.0-1.1 |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: nghttp2 Denial of Service via malformed HTTP/2 frames.

**Why not fixed**: No patched version available in Debian Trixie.

**Mitigation**: Application acts as HTTP/2 client only (via httpx/curl); it does not serve HTTP/2 directly. DoS via malformed frames is only exploitable by a malicious server response.

**Suppressed in**: `.trivyignore`

---

### CVE-2026-29111 -- libsystemd0 / libudev1 (HIGH)

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-29111 |
| **Severity** | HIGH |
| **Packages** | libsystemd0, libudev1 (257.9-1~deb13u1) |
| **Image** | python:3.12-slim (Debian Trixie) |
| **Scanner** | Trivy |
| **Documented** | 2026-05-10 |
| **Review by** | 2026-07-09 |
| **Fixed version** | None available |

**Description**: systemd arbitrary code execution or Denial of Service.

**Why not fixed**: No patched version exists in Debian Trixie as of documentation date. systemd libraries are present in the base image as low-level OS dependencies.

**Mitigation**: Container runs without systemd as PID 1 (uses standard container init). The vulnerable systemd code paths are not exercised at runtime.

**Suppressed in**: `.trivyignore`

---

## Resolved Entries

*No resolved entries yet.*

---

## Review Schedule

| CVE | Review By | Responsible |
|-----|-----------|-------------|
| CVE-2026-33845 | 2026-07-09 | Byron Williams |
| CVE-2026-7598 | 2026-07-09 | Byron Williams |
| CVE-2026-4878 | 2026-07-09 | Byron Williams |
| CVE-2026-33846 | 2026-07-09 | Byron Williams |
| CVE-2026-3833 | 2026-07-09 | Byron Williams |
| CVE-2026-42010 | 2026-07-09 | Byron Williams |
| CVE-2026-42011 | 2026-07-09 | Byron Williams |
| CVE-2025-69720 | 2026-07-09 | Byron Williams |
| CVE-2026-27135 | 2026-07-09 | Byron Williams |
| CVE-2026-29111 | 2026-07-09 | Byron Williams |
