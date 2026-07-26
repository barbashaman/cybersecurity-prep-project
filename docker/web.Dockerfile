# ---------------------------------------------------------------------------
# Web service image (Jinja2 server-rendered front end).
# Same multi-stage pattern as the API image.
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements-runtime.lock ./
RUN pip install --require-hashes -r requirements-runtime.lock

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps .

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=8080 \
    API_BASE_URL=http://api:8000

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app src ./src
COPY --chown=app:app VERSION ./VERSION

USER app
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import os,urllib.request,sys; port=os.environ.get('WEB_PORT','8080'); sys.exit(0) if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2).status==200 else sys.exit(1)"]

CMD ["sh", "-c", "uvicorn ecommerce_backoffice_web.main:app --host ${WEB_HOST} --port ${WEB_PORT}"]
