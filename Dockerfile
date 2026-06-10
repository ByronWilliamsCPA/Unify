# Multi-stage Dockerfile for Foundry Unify
# Optimized for production with security best practices and minimal image size.
#
# Both stages use Chainguard's Wolfi-based Python images, which are rebuilt
# continuously and ship with a near-zero CVE surface (no perl, curl, ncurses,
# or other base-OS packages that carry the CVEs debian-slim and distroless do).
# The -dev variant provides a shell and apk for building; the minimal runtime
# has neither. Both pin the same Python version, so the resolved virtual
# environment's interpreter symlink stays valid when copied across stages.

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
# Chainguard python:latest-dev (Wolfi). Digest-pinned for reproducibility and
# to satisfy DL3007; Renovate updates the digest as the image is rebuilt.
FROM cgr.dev/chainguard/python@sha256:ddd3811dcbef56aa9f3882ae16fdc2920174ac6028c12e76cfb64c1d37b7abe2 AS builder

WORKDIR /app

# Use the image's own Python; never let uv download a standalone interpreter,
# otherwise the venv would reference a path that does not exist in the runtime.
ENV UV_PYTHON=/usr/bin/python \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

# Install UV (static binary) for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (cached layer), then the project itself
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal Wolfi production image
# =============================================================================
# Chainguard python:latest (Wolfi minimal runtime). Digest-pinned; Renovate
# updates the digest as the image is rebuilt.
FROM cgr.dev/chainguard/python@sha256:30ac20a34bae29023ae54b454e85fedb5cfb7de5f206dc73112bf8b0e3e3e190

# Metadata labels (OCI standard)
LABEL org.opencontainers.image.title="Foundry Unify"
LABEL org.opencontainers.image.description="OCR orchestration and layout analysis service for the Foundry RAG pipeline"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="Byron Williams <byronawilliams@gmail.com>"
LABEL org.opencontainers.image.url="https://github.com/ByronWilliamsCPA/Unify"
LABEL org.opencontainers.image.source="https://github.com/ByronWilliamsCPA/Unify"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Chainguard runtime already runs as the unprivileged "nonroot" user (uid 65532).
# Copy the resolved venv and the application source with that ownership.
COPY --from=builder --chown=65532:65532 /app/.venv /app/.venv
COPY --chown=65532:65532 src /app/src

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src

EXPOSE 8000

# Python-based health check (no curl/shell in the runtime image).
# Explicit timeout plus broad except: any probe error means unhealthy (exit 1)
# without a traceback, and a hung connection cannot outlive --timeout.
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request\ntry:\n    sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/live', timeout=2).status == 200 else 1)\nexcept Exception:\n    sys.exit(1)"]

# Chainguard python sets ENTRYPOINT ["python"]; clear it so CMD is the full
# invocation, then run uvicorn from the venv.
ENTRYPOINT []
CMD ["python", "-m", "uvicorn", "foundry_unify.main:app", "--host", "0.0.0.0", "--port", "8000"]
