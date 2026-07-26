#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/lib/common.sh
#
# Shared library sourced by every runner. Centralises:
#   * Docker preflight  - daemon reachable, stale container / orphan-volume
#                         cleanup, port-conflict detection.
#   * Version gate      - poll /health, compare reported version to $VERSION,
#                         abort on mismatch so no suite tests a stale image.
#   * Swagger banner    - print the live /docs address after healthcheck.
#
# Not meant to be executed directly.
# ---------------------------------------------------------------------------
set -euo pipefail

# --- Resolve repo root regardless of caller CWD -----------------------------
COMMON_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${COMMON_SH_DIR}/../.." && pwd)"

# --- Load .env (fall back to .env.example) ----------------------------------
load_environment() {
  local env_file="${REPO_ROOT}/.env"
  if [[ ! -f "$env_file" ]]; then
    env_file="${REPO_ROOT}/.env.example"
    log_warn "No .env found; falling back to .env.example (local defaults)."
  fi
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}

# --- Logging ----------------------------------------------------------------
if [[ -t 1 ]]; then
  readonly C_RED='\033[0;31m'; readonly C_GREEN='\033[0;32m'
  readonly C_YELLOW='\033[0;33m'; readonly C_BLUE='\033[0;34m'
  readonly C_BOLD='\033[1m'; readonly C_RESET='\033[0m'
else
  readonly C_RED=''; readonly C_GREEN=''; readonly C_YELLOW=''
  readonly C_BLUE=''; readonly C_BOLD=''; readonly C_RESET=''
fi
log_info()  { printf "${C_BLUE}[INFO]${C_RESET}  %s\n"  "$*"; }
log_ok()    { printf "${C_GREEN}[ OK ]${C_RESET}  %s\n" "$*"; }
log_warn()  { printf "${C_YELLOW}[WARN]${C_RESET}  %s\n" "$*"; }
log_error() { printf "${C_RED}[FAIL]${C_RESET}  %s\n" "$*" >&2; }
die()       { log_error "$*"; exit 1; }

# --- Config -----------------------------------------------------------------
readonly COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ecommerce_backoffice}"
readonly HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
readonly HEALTH_POLL_INTERVAL_SECONDS="${HEALTH_POLL_INTERVAL_SECONDS:-3}"

compose() {
  docker compose -p "${COMPOSE_PROJECT_NAME}" "$@"
}

expected_version() {
  if [[ -n "${VERSION:-}" ]]; then
    printf "%s" "${VERSION}"
  elif [[ -f "${REPO_ROOT}/VERSION" ]]; then
    tr -d '[:space:]' < "${REPO_ROOT}/VERSION"
  else
    die "VERSION not set and ${REPO_ROOT}/VERSION missing; cannot run the version gate."
  fi
}

# ---------------------------------------------------------------------------
# Docker preflight
# ---------------------------------------------------------------------------
docker_preflight() {
  log_info "Docker preflight..."
  docker info >/dev/null 2>&1 || die "PREFLIGHT_DAEMON: Docker daemon unreachable. Start Docker Desktop."

  # Remove stale containers from a previous, half-torn-down run.
  local stale
  stale="$(docker ps -aq --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}" --filter "status=exited" 2>/dev/null || true)"
  if [[ -n "$stale" ]]; then
    log_warn "Removing stale exited containers from a previous run."
    # shellcheck disable=SC2086
    docker rm -f $stale >/dev/null 2>&1 || true
  fi

  # Warn about orphaned anonymous volumes.
  local dangling
  dangling="$(docker volume ls -qf dangling=true 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${dangling:-0}" != "0" ]]; then
    log_warn "${dangling} dangling volume(s) present. Run 'docker volume prune' to reclaim space."
  fi

  detect_port_conflicts
  log_ok "Docker preflight passed."
}

detect_port_conflicts() {
  local ports=("${API_PORT:-8000}" "${WEB_PORT:-8080}" "${POSTGRES_PORT:-5432}" "${ZAP_PORT:-8090}")
  local port in_use=0
  for port in "${ports[@]}"; do
    # Best-effort, cross-platform: prefer ss, then netstat.
    if command -v ss >/dev/null 2>&1; then
      if ss -ltn 2>/dev/null | grep -qE "[:.]${port}[[:space:]]"; then
        log_warn "Port ${port} already in use on the host."
        in_use=1
      fi
    elif command -v netstat >/dev/null 2>&1; then
      if netstat -an 2>/dev/null | grep -qE "[:.]${port}[[:space:]].*LISTEN"; then
        log_warn "Port ${port} already in use on the host."
        in_use=1
      fi
    fi
  done
  (( in_use == 0 )) && log_ok "No host port conflicts detected."
  return 0
}

# ---------------------------------------------------------------------------
# Version gate - poll /health and compare the reported version to $VERSION.
# ---------------------------------------------------------------------------
version_gate() {
  local base_url="${1:-http://localhost:${API_PORT:-8000}}"
  local want deadline reported
  want="$(expected_version)"
  deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))

  log_info "Version gate: waiting for ${base_url}/health to report version '${want}'."
  while (( $(date +%s) < deadline )); do
    local body
    if body="$(curl -fsS --max-time 5 "${base_url}/health" 2>/dev/null)"; then
      reported="$(printf '%s' "$body" | grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*"([^"]*)"$/\1/')"
      if [[ -z "$reported" ]]; then
        log_warn "/health reachable but no version field yet; retrying."
      elif [[ "$reported" == "$want" ]]; then
        log_ok "Version gate passed: running version '${reported}' matches expected '${want}'."
        return 0
      else
        die "VERSION_MISMATCH: /health reports '${reported}' but expected '${want}'. Rebuild the image before testing (a stale image is running)."
      fi
    fi
    sleep "${HEALTH_POLL_INTERVAL_SECONDS}"
  done
  die "VERSION_GATE_TIMEOUT: ${base_url}/health did not become healthy within ${HEALTH_TIMEOUT_SECONDS}s."
}

# ---------------------------------------------------------------------------
# Swagger banner - printed after the healthcheck passes.
# ---------------------------------------------------------------------------
print_swagger_banner() {
  local api_port="${API_PORT:-8000}"
  local web_port="${WEB_PORT:-8080}"
  printf "\n"
  printf "${C_BOLD}${C_GREEN}"
  printf '========================================================================\n'
  printf '  E-COMMERCE BACKOFFICE  -  version %s  -  STACK IS UP\n' "$(expected_version)"
  printf '========================================================================\n'
  printf "${C_RESET}${C_BOLD}"
  printf '  Swagger UI (OpenAPI 3.1) : http://localhost:%s/docs\n'        "$api_port"
  printf '  ReDoc                    : http://localhost:%s/redoc\n'       "$api_port"
  printf '  OpenAPI contract (JSON)  : http://localhost:%s/openapi.json\n' "$api_port"
  printf '  Health                   : http://localhost:%s/health\n'      "$api_port"
  printf '  Web front end            : http://localhost:%s/\n'            "$web_port"
  printf "${C_RESET}${C_BOLD}${C_GREEN}"
  printf '========================================================================\n'
  printf "${C_RESET}\n"
}

# ---------------------------------------------------------------------------
# ensure_stack_up - bring up database + api + web if not already healthy,
# then run the version gate. Used by every test runner so a suite can never
# silently test a stale image.
# ---------------------------------------------------------------------------
ensure_stack_up() {
  docker_preflight
  if ! curl -fsS --max-time 3 "http://localhost:${API_PORT:-8000}/health" >/dev/null 2>&1; then
    log_info "Stack not responding; building and starting it."
    compose build api web
    compose up -d database api web
  fi
  version_gate "http://localhost:${API_PORT:-8000}"
}

# ---------------------------------------------------------------------------
# new_run_report_dir - create the immutable per-run report directory mirroring
# the Tier-2 archive layout, and echo its path. RUN_ID / SHORT_SHA are honoured
# if exported (CI), otherwise derived locally.
# ---------------------------------------------------------------------------
new_run_report_dir() {
  local date_dir run_id short_sha base
  date_dir="$(date -u +%Y-%m-%d)"
  run_id="${RUN_ID:-local-$(date -u +%H%M%S)}"
  short_sha="${SHORT_SHA:-$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || echo nogit)}"
  base="${REPO_ROOT}/reports/runs/${date_dir}/${run_id}-${short_sha}"
  mkdir -p "${base}/tests/robot" "${base}/tests/pytest" \
           "${base}/security/zap" "${base}/security/bandit" \
           "${base}/security/semgrep" "${base}/security/trivy" \
           "${base}/supply-chain" "${base}/api-contract" "${base}/advisories"
  printf "%s" "${base}"
}
