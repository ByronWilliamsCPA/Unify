# 05 - CI/CD and Tooling

State: actions are current and mostly SHA-pinned, but SonarCloud is wired two contradictory ways (wrong org in one path, duplicated runs, non-blocking gate), and the full pipeline runs twice per PR.

## CI-01 SonarCloud organization mismatch

Severity: High. Effort: S.

Two SonarCloud configurations disagree on the organization. `ci.yml` passes `sonarcloud-organization: 'ByronWilliamsCPA'` to the org reusable workflow, while `sonar-project.properties` and the standalone `sonarcloud.yml` both set `sonar.organization=williaby`. The project key is identical in all three (`ByronWilliamsCPA_foundry_unify`). One of the two org values is wrong, so at least one SonarCloud path fails to authenticate or pushes analysis to the wrong organization.

Evidence: `ci.yml:39` `sonarcloud-organization: 'ByronWilliamsCPA'`; `sonar-project.properties:7` `sonar.organization=williaby`; `sonarcloud.yml:131` `-Dsonar.organization=williaby`.

Recommendation: Decide the correct organization and set it identically in all three places.

## CI-02 Duplicate SonarCloud analysis

Severity: Medium. Effort: S.

SonarCloud runs twice. `ci.yml` enables it inside the org `python-ci.yml` (`enable-sonarcloud: true`), and a standalone `sonarcloud.yml` runs its own scan. Both trigger on push to main and on PRs, so each push pays for two analyses that report to the same project key.

Evidence: `ci.yml:38` `enable-sonarcloud: true`; `sonarcloud.yml` entire workflow scans the same project.

Recommendation: Keep one path. If the org workflow handles Sonar, delete `sonarcloud.yml`.

## CI-03 Full CI runs twice per pull request

Severity: Medium. Effort: M.

`python-ci.yml` is invoked twice on every PR to main: by `ci.yml`'s `ci` job and by `pr-validation.yml`'s `core-validation` job. Both run the test, lint, and type-check suite. PRs pay roughly double CI minutes and wall-clock time.

Evidence: `ci.yml:35` `uses: .../python-ci.yml@main`; `pr-validation.yml:42` `uses: .../python-ci.yml@e8fc83c...`; both trigger on `pull_request` to main.

Recommendation: Run `python-ci.yml` from one workflow on PRs; let the other depend on its result or cover only its extra jobs (dead-code, link-check).

## CI-04 Same reusable workflow pinned two ways

Severity: Low. Effort: S.

The two `python-ci.yml` calls use different refs: `ci.yml` pins `@main` (moving) and `pr-validation.yml` pins `@e8fc83c...` (SHA). The same dependency resolves to different versions within one repo on the same PR.

Evidence: `ci.yml:35` `@main`; `pr-validation.yml:42` `@e8fc83c98c2971ad1ece71573d28171463e30c16`.

Recommendation: Pin both to the same SHA (covered repo-wide by SEC-01).

## CI-05 Non-blocking SonarCloud gate

Severity: Medium. Effort: S.

In `sonarcloud.yml` the test step carries `continue-on-error: true` ("Don't fail on test failures") and the quality-gate step carries `continue-on-error: true` ("Don't fail workflow, just report status"). The standalone Sonar workflow can never block a merge, including on a failed quality gate or failed tests.

Evidence: `sonarcloud.yml:120` (tests `continue-on-error: true`), `sonarcloud.yml:135` (quality gate `continue-on-error: true`).

Recommendation: If this workflow is kept (see CI-02), make the quality gate blocking; otherwise remove it.

## CI-06 Obsolete docker-compose version attribute

Severity: Low. Effort: S.

`docker-compose.yml` declares `version: '3.9'`. The top-level `version` key is obsolete in Compose v2 and emits a warning on every `docker compose` invocation.

Evidence: `docker-compose.yml:4` `version: '3.9'`.

Recommendation: Remove the `version` line; the same applies to `docker-compose.prod.yml` if present there.

## CI-07 Stale pre-commit pins and type-check gate not in pre-commit

Severity: Low. Effort: S.

`.pre-commit-config.yaml` pins `ruff-pre-commit` at `v0.9.0` (Jan 2025) while the installed and floor-current Ruff is 0.15.x; bandit hook is at `1.7.10`. BasedPyright, the documented strict type-check gate, has no pre-commit hook, so type errors are caught only in CI, later than local commit time.

Evidence: `.pre-commit-config.yaml:130` `rev: v0.9.0` (ruff); `:78` `rev: 1.7.10` (bandit); no basedpyright `id:` in the file.

Recommendation: Bump pre-commit revs (pre-commit autoupdate) and add a basedpyright local hook to match the CI gate.

## CI-08 pip cache on a uv-managed project

Severity: Low. Effort: S.

`sonarcloud.yml` configures `actions/setup-python` with `cache: 'pip'`, but the project resolves dependencies with uv and a `uv.lock`; there is no pip cache to populate, so the setting is a no-op.

Evidence: `sonarcloud.yml` setup-python step `cache: 'pip'`.

Recommendation: Drop `cache: 'pip'` and rely on `astral-sh/setup-uv` caching (also fixes SEC-03).

## Workflow currency: clean

Actions are on current majors: `actions/checkout@v4.2.2`, `setup-python@v5.3.0`, `upload-artifact@v4.5.0`. No `actions/upload-artifact@v3` (deprecated), no `set-output`/`save-state`, no node16/node12 runners. `harden-runner` is applied in the inline jobs. One line: no deprecated-action exposure.

## Machine-readable findings

```json
[
  {"id": "CI-01", "title": "SonarCloud organization mismatch (williaby vs ByronWilliamsCPA)", "domain": "cicd", "severity": "High", "effort": "S", "files": [".github/workflows/ci.yml", ".github/workflows/sonarcloud.yml", "sonar-project.properties"], "evidence": "ci.yml:39 ByronWilliamsCPA vs sonar-project.properties:7 / sonarcloud.yml:131 williaby", "recommendation": "Set the correct organization identically in all three places.", "cve": ""},
  {"id": "CI-02", "title": "Duplicate SonarCloud analysis", "domain": "cicd", "severity": "Medium", "effort": "S", "files": [".github/workflows/ci.yml", ".github/workflows/sonarcloud.yml"], "evidence": "ci.yml:38 enable-sonarcloud:true and standalone sonarcloud.yml both scan same project", "recommendation": "Keep one Sonar path; delete sonarcloud.yml if the org workflow handles it.", "cve": ""},
  {"id": "CI-03", "title": "Full CI runs twice per PR", "domain": "cicd", "severity": "Medium", "effort": "M", "files": [".github/workflows/ci.yml", ".github/workflows/pr-validation.yml"], "evidence": "python-ci.yml invoked by ci.yml:35 and pr-validation.yml:42 on same PR", "recommendation": "Run python-ci.yml once on PRs; have the other depend on it or cover only extra jobs.", "cve": ""},
  {"id": "CI-04", "title": "Same reusable workflow pinned @main and @SHA", "domain": "cicd", "severity": "Low", "effort": "S", "files": [".github/workflows/ci.yml", ".github/workflows/pr-validation.yml"], "evidence": "ci.yml:35 @main vs pr-validation.yml:42 @e8fc83c", "recommendation": "Pin both to the same SHA.", "cve": ""},
  {"id": "CI-05", "title": "Non-blocking SonarCloud quality gate", "domain": "cicd", "severity": "Medium", "effort": "S", "files": [".github/workflows/sonarcloud.yml"], "evidence": "sonarcloud.yml:120 tests continue-on-error:true; :135 quality gate continue-on-error:true", "recommendation": "Make the gate blocking or remove the workflow.", "cve": ""},
  {"id": "CI-06", "title": "Obsolete docker-compose version attribute", "domain": "cicd", "severity": "Low", "effort": "S", "files": ["docker-compose.yml"], "evidence": "docker-compose.yml:4 version: '3.9'", "recommendation": "Remove the version line.", "cve": ""},
  {"id": "CI-07", "title": "Stale pre-commit pins; basedpyright gate missing from pre-commit", "domain": "cicd", "severity": "Low", "effort": "S", "files": [".pre-commit-config.yaml"], "evidence": ".pre-commit-config.yaml:130 ruff rev v0.9.0 vs installed 0.15.x; no basedpyright hook", "recommendation": "Run pre-commit autoupdate and add a basedpyright local hook.", "cve": ""},
  {"id": "CI-08", "title": "pip cache configured on a uv-managed project", "domain": "cicd", "severity": "Low", "effort": "S", "files": [".github/workflows/sonarcloud.yml"], "evidence": "sonarcloud.yml setup-python cache: 'pip'", "recommendation": "Drop cache:'pip'; use setup-uv caching.", "cve": ""}
]
```
