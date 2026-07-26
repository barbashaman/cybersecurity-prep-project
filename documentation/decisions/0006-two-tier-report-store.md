Document Name: ADR 0006 - Two-tier report store on an orphan reports branch
Covered Elements: Evidence storage strategy, orphan branch, concurrency lock, retention
Creation Date: 26/07/2026-13:35:00.000

# ADR 0006: Two-tier report store on an orphan `reports` branch

- **Status:** Accepted
- **Context:** Debugging the run in front of you and preserving a permanent,
  browsable evidence trail are different needs. Report commits must not pollute
  code history.
- **Decision:** Two tiers. **Tier 1** — per-run `actions/upload-artifact`
  (90-day, `if: always()`). **Tier 2** — an **orphan `reports` branch** in the
  same repo, written by a composite action using a git worktree, immutable
  per-run directories, a regenerated `index.html`, and a rebase-retry push under
  a shared `concurrency: reports-publish` lock. Retention keeps `main` and
  `iter-*` tag runs permanently, pruning other feature runs beyond 20.
- **Alternatives:** A separate storage bucket or an external dashboard service —
  rejected for a self-contained, zero-extra-infrastructure portfolio. A normal
  branch or committing reports to `main` — rejected because it pollutes diffs,
  blame and PR reviews.
- **Consequences:** Failing (Red) runs still publish evidence. Enabling GitHub
  Pages against the branch later yields a live URL with no rework.
