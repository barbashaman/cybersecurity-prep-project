"""Enforce the reports archive retention policy.

Runs marked permanent (a ``.keep-permanent`` marker, written for ``main`` and
``iter-*`` tag runs) are always kept. Of the remaining ordinary feature-branch
runs, only the most recent ``--keep`` (default 20) are retained; older ones are
deleted. Stdlib-only; operates on a checked-out archive worktree.

Usage:
    python prune.py --archive-root <dir> [--keep 20]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _run_dirs(archive_root: Path) -> list[Path]:
    return [p.parent for p in archive_root.glob("runs/**/manifest.json")]


def prune(archive_root: Path, keep: int) -> tuple[int, int]:
    permanent: list[Path] = []
    prunable: list[Path] = []
    for run_dir in _run_dirs(archive_root):
        if (run_dir / ".keep-permanent").exists():
            permanent.append(run_dir)
        else:
            prunable.append(run_dir)

    # Most recent first by directory mtime (deterministic enough for pruning).
    prunable.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    to_delete = prunable[keep:]
    for run_dir in to_delete:
        shutil.rmtree(run_dir, ignore_errors=True)

    return len(permanent) + min(len(prunable), keep), len(to_delete)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prune the reports archive.")
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--keep", type=int, default=20)
    args = parser.parse_args(argv)

    kept, deleted = prune(args.archive_root, args.keep)
    print(f"Retention: kept {kept} run(s), pruned {deleted} feature-branch run(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
