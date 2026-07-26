#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# verify_prerequisites.sh
#
# Blocking Step-0 gate. Every other script sources this so that a missing
# prerequisite produces a single, named error instead of a confusing failure
# deep inside Docker or pytest.
#
# Sourced usage (preferred):   source scripts/verify_prerequisites.sh
# Standalone usage:            bash   scripts/verify_prerequisites.sh
# ---------------------------------------------------------------------------
set -euo pipefail

# Colours (disabled when not a TTY).
if [[ -t 1 ]]; then
  readonly _C_RED='\033[0;31m'; readonly _C_GREEN='\033[0;32m'
  readonly _C_YELLOW='\033[0;33m'; readonly _C_RESET='\033[0m'
else
  readonly _C_RED=''; readonly _C_GREEN=''; readonly _C_YELLOW=''; readonly _C_RESET=''
fi

readonly REQUIRED_PYTHON_MAJOR_MINOR="3.12"

_prereq_ok()   { printf "${_C_GREEN}[ OK ]${_C_RESET}   %s\n"   "$1"; }
_prereq_warn() { printf "${_C_YELLOW}[WARN]${_C_RESET}   %s\n"   "$1"; }
_prereq_fail() { printf "${_C_RED}[FAIL]${_C_RESET}   %s\n"      "$1" >&2; }

# ---------------------------------------------------------------------------
# Individual checks. Each returns non-zero and prints a named remediation.
# ---------------------------------------------------------------------------

verify_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    _prereq_fail "PREREQUISITE_DOCKER_MISSING: 'docker' not found on PATH."
    printf "        Windows: run 'wsl --install' (reboot), then install Docker Desktop\n"
    printf "        with the WSL2 backend and start it.\n"
    return 1
  fi
  if ! docker info >/dev/null 2>&1; then
    _prereq_fail "PREREQUISITE_DOCKER_DAEMON_UNREACHABLE: docker is installed but the daemon is not responding."
    printf "        Start Docker Desktop and wait until the whale icon is steady.\n"
    return 1
  fi
  # compose v2 plugin
  if ! docker compose version >/dev/null 2>&1; then
    _prereq_fail "PREREQUISITE_COMPOSE_MISSING: 'docker compose' (v2) plugin not available."
    return 1
  fi
  _prereq_ok "Docker daemon reachable and 'docker compose' available."
  return 0
}

verify_python() {
  local candidate="" version=""
  for candidate in "python3.12" "python3" "python" "py"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if [[ "$candidate" == "py" ]]; then
        version="$(py -3.12 --version 2>/dev/null | awk '{print $2}')" || true
      else
        version="$("$candidate" --version 2>/dev/null | awk '{print $2}')" || true
      fi
      if [[ "$version" == ${REQUIRED_PYTHON_MAJOR_MINOR}.* ]]; then
        _prereq_ok "Python ${version} available (via '${candidate}')."
        return 0
      fi
    fi
  done
  _prereq_fail "PREREQUISITE_PYTHON_312_MISSING: Python ${REQUIRED_PYTHON_MAJOR_MINOR} not found."
  printf "        Install with 'py install 3.12' or 'winget install -e --id Python.Python.3.12'.\n"
  printf "        (Playwright/Robot Framework wheels are not reliably published for newer Pythons.)\n"
  return 1
}

verify_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    _prereq_fail "PREREQUISITE_GH_MISSING: GitHub CLI 'gh' not found on PATH."
    printf "        Install: winget install -e --id GitHub.cli\n"
    return 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    _prereq_fail "PREREQUISITE_GH_UNAUTHENTICATED: 'gh' is installed but not authenticated."
    printf "        Run 'gh auth login -h github.com' (or export a valid GH_TOKEN).\n"
    return 1
  fi
  _prereq_ok "GitHub CLI authenticated."
  return 0
}

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
# REQUIRE_GH   - set to 0 to skip the gh check (app/test runners do not need it).
# REQUIRE_DOCKER - set to 0 to skip the docker check.
# ---------------------------------------------------------------------------
verify_prerequisites() {
  local require_docker="${REQUIRE_DOCKER:-1}"
  local require_gh="${REQUIRE_GH:-0}"
  local failures=0

  printf "==> Verifying prerequisites\n"
  verify_python || failures=$((failures + 1))
  if [[ "$require_docker" == "1" ]]; then
    verify_docker || failures=$((failures + 1))
  fi
  if [[ "$require_gh" == "1" ]]; then
    verify_gh || failures=$((failures + 1))
  fi

  if (( failures > 0 )); then
    _prereq_fail "${failures} prerequisite check(s) failed. Resolve the items above and re-run."
    return 1
  fi
  _prereq_ok "All required prerequisites satisfied."
  return 0
}

# Run immediately when executed directly (not when sourced).
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  REQUIRE_DOCKER="${REQUIRE_DOCKER:-1}"
  REQUIRE_GH="${REQUIRE_GH:-1}"
  verify_prerequisites
fi
