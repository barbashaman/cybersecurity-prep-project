Document Name: Reporting and Evidence Architecture
Covered Elements: Unified test dashboard, advisory generation, two-tier artifact store, archive layout, retention policy
Creation Date: 26/07/2026-13:25:00.000

# Reporting and Evidence Architecture

Evidence is the deliverable. Every pipeline run - including the deliberately
failing Red-phase runs - publishes a complete, browsable record.

## Unified test dashboard

`tests/toolkit/reporting/unified_report.py` (stdlib-only, so it runs identically
in the container and locally) merges Robot Framework `output.xml` and pytest
JUnit XML into one `unified-dashboard.html` with per-suite rows, a success-rate
figure and per-suite bars. It also emits the run `manifest.json`.

## Advisories are generated, not written

`tests/toolkit/reporting/advisory_generator.py` renders markdown from the Jinja2
template at `documentation/advisories/advisory_template.md.j2`, fed by the
failing test's structured result plus scanner evidence (ZAP alert id, Bandit
test id, Semgrep rule id). Every document carries the mandated header:

```
Document Name: ...
Covered Elements: ...
Creation Date: dd/MM/yyyy-HH:mm:ss.fff
```

`ci-advisory.yml` generates and commits advisories on iteration branches.

## Two-tier artifact store

The two tiers solve different problems.

**Tier 1 — per-run Actions artifacts.** Every job uploads its `report-payload`
via `actions/upload-artifact@v4` under a deterministic name
(`reports-<workflow>-<run_number>-<sha>`), 90-day retention, `if: always()` so
failing runs still publish their evidence.

**Tier 2 — the `reports` archive branch.** An orphan branch sharing no history
with `main`, so report commits never pollute code diffs, blame or PR reviews. A
reusable composite action (`.github/actions/publish-reports/`) checks the branch
out into a worktree (creating the orphan on first use), copies the payload into
an immutable per-run directory, regenerates `index.html`, and pushes with a
`git pull --rebase` retry loop. All publishing jobs share a
`concurrency: { group: reports-publish }` lock so concurrent workflows cannot
clobber each other.

### Archive layout

Identical to what `run_all_tests.sh` produces locally, so CI and local output
are interchangeable:

```
index.html                              # generated: run history + success-rate trend
runs/<YYYY-MM-DD>/<run_id>-<short_sha>/
  manifest.json
  tests/{unified-dashboard.html, robot/*, pytest/*}
  security/{zap/*, bandit/*, semgrep/*, trivy/*}
  supply-chain/{sbom.cyclonedx.json, pip-audit.json}
  api-contract/{openapi.json, swagger-ui/}
  advisories/*.md
latest/                                 # copy of the most recent main-branch run
```

The generated `index.html` reads every `manifest.json` and plots the
success-rate trend as an inline SVG - twenty visible dips and recoveries, one
pair per iteration. `manifest.schema.json` documents the manifest contract.

## Retention policy

`reports-retention.yml` (scheduled) keeps `main` and `iter-*` tag runs
permanently (a `.keep-permanent` marker) and prunes ordinary feature-branch runs
beyond the most recent 20 (`prune.py`).

## Forward path

Because the branch serves `index.html` at its root, enabling GitHub Pages
against it later produces a live URL with no rework.
