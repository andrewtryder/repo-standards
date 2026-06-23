#!/usr/bin/env python3
"""Read-only guardrail for docs/standards vs AI rule source sync."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DOCS_OR_STANDARD_PREFIXES = (
    "README.md",
    "docs/",
    "templates/workflows/",
    "templates/repo-policy.",
    "profiles/",
    ".repo-policy.yml",
)

AI_RULE_SOURCE_PREFIXES = (
    "ai/rules/",
    ".rulesync/rules/",
    "templates/rulesync.jsonc",
    "rulesync.jsonc",
)

GENERATED_AI_OUTPUT_PREFIXES = (
    "AGENTS.md",
    ".cursor/",
    ".agents/",
)


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if prefix.endswith("/"):
            if path == prefix.rstrip("/") or path.startswith(prefix):
                return True
        elif path == prefix or path.startswith(prefix):
            return True
    return False


def classify(path: str) -> str | None:
    if matches_prefix(path, DOCS_OR_STANDARD_PREFIXES):
        return "docs"
    if matches_prefix(path, AI_RULE_SOURCE_PREFIXES):
        return "ai_rules"
    if matches_prefix(path, GENERATED_AI_OUTPUT_PREFIXES):
        return "generated"
    return None


def changed_files(repo_root: Path, base_ref: str) -> list[str]:
    for args in (
        ["diff", "--name-only", f"{base_ref}...HEAD"],
        ["diff", "--name-only", base_ref],
        ["diff", "--name-only", "--cached"],
    ):
        result = run_git(args, repo_root)
        if result.returncode == 0 and result.stdout.strip():
            paths = [
                normalize_path(line)
                for line in result.stdout.splitlines()
                if line.strip()
            ]
            return sorted(set(paths))

    result = run_git(["status", "--porcelain"], repo_root)
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(normalize_path(raw))
    return sorted(set(paths))


def filter_by_category(paths: list[str], category: str) -> list[str]:
    return sorted(path for path in paths if classify(path) == category)


def print_section(title: str, items: list[str]) -> None:
    print(title)
    if items:
        for item in items:
            print(f"- {item}")
    else:
        print("- None")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check docs/standards and AI rule source stay aligned."
    )
    parser.add_argument(
        "--base-ref",
        default="main",
        help="Git ref to compare against (default: main)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when warning conditions are present",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    paths = changed_files(repo_root, args.base_ref)
    if not paths:
        print("No changed files detected.")
        return 0

    docs_changes = filter_by_category(paths, "docs")
    ai_rule_changes = filter_by_category(paths, "ai_rules")
    generated_changes = filter_by_category(paths, "generated")

    print_section("Docs/standards changed:", docs_changes)
    print_section("AI rule source changed:", ai_rule_changes)
    print_section("Generated AI/editor output changed:", generated_changes)

    warnings: list[str] = []

    if docs_changes and not ai_rule_changes:
        warnings.append(
            "Docs or standards changed, but no AI rule source changed.\n"
            "If this PR changes how agents should behave, update ai/rules/* "
            "and regenerate Rulesync outputs.\n"
            "If this is documentation-only, explain why no AI behavior "
            "changed in the PR."
        )

    if generated_changes and not ai_rule_changes:
        warnings.append(
            "Generated AI/editor outputs changed without AI rule source changes.\n"
            "Generated outputs should be produced by Rulesync from "
            "ai/rules/* or .rulesync/rules/* — not hand-edited as source."
        )

    if warnings:
        print("Warning:")
        for warning in warnings:
            print(warning)
            print()
        if args.strict:
            return 1
        return 0

    print("No docs/AI-rule sync warnings detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
