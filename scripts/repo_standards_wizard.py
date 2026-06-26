#!/usr/bin/env python3
"""Start the Textual repo-standards migration wizard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Textual wizard for migrating one repository to repo-standards."
    )
    parser.add_argument("--repo", type=Path, default=None, help="Target repository path.")
    parser.add_argument(
        "--standards",
        type=Path,
        default=REPO_ROOT,
        help=f"repo-standards checkout path (default: {REPO_ROOT}).",
    )
    parser.add_argument(
        "--base-ref",
        default="main",
        help="Base ref used for assessment context (default: main).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from repo_standards.tui.app import RepoStandardsWizardApp
    except ImportError as exc:
        print(
            "Textual is not installed. Install optional TUI dependencies with:\n"
            "  python3 -m pip install -r requirements-tui.txt",
            file=sys.stderr,
        )
        print(f"Import error: {exc}", file=sys.stderr)
        return 1

    app = RepoStandardsWizardApp(
        repo=args.repo.resolve() if args.repo else None,
        standards=args.standards.resolve(),
        base_ref=args.base_ref,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

