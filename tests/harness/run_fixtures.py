#!/usr/bin/env python3
"""Run repo-standards detect -> apply -> assess against committed fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - Dockerfile installs pyyaml
    raise SystemExit(
        "PyYAML is required. Install with: python3 -m pip install pyyaml"
    ) from exc

HARNESS_DIR = Path(__file__).resolve().parent
TESTS_DIR = HARNESS_DIR.parent
DEFAULT_STANDARDS = TESTS_DIR.parent


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"+ {' '.join(cmd)}", flush=True)
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr, flush=True)
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(cmd)}"
        )
    return completed


def load_expectations(tests_dir: Path) -> dict[str, Any]:
    path = tests_dir / "harness" / "expectations.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "fixtures" not in data:
        raise ValueError(f"Invalid expectations file: {path}")
    return data["fixtures"]


def prepare_workdir(fixture_src: Path, workdir: Path) -> None:
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(fixture_src, workdir)
    run(["git", "init"], cwd=workdir)
    run(["git", "config", "user.email", "fixture@test.local"], cwd=workdir)
    run(["git", "config", "user.name", "Fixture Test"], cwd=workdir)
    run(["git", "add", "."], cwd=workdir)
    run(["git", "commit", "-m", "chore: initial fixture snapshot"], cwd=workdir)
    run(["git", "branch", "-M", "main"], cwd=workdir)


def build_agent_command(
    standards: Path,
    workdir: Path,
    spec: dict[str, Any],
    *,
    skip_rulesync: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(standards / "scripts" / "repo_standards_agent.py"),
        "--repo",
        str(workdir),
        "--standards",
        str(standards),
        "--yes",
        "--apply",
        "--mode",
        spec["mode"],
        "--adoption-level",
        spec["adoption_level"],
        "--visibility",
        spec["visibility"],
        "--license",
        spec["license"],
    ]
    if spec.get("profile"):
        cmd.extend(["--profile", spec["profile"]])
    if skip_rulesync:
        cmd.append("--skip-rulesync")
    return cmd


def run_fixture(
    name: str,
    spec: dict[str, Any],
    *,
    standards: Path,
    tests_dir: Path,
    workdir: Path | None,
    keep_workdir: bool,
    skip_assess: bool,
    skip_rulesync: bool,
) -> tuple[bool, str, Path]:
    fixture_src = tests_dir / "fixtures" / name
    if not fixture_src.is_dir():
        return False, f"fixture source missing: {fixture_src}", Path()

    owns_temp = workdir is None
    target = workdir or Path(tempfile.mkdtemp(prefix=f"repo-standards-{name}-"))

    try:
        prepare_workdir(fixture_src, target)

        detect = run(
            [
                sys.executable,
                str(standards / "scripts" / "detect_repo_standard.py"),
                "--repo",
                str(target),
                "--standards",
                str(standards),
                "--format",
                "json",
            ],
            check=True,
        )
        detection = json.loads(detect.stdout)
        expected_profile = spec["detected_profile"]
        actual_profile = detection.get("recommended_profile")
        if actual_profile != expected_profile:
            return (
                False,
                f"detection profile mismatch: expected {expected_profile}, got {actual_profile}",
                target,
            )

        agent = run(
            build_agent_command(
                standards,
                target,
                spec,
                skip_rulesync=skip_rulesync,
            ),
            check=False,
        )
        if agent.returncode != 0:
            return False, "repo_standards_agent apply failed", target

        for rel in spec.get("expected_files", []):
            if skip_rulesync and rel in {"AGENTS.md", ".cursor", ".agents"}:
                continue
            if not (target / rel).exists():
                return False, f"missing expected file: {rel}", target

        if not skip_assess:
            assess = run(
                [
                    sys.executable,
                    str(standards / "scripts" / "assess_repo_standards.py"),
                    "--repo",
                    str(target),
                    "--standards",
                    str(standards),
                    "--base-ref",
                    "HEAD",
                    "--output-dir",
                    str(target / ".standards-assessment"),
                    "--run-safe-checks",
                ],
                check=False,
            )
            if assess.returncode != 0:
                return False, "assessment reported blockers or failed", target

        return True, "ok", target
    finally:
        if owns_temp and not keep_workdir and target.exists():
            shutil.rmtree(target, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--standards",
        type=Path,
        default=DEFAULT_STANDARDS,
        help="Path to repo-standards root.",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=TESTS_DIR,
        help="Path to tests/ directory.",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Run a single fixture by name.",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="Use a fixed workdir (for act follow-up).",
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Do not delete temporary workdirs after a run.",
    )
    parser.add_argument(
        "--skip-assess",
        action="store_true",
        help="Stop after apply/file assertions (for act prep).",
    )
    parser.add_argument(
        "--skip-rulesync",
        action="store_true",
        help="Do not run Rulesync during apply; useful for offline local fixture checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    standards = args.standards.resolve()
    tests_dir = args.tests_dir.resolve()

    if not standards.is_dir():
        print(f"Error: standards path not found: {standards}", file=sys.stderr)
        return 1

    fixtures = load_expectations(tests_dir)
    names = [args.fixture] if args.fixture else sorted(fixtures)
    failures: list[str] = []
    passed = 0

    for name in names:
        if name not in fixtures:
            failures.append(f"{name}: unknown fixture")
            continue
        spec = fixtures[name]
        print(f"\n=== Fixture: {name} ===", flush=True)
        ok, message, workdir = run_fixture(
            name,
            spec,
            standards=standards,
            tests_dir=tests_dir,
            workdir=args.workdir if args.fixture else None,
            keep_workdir=args.keep_workdir or bool(args.workdir),
            skip_assess=args.skip_assess,
            skip_rulesync=args.skip_rulesync,
        )
        if ok:
            passed += 1
            print(f"PASS {name}: {message}", flush=True)
            if args.workdir or args.keep_workdir:
                print(f"Workdir: {workdir}", flush=True)
        else:
            failures.append(f"{name}: {message}")
            print(f"FAIL {name}: {message}", flush=True)

    print(f"\nSummary: {passed} passed, {len(failures)} failed", flush=True)
    for item in failures:
        print(f"  - {item}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
