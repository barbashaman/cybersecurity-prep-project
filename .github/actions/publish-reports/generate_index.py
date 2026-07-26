"""Regenerate the `reports` branch index.

Reads every ``runs/**/manifest.json`` in the archive root and renders a single
``index.html`` with the run history table and a success-rate trend chart
(inline SVG - no external assets, so it works both as a plain file and, later,
via GitHub Pages). Stdlib-only.

Usage:
    python generate_index.py --archive-root <dir>
"""
# ruff: noqa: E501  - this module embeds inline CSS/HTML with long style rules.

from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    branch: str
    commit: str
    workflow: str
    iteration: str
    generated_at: str
    success_rate: float
    total: int
    passed: int
    failed: int
    rel_path: str


def _load_runs(archive_root: Path) -> list[RunRecord]:
    records: list[RunRecord] = []
    for manifest_path in sorted(archive_root.glob("runs/**/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        totals = data.get("totals", {})
        run_dir = manifest_path.parent
        records.append(
            RunRecord(
                run_id=str(data.get("run_id", run_dir.name)),
                branch=str(data.get("branch", "unknown")),
                commit=str(data.get("commit", "unknown"))[:12],
                workflow=str(data.get("workflow", "unknown")),
                iteration=str(data.get("iteration", "")),
                generated_at=str(data.get("generated_at", "")),
                success_rate=float(totals.get("success_rate", 0.0)),
                total=int(totals.get("total", 0)),
                passed=int(totals.get("passed", 0)),
                failed=int(totals.get("failed", 0)),
                rel_path=str(run_dir.relative_to(archive_root)).replace("\\", "/"),
            )
        )
    records.sort(key=lambda r: r.generated_at)
    return records


def _trend_svg(records: list[RunRecord]) -> str:
    if not records:
        return "<p class='empty'>No runs archived yet.</p>"
    width, height, pad = 720, 220, 30
    n = len(records)
    span = max(n - 1, 1)
    points: list[str] = []
    dots: list[str] = []
    for i, rec in enumerate(records):
        x = pad + (width - 2 * pad) * (i / span)
        y = pad + (height - 2 * pad) * (1 - rec.success_rate / 100.0)
        points.append(f"{x:.1f},{y:.1f}")
        colour = "#2e7d32" if rec.failed == 0 else "#c62828"
        dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.5' fill='{colour}'></circle>")
    polyline = (
        f"<polyline fill='none' stroke='#38bdf8' stroke-width='2' "
        f"points='{' '.join(points)}'></polyline>"
    )
    baseline = pad + (height - 2 * pad)
    axis = (
        f"<line x1='{pad}' y1='{pad}' x2='{pad}' y2='{baseline}' stroke='#888'></line>"
        f"<line x1='{pad}' y1='{baseline}' x2='{width - pad}' y2='{baseline}' stroke='#888'></line>"
        f"<text x='4' y='{pad + 4}' font-size='10' fill='#888'>100%</text>"
        f"<text x='8' y='{baseline}' font-size='10' fill='#888'>0%</text>"
    )
    return (
        f"<svg viewBox='0 0 {width} {height}' width='100%' role='img' "
        f"aria-label='Success-rate trend'>{axis}{polyline}{''.join(dots)}</svg>"
    )


def _render_index(records: list[RunRecord]) -> str:
    rows: list[str] = []
    for rec in reversed(records):
        colour = "#2e7d32" if rec.failed == 0 else "#c62828"
        rows.append(
            "<tr>"
            f"<td>{html.escape(rec.generated_at)}</td>"
            f"<td>{html.escape(rec.branch)}</td>"
            f"<td><code>{html.escape(rec.commit)}</code></td>"
            f"<td>{html.escape(rec.workflow)}</td>"
            f"<td>{html.escape(rec.iteration)}</td>"
            f"<td style='color:{colour};font-weight:600'>{rec.success_rate:.1f}%</td>"
            f"<td class='num'>{rec.passed}/{rec.total}</td>"
            f"<td><a href='{html.escape(rec.rel_path)}/tests/unified-dashboard.html'>report</a></td>"
            "</tr>"
        )
    body_rows = "".join(rows) or (
        "<tr><td colspan='8' class='empty'>No runs archived yet.</td></tr>"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Pipeline Reports Archive</title>
<style>
 body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:2rem;color:#e2e8f0;background:#0f172a}}
 h1{{margin-bottom:.2rem}}
 .card{{background:#111827;border:1px solid #1f2937;border-radius:.5rem;padding:1rem 1.2rem;margin:1rem 0}}
 table{{border-collapse:collapse;width:100%}}
 th,td{{border:1px solid #1f2937;padding:.45rem .6rem;text-align:left;font-size:.9rem}}
 th{{background:#0b1220}}
 td.num{{text-align:right;font-variant-numeric:tabular-nums}}
 a{{color:#38bdf8}} code{{color:#93c5fd}}
 .empty{{text-align:center;color:#64748b;font-style:italic}}
 .sub{{color:#94a3b8}}
</style></head><body>
<h1>Pipeline Reports Archive</h1>
<p class="sub">Immutable per-run evidence for the OWASP Top 10:2025 countdown.
 Each iteration is a visible dip (Red) and recovery (Green).</p>
<div class="card"><h2>Success-rate trend</h2>{_trend_svg(records)}</div>
<div class="card"><h2>Run history ({len(records)})</h2>
 <table><thead><tr>
  <th>Generated (UTC)</th><th>Branch</th><th>Commit</th><th>Workflow</th>
  <th>Iteration</th><th>Success</th><th>Pass/Total</th><th>Report</th>
 </tr></thead><tbody>{body_rows}</tbody></table></div>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate the reports archive index.")
    parser.add_argument("--archive-root", required=True, type=Path)
    args = parser.parse_args(argv)

    records = _load_runs(args.archive_root)
    index_path = args.archive_root / "index.html"
    index_path.write_text(_render_index(records), encoding="utf-8")
    print(f"Wrote {index_path} ({len(records)} runs).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
