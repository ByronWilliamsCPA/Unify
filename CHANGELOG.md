# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup and structure

### Removed
- Deleted `.github/workflows/dependency-review.yml`. GitHub now bills
  Advanced Security (Code Security), so `actions/dependency-review-action`
  no longer functions on this repo.
- Disabled `upload-sarif` in `scorecard.yml` and `container-security.yml`
  (org-level `python-scorecard.yml` / `python-container-security.yml`
  reusable workflow inputs); `github/codeql-action/upload-sarif` no longer
  functions without Advanced Security. Scorecard and Trivy results remain
  available via the `scorecard-results` and `container-security-reports`
  workflow artifacts the reusable workflows already publish unconditionally.
  Hadolint's SARIF has no artifact fallback today; its findings are visible
  only in the job log until a follow-up adds one to the reusable workflow.
- `security-analysis.yml`'s `run-codeql: true` / `run-dependency-review: true`
  inputs are left as-is; a separate coordinated change updates the shared
  `python-security-analysis.yml` reusable workflow before this caller changes.

## [0.1.0] - TBD

### Added
- Initial project structure with Poetry package management
- Pydantic v2 JSON schema validation
- Structured logging with structlog and rich console output
- Pre-commit hooks (Ruff format, Ruff lint, BasedPyright, Bandit, Safety)
- Comprehensive test suite with pytest
- GitHub Actions CI/CD pipeline with quality gates
- CLI tool foundation
- License

### Documentation
- README with project overview and quick start
- CONTRIBUTING guidelines with development workflow
- References to ByronWilliamsCPA org-level Security Policy
- References to ByronWilliamsCPA org-level Code of Conduct

### Infrastructure
- Poetry dependency management with lock file
- pytest test framework with coverage reporting
- GitHub issue tracking and templates
- Automated dependency security scanning (Safety, Bandit)
- Code quality enforcement (Ruff, BasedPyright)
- CI/CD pipeline with multiple quality gates

### Security
- Bandit security linting
- Safety dependency vulnerability scanning
- Pre-commit hooks for security validation

[Unreleased]: https://github.com/williaby/foundry_unify/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/williaby/foundry_unify/releases/tag/v0.1.0
