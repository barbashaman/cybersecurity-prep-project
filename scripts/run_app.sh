#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_app.sh - fail-safe startup of the full stack.
#
# Sources the prerequisite gate and common library, runs Docker preflight,
# builds and starts the compose stack, waits for the API version gate, then
# prints the live Swagger banner.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prerequisite gate (app needs Docker + Python; not gh).
REQUIRE_DOCKER=1 REQUIRE_GH=0
# shellcheck source=scripts/verify_prerequisites.sh
source "${SCRIPT_DIR}/verify_prerequisites.sh"
verify_prerequisites

# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_environment

DETACHED="${DETACHED:-1}"

main() {
  docker_preflight

  log_info "Building images (api, web, database)..."
  compose build api web

  log_info "Starting stack..."
  if [[ "$DETACHED" == "1" ]]; then
    compose up -d database api web
  else
    compose up database api web &
  fi

  version_gate "http://localhost:${API_PORT:-8000}"
  print_swagger_banner

  log_info "Tail logs with:   docker compose -p ${COMPOSE_PROJECT_NAME} logs -f api web"
  log_info "Stop the stack:   docker compose -p ${COMPOSE_PROJECT_NAME} down -v"
}

main "$@"
