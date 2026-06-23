#!/usr/bin/env python3
"""Safely apply repo-standards to a target repository. Dry-run by default."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from detect_repo_standard import PROFILE_POLICY_TEMPLATES, detect_repo  # noqa: E402

ActionType = Literal["CREATE", "UPDATE", "SKIP", "MERGE", "WARN", "BLOCK"]

GITIGNORE_MERGE_ENTRIES = [
    "coverage/",
    "htmlcov/",
    ".coverage",
]

COPIED_WORKFLOWS = [
    "semantic-pull-request.yml",
    "ai-rules-check.yml",
    "docs-check.yml",
    "secret-scan.yml",
]

PROTECTED_PATH_PATTERNS = [
    ".github/workflows/*deploy*.yml",
    ".github/workflows/*deploy*.yaml",
    ".github/workflows/*release*.yml",
    ".github/workflows/*release*.yaml",
    ".github/workflows/*publish*.yml",
    ".github/workflows/*publish*.yaml",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "wrangler.toml",
    "wrangler.json",
    "wrangler.jsonc",
    "railway.json",
    "cloudbuild.yaml",
    "cloudbuild.yml",
    "Dockerfile",
]

PROTECTED_PREFIXES = ("src/", "app/", "lib/")

NODE_CI_WORKFLOW = """name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  node-ci:
    uses: andrewtryder/repo-standards/.github/workflows/node-ci.reusable.yml@v1.3.0
    with:
      node_version: "24"
      install_command: "npm ci"
      format_check_command: "npm run format:check --if-present"
      lint_command: "npm run lint --if-present"
      typecheck_command: "npm run typecheck --if-present"
      test_command: "npm test --if-present"
      coverage_command: "npm run test:coverage --if-present"
      build_command: "npm run build --if-present"
"""

PYTHON_CI_WORKFLOW = """name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  python-ci:
    uses: andrewtryder/repo-standards/.github/workflows/python-ci.reusable.yml@v1.3.0
    with:
      python_version: "3.12"
      install_command: "python -m pip install -r requirements.txt -r requirements-dev.txt"
      format_check_command: "ruff format --check ."
      lint_command: "ruff check ."
      test_command: "coverage run -m pytest"
      coverage_args: "--report-only"
"""


@dataclass
class Action:
    action: ActionType
    path: str
    detail: str = ""


@dataclass
class MigrationSummary:
    repo: Path
    mode: str
    profile: str
    detection: dict[str, Any]
    workflow_strategy: str
    apply_mode: bool
    actions: list[Action] = field(default_factory=list)
    rulesync_ran: bool = False
    rulesync_result: str = "skipped"
    rulesync_output: str = ""
    assessment_ran: bool = False
    assessment_result: str = "skipped"
    assessment_detail: str = ""

    def by_type(self, action_type: ActionType) -> list[Action]:
        return [a for a in self.actions if a.action == action_type]


def policy_template_path(standards: Path, profile: str) -> Path:
    rel = PROFILE_POLICY_TEMPLATES.get(
        profile, PROFILE_POLICY_TEMPLATES["mixed-special"]
    )
    return standards / rel


def is_protected_path(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    for pattern in PROTECTED_PATH_PATTERNS:
        if fnmatch.fnmatch(normalized, pattern):
            return True
    for prefix in PROTECTED_PREFIXES:
        if normalized == prefix.rstrip("/") or normalized.startswith(prefix):
            return True
    return False


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def files_match(source: Path, target: Path) -> bool:
    if not source.is_file() or not target.is_file():
        return False
    return source.read_bytes() == target.read_bytes()


def plan_file_copy(
    summary: MigrationSummary,
    *,
    rel_path: str,
    source: Path,
    target: Path,
    update_existing: bool,
    force: bool,
    authoritative: bool = False,
) -> None:
    if is_protected_path(rel_path):
        summary.actions.append(
            Action("BLOCK", rel_path, "Protected path; will not modify.")
        )
        return

    if not source.is_file():
        summary.actions.append(
            Action("BLOCK", rel_path, f"Source missing: {source}")
        )
        return

    if not target.is_file():
        summary.actions.append(Action("CREATE", rel_path, f"From {source.name}"))
        return

    if files_match(source, target):
        summary.actions.append(Action("SKIP", rel_path, "Already matches standards."))
        return

    if authoritative:
        if force:
            summary.actions.append(
                Action("UPDATE", rel_path, "Overwrite .repo-policy.yml with --force.")
            )
        else:
            summary.actions.append(
                Action(
                    "SKIP",
                    rel_path,
                    ".repo-policy.yml is authoritative; review manually.",
                )
            )
            summary.actions.append(
                Action(
                    "WARN",
                    rel_path,
                    "Existing .repo-policy.yml preserved; use --force to overwrite.",
                )
            )
        return

    if update_existing or force:
        summary.actions.append(
            Action("UPDATE", rel_path, "Existing standards-owned file differs.")
        )
    else:
        summary.actions.append(
            Action(
                "SKIP",
                rel_path,
                "Existing file differs; use --update-existing or --force.",
            )
        )


def plan_inline_file(
    summary: MigrationSummary,
    *,
    rel_path: str,
    content: str,
    target: Path,
    update_existing: bool,
    force: bool,
) -> None:
    if is_protected_path(rel_path):
        summary.actions.append(
            Action("BLOCK", rel_path, "Protected path; will not modify.")
        )
        return

    if not target.is_file():
        summary.actions.append(Action("CREATE", rel_path, "Generated workflow."))
        return

    if target.read_text(encoding="utf-8") == content:
        summary.actions.append(Action("SKIP", rel_path, "Already matches."))
        return

    if update_existing or force:
        summary.actions.append(Action("UPDATE", rel_path, "Existing file differs."))
    else:
        summary.actions.append(
            Action(
                "SKIP",
                rel_path,
                "Existing file differs; use --update-existing or --force.",
            )
        )


def plan_gitignore_merge(summary: MigrationSummary, repo: Path) -> None:
    gitignore = repo / ".gitignore"
    existing_lines: set[str] = set()
    if gitignore.is_file():
        existing_lines = {
            line.strip()
            for line in read_text(gitignore).splitlines()
            if line.strip() and not line.strip().startswith("#")
        }

    missing = [entry for entry in GITIGNORE_MERGE_ENTRIES if entry not in existing_lines]
    if not missing:
        summary.actions.append(
            Action("SKIP", ".gitignore", "Coverage entries already present.")
        )
        return

    summary.actions.append(
        Action(
            "MERGE",
            ".gitignore",
            f"Append missing entries: {', '.join(missing)}",
        )
    )


def plan_rulesync_rules(
    summary: MigrationSummary,
    standards: Path,
    repo: Path,
    update_existing: bool,
    force: bool,
) -> None:
    rules_dir = standards / "ai" / "rules"
    if not rules_dir.is_dir():
        summary.actions.append(
            Action("BLOCK", ".rulesync/rules", "ai/rules source missing in standards.")
        )
        return

    for source in sorted(rules_dir.glob("*.md")):
        rel = f".rulesync/rules/{source.name}"
        plan_file_copy(
            summary,
            rel_path=rel,
            source=source,
            target=repo / rel,
            update_existing=update_existing,
            force=force,
        )


def plan_workflows(
    summary: MigrationSummary,
    standards: Path,
    repo: Path,
    workflow_strategy: str,
    language: str,
    update_existing: bool,
    force: bool,
) -> None:
    if workflow_strategy == "none":
        return

    for name in COPIED_WORKFLOWS:
        rel = f".github/workflows/{name}"
        plan_file_copy(
            summary,
            rel_path=rel,
            source=standards / "templates" / "workflows" / name,
            target=repo / rel,
            update_existing=update_existing,
            force=force,
        )

    if workflow_strategy != "reusable":
        return

    ci_rel = ".github/workflows/ci.yml"
    ci_target = repo / ci_rel
    ci_content = NODE_CI_WORKFLOW if language == "typescript" else PYTHON_CI_WORKFLOW
    if language not in {"typescript", "python"}:
        summary.actions.append(
            Action(
                "WARN",
                ci_rel,
                "Cannot auto-generate reusable CI for this language.",
            )
        )
        return

    plan_inline_file(
        summary,
        rel_path=ci_rel,
        content=ci_content,
        target=ci_target,
        update_existing=update_existing,
        force=force,
    )
    if ci_target.is_file() and ci_target.read_text(encoding="utf-8") != ci_content:
        for action in summary.actions:
            if action.path == ci_rel and action.action == "SKIP":
                summary.actions.append(
                    Action(
                        "WARN",
                        ci_rel,
                        "Existing ci.yml preserved; review reusable workflow migration.",
                    )
                )
                break


def plan_nvmrc(
    summary: MigrationSummary,
    standards: Path,
    repo: Path,
    language: str,
    force: bool,
) -> None:
    if language != "typescript":
        return

    rel = ".nvmrc"
    source = standards / "configs" / "node" / ".nvmrc"
    target = repo / rel
    if not target.is_file():
        plan_file_copy(
            summary,
            rel_path=rel,
            source=source,
            target=target,
            update_existing=False,
            force=force,
        )
        return

    if files_match(source, target):
        summary.actions.append(Action("SKIP", rel, "Already matches standards."))
    elif force:
        summary.actions.append(Action("UPDATE", rel, "Overwrite with --force."))
    else:
        summary.actions.append(Action("SKIP", rel, "Existing .nvmrc preserved."))


def scan_protected_workflows(summary: MigrationSummary, repo: Path) -> None:
    workflows = repo / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in sorted(workflows.iterdir()):
        if not path.is_file():
            continue
        name = path.name.lower()
        if any(token in name for token in ("deploy", "release", "publish")):
            rel = f".github/workflows/{path.name}"
            summary.actions.append(
                Action(
                    "WARN",
                    rel,
                    "Deploy/release workflow preserved; will not modify.",
                )
            )


def build_plan(
    repo: Path,
    standards: Path,
    *,
    mode: str,
    profile: str | None,
    workflow_strategy: str,
    update_existing: bool,
    force: bool,
) -> MigrationSummary:
    detection = detect_repo(repo, standards)
    selected_profile = profile or detection["recommended_profile"]
    language = detection["language"]

    summary = MigrationSummary(
        repo=repo,
        mode=mode,
        profile=selected_profile,
        detection=detection,
        workflow_strategy=workflow_strategy,
        apply_mode=False,
    )

    scan_protected_workflows(summary, repo)

    policy_source = policy_template_path(standards, selected_profile)
    plan_file_copy(
        summary,
        rel_path=".repo-policy.yml",
        source=policy_source,
        target=repo / ".repo-policy.yml",
        update_existing=force,
        force=force,
        authoritative=True,
    )

    plan_file_copy(
        summary,
        rel_path="rulesync.jsonc",
        source=standards / "templates" / "rulesync.jsonc",
        target=repo / "rulesync.jsonc",
        update_existing=update_existing,
        force=force,
    )

    plan_rulesync_rules(summary, standards, repo, update_existing, force)

    plan_file_copy(
        summary,
        rel_path="CONTRIBUTING.md",
        source=standards / "templates" / "CONTRIBUTING.md",
        target=repo / "CONTRIBUTING.md",
        update_existing=update_existing,
        force=force,
    )

    plan_file_copy(
        summary,
        rel_path=".github/PULL_REQUEST_TEMPLATE.md",
        source=standards / "templates" / ".github" / "PULL_REQUEST_TEMPLATE.md",
        target=repo / ".github" / "PULL_REQUEST_TEMPLATE.md",
        update_existing=update_existing,
        force=force,
    )

    plan_file_copy(
        summary,
        rel_path=".github/dependabot.yml",
        source=standards / "templates" / "dependabot.yml",
        target=repo / ".github" / "dependabot.yml",
        update_existing=update_existing,
        force=force,
    )

    plan_workflows(
        summary,
        standards,
        repo,
        workflow_strategy,
        language,
        update_existing,
        force,
    )

    plan_nvmrc(summary, standards, repo, language, force)
    plan_gitignore_merge(summary, repo)

    agents_dir = repo / ".agents"
    if agents_dir.is_dir():
        summary.actions.append(
            Action(
                "WARN",
                ".agents",
                "Existing .agents directory detected; Rulesync may update generated agent files.",
            )
        )

    summary.actions.append(
        Action("WARN", repo.as_posix(), "Deploy behavior preserved.")
    )
    summary.actions.append(
        Action("WARN", repo.as_posix(), "Package manager preserved.")
    )

    if mode == "new":
        summary.actions.append(
            Action("WARN", repo.as_posix(), "Review profile before first commit.")
        )

    return summary


def execute_create_or_update(
    source: Path | None,
    content: str | None,
    target: Path,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if content is not None:
        target.write_text(content, encoding="utf-8")
    elif source is not None:
        target.write_bytes(source.read_bytes())
    else:
        raise ValueError("source or content required")


def apply_actions(summary: MigrationSummary, standards: Path, repo: Path) -> None:
    policy_source = policy_template_path(standards, summary.profile)

    sources: dict[str, Path | None] = {
        ".repo-policy.yml": policy_source,
        "rulesync.jsonc": standards / "templates" / "rulesync.jsonc",
        "CONTRIBUTING.md": standards / "templates" / "CONTRIBUTING.md",
        ".github/PULL_REQUEST_TEMPLATE.md": (
            standards / "templates" / ".github" / "PULL_REQUEST_TEMPLATE.md"
        ),
        ".github/dependabot.yml": standards / "templates" / "dependabot.yml",
    }

    for name in COPIED_WORKFLOWS:
        sources[f".github/workflows/{name}"] = (
            standards / "templates" / "workflows" / name
        )

    sources[".nvmrc"] = standards / "configs" / "node" / ".nvmrc"

    ci_content: str | None = None
    if summary.workflow_strategy == "reusable":
        if summary.detection["language"] == "typescript":
            ci_content = NODE_CI_WORKFLOW
        elif summary.detection["language"] == "python":
            ci_content = PYTHON_CI_WORKFLOW

    for action in summary.actions:
        if action.action not in {"CREATE", "UPDATE", "MERGE"}:
            continue

        target = repo / action.path
        if action.action == "MERGE" and action.path == ".gitignore":
            lines: list[str] = []
            if target.is_file():
                lines = read_text(target).splitlines()
            block = ["", "# Coverage artifacts", *GITIGNORE_MERGE_ENTRIES]
            existing = {line.strip() for line in lines if line.strip()}
            append = [entry for entry in GITIGNORE_MERGE_ENTRIES if entry not in existing]
            if append:
                if lines and lines[-1].strip():
                    lines.append("")
                lines.extend(["# Coverage artifacts", *append])
                target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            continue

        if action.path.startswith(".rulesync/rules/"):
            source = standards / "ai" / "rules" / Path(action.path).name
            execute_create_or_update(source, None, target)
            continue

        if action.path == ".github/workflows/ci.yml" and ci_content is not None:
            execute_create_or_update(None, ci_content, target)
            continue

        source = sources.get(action.path)
        if source is not None:
            execute_create_or_update(source, None, target)


def run_rulesync(repo: Path) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["npx", "rulesync", "generate"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, str(exc)

    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    ).strip()
    return completed.returncode == 0, output


def check_rulesync_outputs(summary: MigrationSummary, repo: Path) -> None:
    expected = [repo / "AGENTS.md", repo / ".cursor" / "rules"]
    missing = [path.relative_to(repo).as_posix() for path in expected if not path.exists()]
    if missing:
        summary.actions.append(
            Action(
                "WARN",
                "rulesync outputs",
                f"Expected outputs missing after Rulesync: {', '.join(missing)}",
            )
        )


def run_assessment(
    repo: Path, standards: Path
) -> tuple[int, str]:
    script = standards / "scripts" / "assess_repo_standards.py"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo",
                str(repo),
                "--standards",
                str(standards),
                "--base-ref",
                "main",
                "--run-safe-checks",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return 1, str(exc)

    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    ).strip()
    return completed.returncode, output


def format_summary_markdown(summary: MigrationSummary) -> str:
    det = summary.detection
    lines = [
        "# Repo standards migration summary",
        "",
        f"Repo: `{summary.repo}`",
        f"Mode: `{summary.mode}`",
        f"Profile: `{summary.profile}`",
        f"Language: `{det.get('language')}`",
        f"Package manager: `{det.get('package_manager')}`",
        f"Deployment provider: `{det.get('deployment_provider')}`",
        f"Workflow strategy: `{summary.workflow_strategy}`",
        f"Apply mode: `{summary.apply_mode}`",
        "",
        "## Detection",
        "",
        f"- Recommended profile: `{det.get('recommended_profile')}`",
        f"- Confidence: `{det.get('confidence')}`",
        "",
        "## Actions",
        "",
    ]

    for action_type in ("CREATE", "UPDATE", "SKIP", "MERGE", "WARN", "BLOCK"):
        items = summary.by_type(action_type)
        lines.append(f"### {action_type}")
        lines.append("")
        if items:
            for item in items:
                detail = f" — {item.detail}" if item.detail else ""
                lines.append(f"- `{item.path}`{detail}")
        else:
            lines.append("- None")
        lines.append("")

    lines.extend(
        [
            "## Rulesync",
            "",
            f"- Ran: `{summary.rulesync_ran}`",
            f"- Result: `{summary.rulesync_result}`",
            "",
            "## Assessment",
            "",
            f"- Ran: `{summary.assessment_ran}`",
            f"- Result: `{summary.assessment_result}`",
            "",
            "## Safety notes",
            "",
            "- Deploy behavior preserved",
            "- Package manager preserved",
            "- Application source untouched",
            "",
            "## Next steps",
            "",
            "- Review `.repo-policy.yml`",
            "- Review generated AI/editor outputs",
            "- Run final assessment",
            "- Open PR",
            "",
        ]
    )

    if summary.rulesync_output:
        lines.extend(["## Rulesync output", "", "```text", summary.rulesync_output, "```", ""])

    if summary.assessment_detail:
        lines.extend(
            ["## Assessment output", "", "```text", summary.assessment_detail, "```", ""]
        )

    return "\n".join(lines)


def summary_to_json(summary: MigrationSummary) -> dict[str, Any]:
    return {
        "repo": str(summary.repo),
        "mode": summary.mode,
        "profile": summary.profile,
        "language": summary.detection.get("language"),
        "package_manager": summary.detection.get("package_manager"),
        "deployment_provider": summary.detection.get("deployment_provider"),
        "workflow_strategy": summary.workflow_strategy,
        "apply_mode": summary.apply_mode,
        "detection": summary.detection,
        "actions": [
            {"action": a.action, "path": a.path, "detail": a.detail}
            for a in summary.actions
        ],
        "rulesync": {
            "ran": summary.rulesync_ran,
            "result": summary.rulesync_result,
            "output": summary.rulesync_output,
        },
        "assessment": {
            "ran": summary.assessment_ran,
            "result": summary.assessment_result,
            "detail": summary.assessment_detail,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely apply repo-standards to a target repository."
    )
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--standards", required=True, type=Path)
    parser.add_argument(
        "--mode",
        choices=("new", "existing"),
        default="existing",
    )
    parser.add_argument("--profile", default=None)
    parser.add_argument(
        "--workflow-strategy",
        choices=("copied", "reusable", "none"),
        default="copied",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print actions only.")
    mode.add_argument("--apply", action="store_true", help="Write safe changes.")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update differing standards-owned files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite standards-owned files, including .repo-policy.yml.",
    )
    parser.add_argument(
        "--run-rulesync",
        action="store_true",
        help="Run Rulesync after applying (default with --apply).",
    )
    parser.add_argument(
        "--skip-rulesync",
        action="store_true",
        help="Do not run Rulesync.",
    )
    parser.add_argument(
        "--run-assessment",
        action="store_true",
        help="Run assess_repo_standards.py after applying.",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        default=None,
        help="Migration summary path (default: .repo-standards-migration-summary.md).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    standards = args.standards.resolve()

    if not repo.is_dir():
        print(f"Error: --repo must be an existing directory: {repo}", file=sys.stderr)
        return 1
    if not standards.is_dir():
        print(
            f"Error: --standards must be an existing directory: {standards}",
            file=sys.stderr,
        )
        return 1

    apply_mode = args.apply
    summary = build_plan(
        repo,
        standards,
        mode=args.mode,
        profile=args.profile,
        workflow_strategy=args.workflow_strategy,
        update_existing=args.update_existing,
        force=args.force,
    )
    summary.apply_mode = apply_mode

    if apply_mode:
        if summary.by_type("BLOCK"):
            print("Error: blocked actions prevent apply.", file=sys.stderr)
            for item in summary.by_type("BLOCK"):
                print(f"  BLOCK {item.path}: {item.detail}", file=sys.stderr)
            return 1

        apply_actions(summary, standards, repo)

        run_rulesync_flag = not args.skip_rulesync
        if args.run_rulesync:
            run_rulesync_flag = True

        if run_rulesync_flag:
            summary.rulesync_ran = True
            ok, output = run_rulesync(repo)
            summary.rulesync_output = output
            if ok:
                summary.rulesync_result = "passed"
                check_rulesync_outputs(summary, repo)
            else:
                summary.rulesync_result = "failed"
                summary.actions.append(
                    Action("BLOCK", "rulesync", "Rulesync failed.")
                )
                print("Error: Rulesync failed.", file=sys.stderr)
                if output:
                    print(output, file=sys.stderr)
        else:
            summary.rulesync_result = "skipped"

        if args.run_assessment:
            summary.assessment_ran = True
            code, output = run_assessment(repo, standards)
            summary.assessment_detail = output
            summary.assessment_result = "passed" if code == 0 else f"exit {code}"

        summary_path = args.summary_file or (
            repo / ".repo-standards-migration-summary.md"
        )
        summary_path.write_text(format_summary_markdown(summary), encoding="utf-8")
    else:
        summary.rulesync_result = "skipped (dry-run)"
        summary.assessment_result = "skipped (dry-run)"

    markdown = format_summary_markdown(summary)
    print(markdown)

    if args.json:
        print(json.dumps(summary_to_json(summary), indent=2, sort_keys=True))

    if summary.by_type("BLOCK") and not apply_mode:
        return 0

    if apply_mode and summary.rulesync_result == "failed":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
