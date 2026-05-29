# 04 - Security and Secrets

State: no secrets in tracked files, no code-level injection surfaces, and a real security middleware; the exposure is supply-chain pinning in workflows (moving refs and remote script execution).

## SEC-01 Org reusable workflows pinned to moving `@main`

Severity: High. Effort: S.

Twelve calls to `ByronWilliamsCPA/.github/.github/workflows/python-*.yml` use `@main`, a moving ref. CI, security analysis, SBOM, container security, mutation, release, scorecard, SLSA, docs, codecov, and publish-pypi all inherit behavior from whatever currently sits on the org repo's main branch. A push there changes this repo's pipeline, including its security gates, with no commit or review here. One call (`pr-validation.yml:42`) is SHA-pinned, proving the pattern is known and just not applied consistently.

Evidence: `grep -rn "ByronWilliamsCPA/.github" .github/workflows/` shows `@main` on `ci.yml:32`, `security-analysis.yml:35`, `sbom.yml`, `container-security.yml`, `mutation-testing.yml`, `release.yml`, `scorecard.yml`, `slsa-provenance.yml`, `docs.yml`, `codecov.yml`, `publish-pypi.yml`; SHA pin at `pr-validation.yml:42`.

Recommendation: Pin every reusable-workflow call to a commit SHA and let Renovate update them, matching the existing `pr-validation.yml` pin.

## SEC-02 Quality-gate action pinned to `@master`

Severity: Medium. Effort: S.

`sonarcloud.yml` pins `sonarsource/sonarqube-quality-gate-action@master`, a third-party action tracked to a moving branch. Every run executes whatever is on that branch at run time.

Evidence: `.github/workflows/sonarcloud.yml:136` `uses: sonarsource/sonarqube-quality-gate-action@master`.

Recommendation: Pin to a released SHA (the sibling `sonarqube-scan-action` at line 125 is already SHA-pinned).

## SEC-03 uv installed via unpinned remote script in CI

Severity: Medium. Effort: S.

`sonarcloud.yml` installs uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`, executing a remote script fetched at run time with no integrity check. Every other workflow uses the pinned `astral-sh/setup-uv` action.

Evidence: `.github/workflows/sonarcloud.yml:108-110`.

Recommendation: Replace with `astral-sh/setup-uv` (SHA-pinned) for consistency and integrity.

## SEC-04 Some actions tag-pinned rather than SHA-pinned

Severity: Low. Effort: S.

Most third-party actions are SHA-pinned (25 of 30 `uses:` lines). Five are tag-pinned: `astral-sh/setup-uv@v7` (multiple) and `actions/dependency-review-action@v4`. Tags are mutable.

Evidence: `grep -rh "uses:" .github/workflows/*.yml | grep -E "@v[0-9]"` -> setup-uv@v7, dependency-review-action@v4.

Recommendation: SHA-pin these to match the rest of the workflows.

## SEC-05 Weak placeholder password in `.env.example`

Severity: Low. Effort: S.

`.env.example:200` sets `DB_PASSWORD=password`. Other values use obvious `your-...-here` placeholders; this one reads like a usable default and can be copied into a real `.env` unchanged.

Evidence: `.env.example:200` `DB_PASSWORD=password`.

Recommendation: Use `DB_PASSWORD=changeme-your-db-password` to match the placeholder convention.

## Clean areas

No code-level injection surfaces: zero `shell=True`, `os.system`, `eval`, `exec`, `pickle.load`, or `yaml.load` across `src/`, `scripts/`, `tools/`; `ruff --select S` passes. Secret scanning is wired: pre-commit runs `trufflehog` (`.pre-commit-config.yaml:63`) and `detect-private-key` (`:42`); no plaintext secrets found in tracked files (`.env.example` and `.infisical.json` carry placeholders only). The `except Exception` blocks in `src/` are BLE001-ignored with documented resilience justifications (`pyproject.toml:393,400`), consistent with CLAUDE.md's "document why" rule. `middleware/security.py` implements the headers, rate limiting, and SSRF prevention it claims (520 LOC). No detect-secrets baseline exists, but secret scanning is covered by trufflehog, so there is no baseline to drift.

## Machine-readable findings

```json
[
  {"id": "SEC-01", "title": "Org reusable workflows pinned to moving @main", "domain": "security", "severity": "High", "effort": "S", "files": [".github/workflows/ci.yml", ".github/workflows/security-analysis.yml", ".github/workflows/sbom.yml", ".github/workflows/release.yml"], "evidence": "12 calls to ByronWilliamsCPA/.github/...@main (ci.yml:32 etc.); pr-validation.yml:42 is SHA-pinned", "recommendation": "Pin every reusable-workflow call to a commit SHA and update via Renovate.", "cve": ""},
  {"id": "SEC-02", "title": "sonarqube-quality-gate-action pinned to @master", "domain": "security", "severity": "Medium", "effort": "S", "files": [".github/workflows/sonarcloud.yml"], "evidence": "sonarcloud.yml:136 uses sonarsource/sonarqube-quality-gate-action@master", "recommendation": "Pin to a released SHA like the sibling scan action.", "cve": ""},
  {"id": "SEC-03", "title": "uv installed via unpinned curl|sh in CI", "domain": "security", "severity": "Medium", "effort": "S", "files": [".github/workflows/sonarcloud.yml"], "evidence": "sonarcloud.yml:108-110 curl -LsSf https://astral.sh/uv/install.sh | sh", "recommendation": "Use SHA-pinned astral-sh/setup-uv action.", "cve": ""},
  {"id": "SEC-04", "title": "Some actions tag-pinned not SHA-pinned", "domain": "security", "severity": "Low", "effort": "S", "files": [".github/workflows"], "evidence": "5 of 30 uses: lines tag-pinned: setup-uv@v7, dependency-review-action@v4", "recommendation": "SHA-pin these to match the other workflows.", "cve": ""},
  {"id": "SEC-05", "title": "Weak placeholder password in .env.example", "domain": "security", "severity": "Low", "effort": "S", "files": [".env.example"], "evidence": ".env.example:200 DB_PASSWORD=password", "recommendation": "Use a placeholder-style value like changeme-your-db-password.", "cve": ""}
]
```
