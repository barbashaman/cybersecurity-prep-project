#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_tests_core.sh - PR-required pyramid subset (mirrors ci-quality-gate).
# Offline: no Docker stack required. Excludes functional HTTP, E2E Robot, and
# performance_extended (those run via run_all_tests.sh / ci-extended).
# ---------------------------------------------------------------------------
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REQUIRE_DOCKER=0 REQUIRE_GH=0
# shellcheck source=scripts/verify_prerequisites.sh
source "${SCRIPT_DIR}/verify_prerequisites.sh"; verify_prerequisites

main() {
  log_info() { printf '[INFO] %s\n' "$*"; }
  log_ok() { printf '[OK] %s\n' "$*"; }

  log_info "Core pyramid (smoke + component + database + integration + security + performance_fast)"
  PYTHONPATH="${SCRIPT_DIR}/../src:${SCRIPT_DIR}/..${PYTHONPATH:+:${PYTHONPATH}}" \
    python -m pytest \
      tests/test_toolkit_smoke.py \
      tests/domain \
      tests/component \
      tests/database \
      tests/integration \
      tests/security \
      tests/performance \
      -m "not performance_extended" \
      -q
  log_ok "Core pyramid green."
}
main "$@"
