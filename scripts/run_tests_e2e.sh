#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_tests_e2e.sh - end-to-end / web-functional suite (Robot Framework)
# executed inside the `tests` container against the running web + API tiers.
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
  log_info "E2E suite -> ${report_dir}/tests/robot"

  compose build tests
  compose run --rm \
    -e TOOLKIT_BASE_URL="http://api:8000" \
    -e WEB_BASE_URL="http://web:8080" \
    tests \
    robot --outputdir /reports/tests/robot \
          --output output.xml --report report.html --log log.html \
          tests/e2e \
    || { log_error "E2E suite reported failures (evidence preserved)."; exit 1; }

  log_ok "E2E suite complete."
}
main "$@"
