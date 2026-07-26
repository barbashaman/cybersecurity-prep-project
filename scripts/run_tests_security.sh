#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_tests_security.sh - security suites: role-matrix checks (pytest, marker
# 'security') plus a ZAP-proxied pass. Local convenience runner; the full DAST
# (baseline + API scan against the exported OpenAPI contract) runs in ci-dast.
# ---------------------------------------------------------------------------
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REQUIRE_DOCKER=1 REQUIRE_GH=0
# shellcheck source=scripts/verify_prerequisites.sh
source "${SCRIPT_DIR}/verify_prerequisites.sh"; verify_prerequisites
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"; load_environment

main() {
  ensure_stack_up
  local report_dir; report_dir="$(new_run_report_dir)"
  log_info "Security suite -> ${report_dir}/security"

  log_info "Starting ZAP proxy service..."
  compose up -d zap || log_warn "ZAP service failed to start; role-matrix checks will still run."

  compose build tests
  compose run --rm \
    -e TOOLKIT_BASE_URL="http://api:8000" \
    -e HTTP_PROXY="http://zap:8090" \
    -e HTTPS_PROXY="http://zap:8090" \
    tests \
    pytest tests/security \
      -m security \
      --junitxml=/reports/tests/pytest/security-junit.xml \
      --html=/reports/security/role-matrix.html --self-contained-html \
    || { log_error "Security suite reported findings/failures (evidence preserved)."; exit 1; }

  log_ok "Security suite complete."
}
main "$@"
