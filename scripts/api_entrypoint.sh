#!/bin/sh
# API container entrypoint: migrate + seed, then start uvicorn.
# The FastAPI lifespan also runs prepare_database idempotently as a safety net
# for local `uvicorn` invocations that bypass this script.
set -eu

echo "[api-entrypoint] Preparing database (alembic upgrade + optional seed)..."
python - <<'PY'
from ecommerce_backoffice_api.infrastructure.config import Settings
from ecommerce_backoffice_api.infrastructure.persistence.startup import prepare_database

engine, _session_factory = prepare_database(Settings.from_env())
engine.dispose()
PY

echo "[api-entrypoint] Starting uvicorn on ${API_HOST:-0.0.0.0}:${API_PORT:-8000}"
exec uvicorn ecommerce_backoffice_api.presentation.main:app \
  --host "${API_HOST:-0.0.0.0}" \
  --port "${API_PORT:-8000}"
