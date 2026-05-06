---
title: "Usage"
schema_type: common
status: published
owner: core-maintainer
purpose: "Usage guide for Foundry Unify."
tags:
  - guide
  - usage
---

This guide covers common usage patterns for Foundry Unify.

## Installation

### From PyPI

```bash
pip install foundry-unify
```

### From Source

```bash
git clone https://github.com/ByronWilliamsCPA/Unify
cd foundry_unify
uv sync --all-extras
```

## Library Usage

### Basic Import

```python
from foundry_unify import __version__

print(f"Version: {__version__}")
```

### Logging

```python
from foundry_unify.utils.logging import get_logger, setup_logging

# Setup logging
setup_logging(level="DEBUG", json_logs=False)

# Get a logger
logger = get_logger(__name__)
logger.info("Hello from Foundry Unify")
```
