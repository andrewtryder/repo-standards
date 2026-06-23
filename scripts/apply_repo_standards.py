#!/usr/bin/env python3
"""Safely apply repo-standards to a target repository. Dry-run by default."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
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
    rules_strategy: str = "profile"
    selected_rules: list[str] = field(default_factory=list)
    existing_generated_outputs: list[str] = field(default_factory=list)
    generated_output_rewrite_allowed: bool = False
    tracked_generated_artifacts: list[str] = field(default_factory=list)
    cleanup_generated_artifacts: bool = False
    analyze_only: bool = False
    recommendations: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    rulesync_ran: bool = False
    rulesync_result: str = "skipped"
    rulesync_output: str = ""
    assessment_ran: bool = False
    assessment_result: str = "skipped"
    assessment_detail: str = ""

    def by_type(self, action_type: ActionType) -> list[Action]:
        return [a for a in self.actions if a.action == action_type]

    @property
    def apply_mode_label(self) -> str:
        if self.analyze_only:
            return "analyze-existing"
        return "apply" if self.apply_mode else "dry-run"


def selected_rule_files(
    standards: Path, profile: str, language: str, strategy: str
) -> list[Path]:
    rules_dir = standards / "ai" / "rules"

    if strategy == "all":
        return sorted(rules_dir.glob("*.md"))

    if profile == "mixed-special" or language == "mixed":
        return sorted(rules_dir.glob("*.md"))

    names = {"00-org.md"}

    if language == "typescript" or profile.startswith("typescript-"):
        names.add("10-typescript.md")

    if language == "python" or profile.startswith("python-"):
        names.add("20-python.md")

    return [rules_dir / name for name in sorted(names) if (rules_dir / name).is_file()]


def rulesync_delete_enabled(repo: Path, standards: Path) -> bool:
    for candidate in (repo / "rulesync.jsonc", standards / "templates" / "rulesync.jsonc"):
        if not candidate.is_file():
            continue
        text = read_text(candidate)
        if re.search(r'"delete"\s*:\s*true', text):
            return True
    return False


def expected_generated_agent_rules(selected_rules: list[Path]) -> set[str]:
    return {f".agents/rules/{rule.name}" for rule in selected_rules}


def expected_generated_cursor_rules(selected_rules: list[Path]) -> set[str]:
    return {f".cursor/rules/{rule.stem}.mdc" for rule in selected_rules}


def existing_generated_agent_rules(repo: Path) -> list[str]:
    rules_dir = repo / ".agents" / "rules"
    if not rules_dir.is_dir():
        return []
    return sorted(
        f".agents/rules/{path.name}"
        for path in rules_dir.glob("*.md")
        if path.is_file()
    )


def existing_generated_cursor_rules(repo: Path) -> list[str]:
    rules_dir = repo / ".cursor" / "rules"
    if not rules_dir.is_dir():
        return []
    return sorted(
        f".cursor/rules/{path.name}"
        for path in rules_dir.glob("*.mdc")
        if path.is_file()
    )


def preflight_generated_outputs(
    summary: MigrationSummary,
    repo: Path,
    standards: Path,
    selected_rules: list[Path],
    *,
    for_apply: bool,
) -> None:
    expected_agents = expected_generated_agent_rules(selected_rules)
    expected_cursor = expected_generated_cursor_rules(selected_rules)

    orphaned: list[str] = []
    for rel in existing_generated_agent_rules(repo):
        if rel not in expected_agents:
            orphaned.append(rel)
            summary.existing_generated_outputs.append(rel)
            summary.actions.append(
                Action(
                    "WARN",
                    rel,
                    "Existing generated agent rule is not represented in selected "
                    "Rulesync source and may be removed by Rulesync.",
                )
            )
            summary.recommendations.append(
                f"Review whether `{rel}` should be migrated into "
                f"`.rulesync/rules/{Path(rel).name}` before running Rulesync."
            )

    for rel in existing_generated_cursor_rules(repo):
        if rel not in expected_cursor:
            summary.existing_generated_outputs.append(rel)
            summary.actions.append(
                Action(
                    "WARN",
                    rel,
                    "Existing generated Cursor rule is not represented in selected "
                    "Rulesync source and may be removed by Rulesync.",
                )
            )

    if rulesync_delete_enabled(repo, standards):
        summary.actions.append(
            Action(
                "WARN",
                "rulesync.jsonc",
                'rulesync.jsonc has delete=true; existing generated output may be deleted.',
            )
        )

    if orphaned and not summary.generated_output_rewrite_allowed and for_apply:
        for rel in orphaned:
            summary.actions.append(
                Action(
                    "BLOCK",
                    rel,
                    "Rulesync may remove existing generated output; use "
                    "--allow-generated-output-rewrite to proceed.",
                )
            )


def tracked_coverage_artifacts(repo: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "coverage", "htmlcov", ".coverage"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def plan_coverage_cleanup(
    summary: MigrationSummary,
    repo: Path,
    cleanup: bool,
) -> None:
    tracked = tracked_coverage_artifacts(repo)
    summary.tracked_generated_artifacts = tracked
    if not tracked:
        return

    detail = ", ".join(tracked[:10])
    if len(tracked) > 10:
        detail += f" (+{len(tracked) - 10} more)"

    if cleanup:
        summary.actions.append(
            Action(
                "MERGE",
                "git index",
                f"Remove tracked generated coverage artifacts from git index: {detail}",
            )
        )
    else:
        summary.actions.append(
            Action(
                "WARN",
                "coverage artifacts",
                "Tracked generated coverage artifacts detected; use "
                "--cleanup-generated-artifacts to remove from git index.",
            )
        )


def remove_tracked_coverage_from_index(repo: Path, tracked: list[str]) -> None:
    if not tracked:
        return
    subprocess.run(
        ["git", "rm", "-r", "--cached", "--", *tracked],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


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
    selected_rules: list[Path],
    update_existing: bool,
    force: bool,
) -> None:
    if not selected_rules:
        summary.actions.append(
            Action("BLOCK", ".rulesync/rules", "No AI rules selected for profile.")
        )
        return

    for source in selected_rules:
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
    rules_strategy: str,
    update_existing: bool,
    force: bool,
    allow_generated_output_rewrite: bool,
    cleanup_generated_artifacts: bool,
    for_apply: bool,
) -> MigrationSummary:
    detection = detect_repo(repo, standards)
    selected_profile = profile or detection["recommended_profile"]
    language = detection["language"]
    selected_rules = selected_rule_files(
        standards, selected_profile, language, rules_strategy
    )

    summary = MigrationSummary(
        repo=repo,
        mode=mode,
        profile=selected_profile,
        detection=detection,
        workflow_strategy=workflow_strategy,
        apply_mode=False,
        rules_strategy=rules_strategy,
        selected_rules=[rule.name for rule in selected_rules],
        generated_output_rewrite_allowed=allow_generated_output_rewrite,
        cleanup_generated_artifacts=cleanup_generated_artifacts,
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

    plan_rulesync_rules(
        summary, standards, repo, selected_rules, update_existing, force
    )

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
    plan_coverage_cleanup(summary, repo, cleanup_generated_artifacts)
    preflight_generated_outputs(
        summary, repo, standards, selected_rules, for_apply=for_apply
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


def build_analysis(
    repo: Path,
    standards: Path,
    *,
    mode: str,
    profile: str | None,
    rules_strategy: str,
) -> MigrationSummary:
    detection = detect_repo(repo, standards)
    selected_profile = profile or detection["recommended_profile"]
    language = detection["language"]
    selected_rules = selected_rule_files(
        standards, selected_profile, language, rules_strategy
    )

    summary = MigrationSummary(
        repo=repo,
        mode=mode,
        profile=selected_profile,
        detection=detection,
        workflow_strategy="n/a",
        apply_mode=False,
        rules_strategy=rules_strategy,
        selected_rules=[rule.name for rule in selected_rules],
        analyze_only=True,
    )

    scan_protected_workflows(summary, repo)
    plan_nvmrc(summary, standards, repo, language, force=False)
    plan_coverage_cleanup(summary, repo, cleanup=False)
    preflight_generated_outputs(
        summary, repo, standards, selected_rules, for_apply=False
    )

    semantic = repo / ".github" / "workflows" / "semantic-pull-request.yml"
    template = standards / "templates" / "workflows" / "semantic-pull-request.yml"
    if semantic.is_file() and template.is_file() and not files_match(template, semantic):
        summary.actions.append(
            Action(
                "WARN",
                ".github/workflows/semantic-pull-request.yml",
                "Existing semantic PR workflow differs from template and will be skipped "
                "unless update flags are used.",
            )
        )
    elif semantic.is_file() and template.is_file() and files_match(template, semantic):
        summary.actions.append(
            Action(
                "SKIP",
                ".github/workflows/semantic-pull-request.yml",
                "Already matches standards.",
            )
        )

    if language == "typescript" or selected_profile.startswith("typescript-"):
        summary.actions.append(
            Action(
                "WARN",
                "rules",
                "TypeScript profile should copy org + TypeScript rules only.",
            )
        )

    summary.recommendations.append("Review `.repo-policy.yml` before adoption.")
    if summary.existing_generated_outputs:
        summary.recommendations.append(
            "Migrate repo-specific generated rules into `.rulesync/rules/` before Rulesync."
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
            selected = [
                standards / "ai" / "rules" / Path(action.path).name
                for name in summary.selected_rules
                if name == Path(action.path).name
            ]
            source = selected[0] if selected else standards / "ai" / "rules" / Path(action.path).name
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
        f"Rules strategy: `{summary.rules_strategy}`",
        f"Apply mode: `{summary.apply_mode_label}`",
        f"Generated-output rewrite allowed: `{summary.generated_output_rewrite_allowed}`",
        f"Cleanup generated artifacts: `{summary.cleanup_generated_artifacts}`",
        "",
        "## Detection",
        "",
        f"- Recommended profile: `{det.get('recommended_profile')}`",
        f"- Confidence: `{det.get('confidence')}`",
        "",
        "## Selected AI rules",
        "",
    ]

    if summary.selected_rules:
        lines.extend(f"- `{name}`" for name in summary.selected_rules)
    else:
        lines.append("- None")

    lines.extend(["", "## Existing generated outputs", ""])
    if summary.existing_generated_outputs:
        lines.extend(f"- `{path}`" for path in summary.existing_generated_outputs)
    else:
        lines.append("- None")

    lines.extend(["", "## Tracked generated artifacts", ""])
    if summary.tracked_generated_artifacts:
        lines.extend(f"- `{path}`" for path in summary.tracked_generated_artifacts)
    else:
        lines.append("- None")

    if summary.recommendations:
        lines.extend(["", "## Recommendations", ""])
        lines.extend(f"- {item}" for item in summary.recommendations)

    lines.extend(["", "## Actions", ""])

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
        "rules_strategy": summary.rules_strategy,
        "apply_mode": summary.apply_mode_label,
        "generated_output_rewrite_allowed": summary.generated_output_rewrite_allowed,
        "cleanup_generated_artifacts": summary.cleanup_generated_artifacts,
        "selected_rules": summary.selected_rules,
        "existing_generated_outputs": summary.existing_generated_outputs,
        "tracked_generated_artifacts": summary.tracked_generated_artifacts,
        "recommendations": summary.recommendations,
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
    parser.add_argument(
        "--rules-strategy",
        choices=("profile", "all"),
        default="profile",
        help="Which AI rules to copy (default: profile).",
    )
    parser.add_argument(
        "--analyze-existing",
        action="store_true",
        help="Analyze existing repo without planning copy operations.",
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
        "--allow-generated-output-rewrite",
        action="store_true",
        help="Allow Rulesync to rewrite or delete existing generated outputs.",
    )
    parser.add_argument(
        "--cleanup-generated-artifacts",
        action="store_true",
        help="Remove tracked coverage artifacts from the git index.",
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

    if args.analyze_existing:
        summary = build_analysis(
            repo,
            standards,
            mode=args.mode,
            profile=args.profile,
            rules_strategy=args.rules_strategy,
        )
        markdown = format_summary_markdown(summary)
        print(markdown)
        if args.json:
            print(json.dumps(summary_to_json(summary), indent=2, sort_keys=True))
        return 0

    summary = build_plan(
        repo,
        standards,
        mode=args.mode,
        profile=args.profile,
        workflow_strategy=args.workflow_strategy,
        rules_strategy=args.rules_strategy,
        update_existing=args.update_existing,
        force=args.force,
        allow_generated_output_rewrite=args.allow_generated_output_rewrite,
        cleanup_generated_artifacts=args.cleanup_generated_artifacts,
        for_apply=apply_mode,
    )
    summary.apply_mode = apply_mode

    if apply_mode:
        blocks = summary.by_type("BLOCK")
        if blocks:
            print("Error: blocked actions prevent apply.", file=sys.stderr)
            for item in blocks:
                print(f"  BLOCK {item.path}: {item.detail}", file=sys.stderr)
            return 1

        apply_actions(summary, standards, repo)

        if summary.cleanup_generated_artifacts and summary.tracked_generated_artifacts:
            remove_tracked_coverage_from_index(repo, summary.tracked_generated_artifacts)

        run_rulesync_flag = not args.skip_rulesync
        if args.run_rulesync:
            run_rulesync_flag = True

        if run_rulesync_flag:
            # Re-check blocks related to generated output rewrite before Rulesync.
            rewrite_blocks = [
                a
                for a in summary.by_type("BLOCK")
                if "generated output" in a.detail.lower()
            ]
            if rewrite_blocks and not args.allow_generated_output_rewrite:
                print("Error: Rulesync blocked by existing generated outputs.", file=sys.stderr)
                return 1

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
