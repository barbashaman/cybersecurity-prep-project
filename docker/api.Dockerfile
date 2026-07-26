# ---------------------------------------------------------------------------
# API service image - multi-stage build on python:3.12-slim.
#
# Stage 1 (builder): install hash-pinned runtime dependencies into a venv.
# Stage 2 (runtime): copy the venv, add source, run as a non-root user with a
#                    Python-based healthcheck (no curl in the runtime image).
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Install runtime dependencies from the hash-pinned lock (reproducible builds).
COPY requirements-runtime.lock ./
RUN pip install --require-hashes -r requirements-runtime.lock

# Install the application package itself (no deps; they came from the lock).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps .

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    API_HOST=0.0.0.0 \
    API_PORT=8000

# Non-root user (baseline good practice; the deliberate misconfig baseline for
# iter-09 lives at the app/config level - DEBUG, CORS, /docs exposure - not here).
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app src ./src
COPY --chown=app:app VERSION ./VERSION

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import os,urllib.request,sys; port=os.environ.get('API_PORT','8000'); sys.exit(0) if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2).status==200 else sys.exit(1)"]

# Application object is provided by Phase 1b; the operational entrypoint
# (health/version/OpenAPI) is provided by presentation.main:app.
CMD ["sh", "-c", "uvicorn ecommerce_backoffice_api.presentation.main:app --host ${API_HOST} --port ${API_PORT}"]
