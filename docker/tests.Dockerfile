# ---------------------------------------------------------------------------
# Tests image - carries the full toolchain (pytest, pytest-bdd, Playwright,
# Robot Framework) plus the security tooling. Installs the complete, all-extras
# hash-pinned lock so CI and local runs resolve identical versions.
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.lock ./
RUN pip install --require-hashes -r requirements.lock

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app

# Playwright's Chromium needs a set of system libraries. curl is handy for the
# health probes the runners perform from inside the network.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system tester && useradd --system --gid tester --home-dir /app tester
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Install the Playwright browser used by the API request context.
RUN python -m playwright install chromium

COPY --chown=tester:tester pyproject.toml README.md VERSION ./
COPY --chown=tester:tester src ./src
COPY --chown=tester:tester tests ./tests

USER tester
# Default to showing help; runners override the command.
CMD ["pytest", "--collect-only", "-q"]
