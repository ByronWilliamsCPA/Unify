# 02 - Code Quality and Legacy Patterns

State: the small codebase passes the full Ruff ruleset clean, has zero debt markers, and uses modern idioms; the defects are placeholder logic that ships as if functional.

## Ruff and idioms: clean

`ruff 0.15.8 check .` returns "All checks passed!" (exit 0). Targeted runs of `--select UP,FA` (pyupgrade, future-annotations), `--select C901` (mccabe complexity), and `--select S` (bandit) each report zero violations across `src/`, `tests/`, `scripts/`, `tools/`. No `typing.List`/`Dict`/`Optional` legacy generics (target is 3.12; code uses `list`, `dict`, `X | None`). No `%`/`.format` logging. No `os.path` where pathlib is the house standard. One line: this area is clean.

## Debt markers and escape hatches: clean

Zero `TODO`/`FIXME`/`HACK`/`XXX` in `src/`, `tests/`, `scripts/`, `tools/`. Four `# type: ignore` and one `# pyright: ignore` exist, each with a specific error code and a structural reason (structlog return type at `utils/logging.py:156`; `Literal` discriminator assignments at `tools/frontmatter_contract/models.py:150,170,185`; AST visitor dispatch at `scripts/check_type_hints.py:70`). 13 `Any` uses in `src/`, mostly in the exception hierarchy's `to_dict` and logging processors, which is defensible. One line: acceptable as-is.

## CQ-01 Non-asserting placeholder test

Severity: Low. Effort: S.

`tests/test_example.py:388` ends a test with `assert True` after calling `setup_logging(...)`. The comment states it exists "to cover the JSON renderer branch". It exercises a code path but asserts nothing, so a regression in that path would not fail the test while still counting toward coverage.

Evidence: `tests/test_example.py:388` `assert True`.

Recommendation: Assert on observable output (captured log record or handler configuration) or delete the test.

## CQ-02 Readiness probe always reports healthy

Severity: Medium. Effort: S.

`readiness()` builds `checks: dict = {}`, leaves every check commented out, then computes `all_healthy = all(check.status for check in checks.values())`. `all([])` is `True`, so `/health/ready` always returns 200 regardless of dependency state. Shipped as a Kubernetes readiness endpoint, this defeats the probe's purpose: a pod with a dead cache or upstream still receives traffic.

Evidence: `src/foundry_unify/api/health.py:157-186`; `check_cache`/`check_external_service` bodies are placeholders (`api/health.py:84-103,113-134`).

Recommendation: Either wire real checks before exposing the route, or have readiness return 503 (or a documented "no checks configured" state) until checks are registered.

## CQ-03 Empty `financial.py` stub

Severity: Low. Effort: S.

`src/foundry_unify/utils/financial.py` is one line: `"""Financial utilities module."""`. It contains no code. It is template residue carried into an OCR service and is documented in CLAUDE.md as "Financial utilities (Decimal precision)".

Evidence: `src/foundry_unify/utils/financial.py:1` (1 line total).

Recommendation: Delete the file (and its CLAUDE.md entry), or populate it if Decimal handling is actually planned.

## Test suite size

104 test functions across 3 files (test_exceptions 58, test_correlation 25, test_example 21). Coverage percentage was not measured: `pytest --cov` needs the dev group synced and was not run to avoid modifying tracked files. The 80% gate is configured in CI (`ci.yml` `coverage-threshold: 80`).

## Machine-readable findings

```json
[
  {"id": "CQ-01", "title": "Non-asserting placeholder test (assert True)", "domain": "code-quality", "severity": "Low", "effort": "S", "files": ["tests/test_example.py"], "evidence": "tests/test_example.py:388 assert True", "recommendation": "Assert on observable output or delete the test.", "cve": ""},
  {"id": "CQ-02", "title": "Readiness probe always returns healthy (empty checks dict)", "domain": "code-quality", "severity": "Medium", "effort": "S", "files": ["src/foundry_unify/api/health.py"], "evidence": "api/health.py:157-186 all([]) is True; checks never populated", "recommendation": "Wire real checks or return 503/documented state until checks registered.", "cve": ""},
  {"id": "CQ-03", "title": "Empty financial.py stub (template residue)", "domain": "legacy-code", "severity": "Low", "effort": "S", "files": ["src/foundry_unify/utils/financial.py"], "evidence": "financial.py:1 one-line docstring, no code", "recommendation": "Delete the file and its CLAUDE.md entry, or populate it.", "cve": ""}
]
```
