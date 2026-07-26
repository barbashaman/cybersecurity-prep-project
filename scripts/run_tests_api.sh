#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_tests_api.sh - API / integration suite (pytest-bdd + Playwright
# APIRequestContext) executed inside the `tests` container against the running
# API. Sources the version gate so it cannot test a stale image.
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
  log_info "API suite -> ${report_dir}/tests/pytest"

  compose build tests
  compose run --rm \
    -e TOOLKIT_TRANSPORT="${TOOLKIT_TRANSPORT:-http}" \
    -e TOOLKIT_BASE_URL="http://api:8000" \
    tests \
    pytest tests/api \
      -m api \
      --junitxml=/reports/tests/pytest/junit.xml \
      --html=/reports/tests/pytest/report.html --self-contained-html \
    || { log_error "API suite reported failures (evidence preserved)."; exit 1; }

  log_ok "API suite complete."
}
main "$@"
