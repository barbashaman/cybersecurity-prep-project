#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_all_tests.sh - full suite runner. Produces the same report tree locally
# that CI publishes to the `reports` archive branch, so local and CI output are
# interchangeable:
#
#   reports/runs/<YYYY-MM-DD>/<run_id>-<short_sha>/
#     manifest.json
#     tests/{unified-dashboard.html, robot/*, pytest/*}
#     security/*
#     ...
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
  local rc=0
  log_info "Full suite -> ${report_dir}"

  compose build tests

  log_info "[1/3] API suite"
  compose run --rm -e TOOLKIT_BASE_URL="http://api:8000" tests \
    pytest tests/api -m api \
      --junitxml=/reports/tests/pytest/junit.xml \
      --html=/reports/tests/pytest/report.html --self-contained-html \
    || rc=1

  log_info "[2/3] E2E suite (Robot Framework)"
  compose run --rm -e TOOLKIT_BASE_URL="http://api:8000" -e WEB_BASE_URL="http://web:8080" tests \
    robot --outputdir /reports/tests/robot \
          --output output.xml --report report.html --log log.html \
          tests/e2e \
    || rc=1

  log_info "[3/3] Security suite"
  compose up -d zap || log_warn "ZAP service unavailable."
  compose run --rm -e TOOLKIT_BASE_URL="http://api:8000" tests \
    pytest tests/security -m security \
      --junitxml=/reports/tests/pytest/security-junit.xml \
    || rc=1

  log_info "Rendering unified dashboard + manifest..."
  compose run --rm tests \
    python -m tests.toolkit.reporting.unified_report \
      --report-dir /reports \
      --robot /reports/tests/robot/output.xml \
      --junit /reports/tests/pytest/junit.xml \
      --junit /reports/tests/pytest/security-junit.xml \
      --out /reports/tests/unified-dashboard.html \
      --manifest /reports/manifest.json \
    || log_warn "Report renderer returned non-zero (empty suite is expected in Phase 1)."

  if (( rc == 0 )); then
    log_ok "Full suite green. Report: ${report_dir}/tests/unified-dashboard.html"
  else
    log_error "Full suite has failures. Evidence preserved at ${report_dir} (this is the Red-phase deliverable)."
  fi
  return "$rc"
}
main "$@"
