"""Unified test dashboard + manifest generator.

Merges Robot Framework ``output.xml`` and pytest JUnit XML into a single,
self-contained HTML dashboard with per-suite descriptions and a success-rate
chart, and writes the run ``manifest.json`` consumed by the archive index.

Deliberately stdlib-only so it runs identically inside the ``tests`` container
and on a developer machine with no extra dependencies. Handles missing/empty
inputs gracefully - an empty suite is the expected Phase 1 state.

Usage:
    python -m tests.toolkit.reporting.unified_report \
        --report-dir /reports \
        --robot /reports/tests/robot/output.xml \
        --junit /reports/tests/pytest/junit.xml \
        --out /reports/tests/unified-dashboard.html \
        --manifest /reports/manifest.json
"""

from __future__ import annotations

import argparse
import html
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True, slots=True)
class SuiteResult:
    """Aggregated outcome for one test suite."""

    name: str
    framework: str
    total: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return round(100.0 * self.passed / self.total, 1)


@dataclass(slots=True)
class RunSummary:
    """The whole run, across every suite."""

    suites: list[SuiteResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(s.total for s in self.suites)

    @property
    def passed(self) -> int:
        return sum(s.passed for s in self.suites)

    @property
    def failed(self) -> int:
        return sum(s.failed for s in self.suites)

    @property
    def skipped(self) -> int:
        return sum(s.skipped for s in self.suites)

    @property
    def duration_seconds(self) -> float:
        return round(sum(s.duration_seconds for s in self.suites), 3)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return round(100.0 * self.passed / self.total, 1)


def _parse_junit(path: Path) -> list[SuiteResult]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    try:
        root = ElementTree.parse(path).getroot()  # noqa: S314 - trusted CI-generated XML
    except ElementTree.ParseError:
        return []
    testsuites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    results: list[SuiteResult] = []
    for suite in testsuites:
        total = int(suite.get("tests", "0"))
        failed = int(suite.get("failures", "0")) + int(suite.get("errors", "0"))
        skipped = int(suite.get("skipped", "0"))
        passed = max(total - failed - skipped, 0)
        duration = float(suite.get("time", "0") or "0")
        name = suite.get("name") or path.stem
        results.append(
            SuiteResult(
                name=f"pytest: {name}",
                framework="pytest",
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_seconds=duration,
            )
        )
    return results


def _parse_robot(path: Path) -> list[SuiteResult]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    try:
        root = ElementTree.parse(path).getroot()  # noqa: S314 - trusted CI-generated XML
    except ElementTree.ParseError:
        return []
    stat = root.find("./statistics/total/stat")
    if stat is None:
        return []
    passed = int(stat.get("pass", "0"))
    failed = int(stat.get("fail", "0"))
    skipped = int(stat.get("skip", "0"))
    total = passed + failed + skipped
    return [
        SuiteResult(
            name="Robot Framework (e2e)",
            framework="robot",
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_seconds=0.0,
        )
    ]


def _bar(rate: float) -> str:
    filled = int(round(rate / 5.0))
    return "#" * filled + "-" * (20 - filled)


def _render_html(summary: RunSummary, meta: dict[str, str]) -> str:
    rows: list[str] = []
    for suite in summary.suites:
        rows.append(
            "<tr>"
            f"<td>{html.escape(suite.name)}</td>"
            f"<td class='num'>{suite.total}</td>"
            f"<td class='num pass'>{suite.passed}</td>"
            f"<td class='num fail'>{suite.failed}</td>"
            f"<td class='num skip'>{suite.skipped}</td>"
            f"<td class='num'>{suite.duration_seconds:.2f}s</td>"
            f"<td><span class='bar'>{_bar(suite.success_rate)}</span> "
            f"{suite.success_rate:.1f}%</td>"
            "</tr>"
        )
    if not rows:
        rows.append(
            "<tr><td colspan='7' class='empty'>No test results found "
            "(empty suite - expected during Phase 1 bootstrap).</td></tr>"
        )
    meta_rows = "".join(
        f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>" for k, v in meta.items()
    )
    overall = summary.success_rate
    colour = "#2e7d32" if summary.failed == 0 else "#c62828"
    generated_at = meta.get("generated_at", "")
    footer_note = f"Generated by unified_report at {generated_at}"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Unified Test Dashboard</title>
<style>
 body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:2rem;color:#222}}
 h1{{margin-bottom:.2rem}}
 .rate{{font-size:2.5rem;font-weight:700;color:{colour}}}
 dl{{display:grid;grid-template-columns:max-content 1fr;gap:.2rem 1rem;margin:1rem 0}}
 dt{{font-weight:600;color:#555}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem}}
 th,td{{border:1px solid #ddd;padding:.5rem .7rem;text-align:left}}
 th{{background:#f4f4f4}}
 td.num{{text-align:right;font-variant-numeric:tabular-nums}}
 .pass{{color:#2e7d32}} .fail{{color:#c62828}} .skip{{color:#f9a825}}
 .bar{{font-family:ui-monospace,Consolas,monospace;letter-spacing:-1px}}
 .empty{{text-align:center;color:#888;font-style:italic}}
 footer{{margin-top:2rem;color:#888;font-size:.85rem}}
</style></head><body>
<h1>Unified Test Dashboard</h1>
<div class="rate">{overall:.1f}%<span style="font-size:1rem;color:#666"> success</span></div>
<dl>{meta_rows}
 <dt>Total</dt><dd>{summary.total}</dd>
 <dt>Passed</dt><dd>{summary.passed}</dd>
 <dt>Failed</dt><dd>{summary.failed}</dd>
 <dt>Skipped</dt><dd>{summary.skipped}</dd>
 <dt>Duration</dt><dd>{summary.duration_seconds:.2f}s</dd>
</dl>
<table>
 <thead><tr><th>Suite</th><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th>
 <th>Duration</th><th>Success rate</th></tr></thead>
 <tbody>{''.join(rows)}</tbody>
</table>
<footer>{footer_note}</footer>
</body></html>
"""


def _collect_meta() -> dict[str, str]:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": generated_at,
        "branch": os.environ.get("GITHUB_REF_NAME", os.environ.get("BRANCH", "local")),
        "commit": os.environ.get("GITHUB_SHA", os.environ.get("SHORT_SHA", "unknown")),
        "workflow": os.environ.get("GITHUB_WORKFLOW", os.environ.get("WORKFLOW", "local")),
        "run_id": os.environ.get("GITHUB_RUN_ID", os.environ.get("RUN_ID", "local")),
        "iteration": os.environ.get("ITERATION", "phase-1-bootstrap"),
    }


def _write_manifest(path: Path, summary: RunSummary, meta: dict[str, str]) -> None:
    manifest = {
        "schema_version": 1,
        "branch": meta["branch"],
        "commit": meta["commit"],
        "workflow": meta["workflow"],
        "run_id": meta["run_id"],
        "iteration": meta["iteration"],
        "generated_at": meta["generated_at"],
        "totals": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "skipped": summary.skipped,
            "success_rate": summary.success_rate,
            "duration_seconds": summary.duration_seconds,
        },
        "suites": [asdict(s) | {"success_rate": s.success_rate} for s in summary.suites],
        "statuses": {
            "tests": "passed" if summary.failed == 0 else "failed",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_summary(robot_paths: list[Path], junit_paths: list[Path]) -> RunSummary:
    summary = RunSummary()
    for junit in junit_paths:
        summary.suites.extend(_parse_junit(junit))
    for robot in robot_paths:
        summary.suites.extend(_parse_robot(robot))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge test results into a unified dashboard.")
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--robot", action="append", default=[], type=Path)
    parser.add_argument("--junit", action="append", default=[], type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)

    summary = build_summary(args.robot, args.junit)
    meta = _collect_meta()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_render_html(summary, meta), encoding="utf-8")
    _write_manifest(args.manifest, summary, meta)

    print(
        f"Unified dashboard: {args.out} "
        f"({summary.total} tests, {summary.success_rate:.1f}% success)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
