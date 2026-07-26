#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# publish.sh - publish one run's report payload to the `reports` archive branch.
#
# Checks out the orphan `reports` branch into a separate worktree (creating it
# on first use), copies the payload into an immutable per-run directory,
# regenerates the index, refreshes `latest/` for main-branch runs, then commits
# and pushes with a pull --rebase retry so concurrent workflows cannot clobber
# each other.
#
# Environment (provided by action.yml):
#   PAYLOAD_DIR   - directory whose contents are the run payload (has manifest.json)
#   REPORT_BRANCH - archive branch name (default: reports)
#   RUN_ID        - unique run id (e.g. GitHub run id)
#   SHORT_SHA     - short commit sha
#   SOURCE_BRANCH - the branch/tag that produced the run
#   IS_PERMANENT  - "true" to mark the run for permanent retention
#   ACTION_DIR    - directory containing generate_index.py
# ---------------------------------------------------------------------------
set -euo pipefail

REPORT_BRANCH="${REPORT_BRANCH:-reports}"
WORKTREE_DIR="$(mktemp -d)"
DATE_DIR="$(date -u +%Y-%m-%d)"
RUN_DIR_NAME="${RUN_ID:-unknown}-${SHORT_SHA:-nosha}"
MAX_RETRIES=5

log() { printf '[publish-reports] %s\n' "$*"; }

if [[ ! -f "${PAYLOAD_DIR}/manifest.json" ]]; then
  log "WARNING: ${PAYLOAD_DIR}/manifest.json missing; publishing payload anyway."
fi

git config --global --add safe.directory "$(pwd)" || true
git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# --- Obtain the reports branch into a worktree (create orphan on first use) ---
git fetch origin "${REPORT_BRANCH}" --depth=1 2>/dev/null || true
if git show-ref --verify --quiet "refs/remotes/origin/${REPORT_BRANCH}"; then
  log "Adding worktree tracking origin/${REPORT_BRANCH}."
  git worktree add "${WORKTREE_DIR}" "origin/${REPORT_BRANCH}" --detach
  git -C "${WORKTREE_DIR}" checkout -B "${REPORT_BRANCH}"
else
  log "Report branch does not exist yet; creating orphan '${REPORT_BRANCH}'."
  git worktree add --detach "${WORKTREE_DIR}"
  git -C "${WORKTREE_DIR}" checkout --orphan "${REPORT_BRANCH}"
  git -C "${WORKTREE_DIR}" reset --hard
  git -C "${WORKTREE_DIR}" clean -fdx
fi

# --- Copy payload into an immutable per-run directory ------------------------
TARGET_DIR="${WORKTREE_DIR}/runs/${DATE_DIR}/${RUN_DIR_NAME}"
mkdir -p "${TARGET_DIR}"
cp -r "${PAYLOAD_DIR}/." "${TARGET_DIR}/"
log "Payload copied to runs/${DATE_DIR}/${RUN_DIR_NAME}."

# --- latest/ mirrors the most recent main-branch run ------------------------
if [[ "${SOURCE_BRANCH:-}" == "main" ]]; then
  rm -rf "${WORKTREE_DIR}/latest"
  mkdir -p "${WORKTREE_DIR}/latest"
  cp -r "${PAYLOAD_DIR}/." "${WORKTREE_DIR}/latest/"
  log "Refreshed latest/ from main-branch run."
fi

# --- Retention marker (pruning is enforced by a separate scheduled job) ------
if [[ "${IS_PERMANENT:-false}" == "true" ]]; then
  touch "${TARGET_DIR}/.keep-permanent"
fi

# --- Regenerate the index ---------------------------------------------------
python "${ACTION_DIR}/generate_index.py" --archive-root "${WORKTREE_DIR}"

# --- Commit -----------------------------------------------------------------
git -C "${WORKTREE_DIR}" add -A
if git -C "${WORKTREE_DIR}" diff --cached --quiet; then
  log "Nothing to publish (no changes)."
  git worktree remove --force "${WORKTREE_DIR}"
  exit 0
fi
git -C "${WORKTREE_DIR}" commit -m "reports: ${SOURCE_BRANCH:-unknown} ${RUN_DIR_NAME} (${WORKFLOW:-ci})"

# --- Push with rebase-retry so concurrent runs don't clobber ----------------
attempt=1
until git -C "${WORKTREE_DIR}" push origin "HEAD:${REPORT_BRANCH}"; do
  if (( attempt >= MAX_RETRIES )); then
    log "ERROR: push failed after ${MAX_RETRIES} attempts."
    git worktree remove --force "${WORKTREE_DIR}"
    exit 1
  fi
  log "Push rejected; rebasing and retrying (attempt ${attempt}/${MAX_RETRIES})."
  git -C "${WORKTREE_DIR}" fetch origin "${REPORT_BRANCH}" || true
  git -C "${WORKTREE_DIR}" rebase "origin/${REPORT_BRANCH}" || {
    log "Rebase hit a conflict; index.html regenerates deterministically, retaking."
    git -C "${WORKTREE_DIR}" rebase --abort || true
    git -C "${WORKTREE_DIR}" reset --hard "origin/${REPORT_BRANCH}"
    # Re-apply payload on top of the latest remote state.
    mkdir -p "${TARGET_DIR}"
    cp -r "${PAYLOAD_DIR}/." "${TARGET_DIR}/"
    python "${ACTION_DIR}/generate_index.py" --archive-root "${WORKTREE_DIR}"
    git -C "${WORKTREE_DIR}" add -A
    git -C "${WORKTREE_DIR}" commit -m "reports: ${SOURCE_BRANCH:-unknown} ${RUN_DIR_NAME} (retry ${attempt})"
  }
  attempt=$((attempt + 1))
  sleep $((attempt * 2))
done

log "Published to ${REPORT_BRANCH}."
git worktree remove --force "${WORKTREE_DIR}"
