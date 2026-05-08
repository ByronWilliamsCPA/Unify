# AI Agent Configuration for Foundry Unify

This file documents the AI agent configuration for the Foundry Unify project.
It is read by Codex, Gemini CLI, and similar AI coding agents at session start.

## Project Context

**Foundry Unify** is an OCR orchestration and layout analysis service for the Foundry RAG pipeline.

- **Language**: Python 3.12
- **Package manager**: UV
- **Repository**: https://github.com/ByronWilliamsCPA/Unify
- **Main package**: `src/foundry_unify/`

## Development Commands

```bash
uv sync --all-extras          # Install all dependencies
uv run pytest -v              # Run tests
uv run ruff check . --fix     # Lint and autofix
uv run ruff format .          # Format code
uv run basedpyright src/      # Type check
uv run bandit -r src          # Security scan
uv run pip-audit              # Dependency vulnerability scan
pre-commit run --all-files    # Run all pre-commit hooks
```

## Key Rules

- Never commit directly to `main`. Always create a feature branch first.
- Run `pre-commit run --all-files` before every commit.
- Minimum 80% test coverage enforced in CI.
- No em-dashes (`--`) in any output -- use commas, semicolons, or colons.
- All type annotations required (BasedPyright strict mode).

## Architecture

See [CLAUDE.md](CLAUDE.md) for full project guidelines, exception hierarchy,
correlation ID patterns, and configuration management standards.
