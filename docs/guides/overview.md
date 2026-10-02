---
title: "Overview"
schema_type: common
status: published
owner: core-maintainer
purpose: "Overview of Foundry Unify features and capabilities."
tags:
  - guide
  - overview
---

OCR orchestration and layout analysis service for the Foundry RAG pipeline

## Key Features

> Status: OCR orchestration and DoclingDOM output are specified, not built. See the
> [Level 1 architecture](../architecture/diagrams/level-1/index.md). The items below describe the project tooling.

### Modern Python Development

- **Python 3.10 to 3.14** (tested on 3.12) with full type annotations
- **UV** for fast dependency management
- **Ruff** for linting and formatting
- **BasedPyright** for strict type checking

### Quality Assurance

- **pytest** with comprehensive coverage
- **Pre-commit hooks** for automated checks
- **GitHub Actions** CI/CD pipeline

## Getting Started

1. **Installation**: See the [Configuration Guide](configuration.md)
2. **Usage**: Check the [Usage Guide](usage.md)
3. **API**: Browse the [API Reference](../api-reference.md)

## Architecture

For details on the project architecture, see [Architecture](../development/architecture.md).
