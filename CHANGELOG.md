# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `src/foundry_unify/main.py` FastAPI application entry point referenced by Dockerfile CMD
- `src/foundry_unify/cli.py` Click-based CLI with `hello` and `config` subcommands
- Smoke tests for `main.py` covering app construction, health probe, and ENVIRONMENT-gated docs URL
- `LICENSES/ODbL-1.0.txt` (referenced by REUSE.toml for data files)
- Production-ready security middleware additions: asyncio lock on rate limiter,
  X-Forwarded-For/X-Real-IP support, SSRF inspection of risky headers
- `--debug` global flag and `--version` to the new CLI

### Changed
- Renamed `src/foundry_unify/utils/logging.py` to `utils/structured_logging.py`
  (resolves Ruff A005 stdlib-shadow warning)
- `add_security_middleware` now defaults `allow_credentials=False` and uses an
  explicit `allow_headers` allowlist instead of `["*"]`
- `main.py` disables the FastAPI docs UI (`/docs`, `/redoc`) when
  `ENVIRONMENT=production`
- SonarCloud organization/project key updated to match `.sonarlint/connectedMode.json`
  (`byronwilliamscpa` / `ByronWilliamsCPA_Unify`)
- Pinned `dangoslen/changelog-enforcer` to v3.7.0 (the v3.8.0 SHA was invalid)
- `python-compatibility.yml` test-command marker expression re-quoted so pytest
  receives `-m 'not slow and not integration'` as a single argument

### Fixed
- 57 compliance findings from the 2026-05-05 full repository compliance audit
  (OpenSSF gaps, pre-commit hook hygiene, Python toolchain config, MkDocs structure,
  documentation completeness)
- `.cruft.json` template URL restored to GitHub HTTPS (was a local filesystem path)
- REUSE compliance: removed unused `Apache-2.0.txt`, `BSD-3-Clause.txt`,
  `GPL-3.0-or-later.txt` license files
- `correlation_context_processor` docstring restored (`_logger` and `_method_name`
  parameter documentation)
- Em-dashes replaced with commas in `.gitignore` and `docs/planning/tech-spec.md`
- `noqa: N802` suppressions in `scripts/check_fips_compatibility.py` and
  `scripts/check_type_hints.py` now include inline justification

### Removed
- Unused license files in `LICENSES/` (Apache-2.0, BSD-3-Clause, GPL-3.0-or-later)
- `.github/dependabot.yml` (Renovate is the canonical dependency manager;
  `uv.lock` is unsupported by Dependabot)

### Security
- Restored `safety>=3.7.0` to dev dependencies (referenced by `security-analysis.yml`)
- Closed TOCTOU race in `RateLimitMiddleware` (concurrent requests could double the
  burst); the check-then-update region now runs under `asyncio.Lock`
- Rate limiter now resolves the client IP from `X-Forwarded-For` / `X-Real-IP` so
  every client behind a reverse proxy does not share one bucket
- SSRF middleware now inspects `Referer`, `Location`, and `X-Forwarded-Host`
  headers in addition to query parameters

## [0.1.0] - 2026-05-05

### Added
- Initial project structure with UV package management
- Pydantic v2 JSON schema validation
- Structured logging with structlog and rich console output
- Pre-commit hooks (Ruff format, Ruff lint, BasedPyright, Bandit)
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
- UV dependency management with lock file
- pytest test framework with coverage reporting
- GitHub issue tracking and templates
- Automated dependency security scanning (pip-audit, Bandit)
- Code quality enforcement (Ruff, BasedPyright)
- CI/CD pipeline with multiple quality gates

### Security
- Bandit security linting
- pip-audit dependency vulnerability scanning
- Pre-commit hooks for security validation

[Unreleased]: https://github.com/ByronWilliamsCPA/Unify/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ByronWilliamsCPA/Unify/releases/tag/v0.1.0
