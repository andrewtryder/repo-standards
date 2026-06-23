#!/usr/bin/env python3
"""Read-only adoption planner for repo-standards. Prints commands; never modifies the target repo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from detect_repo_standard import PROFILE_POLICY_TEMPLATES, detect_repo  # noqa: E402

SAFETY_NOTES = [
    "Preserve existing deploy behavior.",
    "Do not change package managers.",
    "Do not refactor application code.",
    "Do not fix unrelated lint/audit/coverage debt in the standards PR.",
    "Treat detector output as advisory; review `.repo-policy.yml` manually.",
]

CORE_COPY_COMMANDS = [
    'cp "$REPO_STANDARDS/templates/rulesync.jsonc" .',
    'mkdir -p .rulesync/rules',
    'cp "$REPO_STANDARDS/ai/rules/"*.md .rulesync/rules/',
    'cp "$REPO_STANDARDS/templates/CONTRIBUTING.md" .',
    'mkdir -p .github',
    'cp "$REPO_STANDARDS/templates/.github/PULL_REQUEST_TEMPLATE.md" .github/PULL_REQUEST_TEMPLATE.md',
    'mkdir -p .github/workflows',
    'cp "$REPO_STANDARDS/templates/workflows/semantic-pull-request.yml" .github/workflows/',
    'cp "$REPO_STANDARDS/templates/workflows/ai-rules-check.yml" .github/workflows/',
    'cp "$REPO_STANDARDS/templates/workflows/docs-check.yml" .github/workflows/',
    'cp "$REPO_STANDARDS/templates/workflows/secret-scan.yml" .github/workflows/',
    'cp "$REPO_STANDARDS/templates/dependabot.yml" .github/dependabot.yml',
]

EXISTING_ONLY_COMMANDS = [
    "# Ignore generated coverage artifacts",
    '{',
    '  echo ""',
    '  echo "# Coverage artifacts"',
    '  echo "coverage/"',
    '  echo "htmlcov/"',
    '  echo ".coverage"',
    '} >> .gitignore',
    'git rm -r --cached coverage/ 2>/dev/null || true',
]

NEW_REPO_SETUP = [
    "mkdir my-new-project",
    "cd my-new-project",
    "git init",
]

MIGRATION_BRANCH = [
    "git checkout main",
    "git pull",
    "git checkout -b chore/standards-migration",
]

RULESYNC_COMMAND = "npx rulesync generate"

ASSESS_BASELINE = """python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \\
  --repo . \\
  --standards "$REPO_STANDARDS" \\
  --base-ref main"""

ASSESS_FINAL = """python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \\
  --repo . \\
  --standards "$REPO_STANDARDS" \\
  --base-ref main \\
  --run-safe-checks"""

DETECT_COMMAND = (
    'python3 "$REPO_STANDARDS/scripts/detect_repo_standard.py" --repo . --format markdown'
)


def policy_template_for_profile(profile: str) -> str:
    return PROFILE_POLICY_TEMPLATES.get(
        profile, PROFILE_POLICY_TEMPLATES["mixed-special"]
    )


def profile_copy_command(profile: str) -> str:
    template = policy_template_for_profile(profile)
    return f'cp "$REPO_STANDARDS/{template}" .repo-policy.yml'


def node_nvmrc_command(language: str) -> str | None:
    if language == "typescript":
        return 'cp "$REPO_STANDARDS/configs/node/.nvmrc" .nvmrc'
    return None


def build_command_list(
    repo: Path, standards: Path, mode: str, result: dict[str, Any]
) -> list[str]:
    profile = result["recommended_profile"]
    language = result["language"]
    commands: list[str] = [f'export REPO_STANDARDS="{standards.resolve()}"', ""]

    if mode == "new":
        commands.extend(NEW_REPO_SETUP)
        commands.append(f'export REPO_STANDARDS="{standards.resolve()}"')
        commands.append("")
    else:
        commands.extend(MIGRATION_BRANCH)
        commands.append("")

    commands.append(DETECT_COMMAND)
    commands.append("")
    commands.append(ASSESS_BASELINE)
    commands.append("")
    commands.append(f"# Review profile `{profile}` before copying:")
    commands.append(profile_copy_command(profile))
    commands.append("")

    for cmd in CORE_COPY_COMMANDS:
        commands.append(cmd)
    commands.append("")

    nvmrc = node_nvmrc_command(language)
    if nvmrc:
        commands.append("# Node repos: pin Node.js version")
        commands.append(nvmrc)
        commands.append("")

    if mode == "existing":
        for cmd in EXISTING_ONLY_COMMANDS:
            commands.append(cmd)
        commands.append("")

    commands.append(RULESYNC_COMMAND)
    commands.append("")
    commands.append(ASSESS_FINAL)

    if mode == "existing":
        commands.append("")
        commands.append("git add .")
        commands.append('git commit -m "chore(standards): adopt repo standards"')
        commands.append("git push -u origin chore/standards-migration")

    return commands


def format_markdown(
    repo: Path, standards: Path, mode: str, result: dict[str, Any]
) -> str:
    profile = result["recommended_profile"]
    policy_template = policy_template_for_profile(profile)
    commands = build_command_list(repo, standards, mode, result)

    lines = [
        "# Repo standards adoption plan",
        "",
        f"Repo: `{repo.resolve()}`",
        f"Mode: `{mode}`",
        "",
        "## Detection summary",
        "",
        f"- Recommended profile: `{profile}`",
        f"- Language: `{result['language']}`",
        f"- Package manager: `{result['package_manager']}`",
        f"- Deployment provider: `{result['deployment_provider']}`",
        f"- Confidence: `{result['confidence']}`",
        "",
        f"Suggested policy template: `{policy_template}`",
        "",
        "## Safety notes",
        "",
    ]
    lines.extend(f"- {note}" for note in SAFETY_NOTES)

    if result.get("manual_review"):
        lines.extend(["", "## Manual review", ""])
        lines.extend(f"- {note}" for note in result["manual_review"])

    lines.extend(
        [
            "",
            "## Workflow strategy",
            "",
            "- Copied workflows: easiest for first migration PRs.",
            "- Reusable workflows: preferred long-term; see `docs/reusable-workflows.md`.",
            "",
            "## Commands",
            "",
            "```bash",
            *commands,
            "```",
            "",
            "Review copied profile and workflow commands before running.",
            "",
        ]
    )
    return "\n".join(lines)


def format_shell(
    repo: Path, standards: Path, mode: str, result: dict[str, Any]
) -> str:
    profile = result["recommended_profile"]
    policy_template = policy_template_for_profile(profile)
    commands = build_command_list(repo, standards, mode, result)

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Review before running. This script is generated as a plan.",
        "# It may need edits for your profile, commands, license, and deploy behavior.",
        "",
        f"# Repo: {repo.resolve()}",
        f"# Mode: {mode}",
        f"# Recommended profile: {profile}",
        f"# Policy template: {policy_template}",
        "",
    ]
    for note in SAFETY_NOTES:
        lines.append(f"# {note}")
    lines.append("")

    for cmd in commands:
        if cmd.startswith("#"):
            lines.append(cmd)
        elif cmd == "":
            lines.append("")
        elif "repo-policy" in cmd and cmd.startswith('cp "$REPO_STANDARDS/templates/repo-policy'):
            lines.append(f"# Review profile `{profile}` before copying:")
            lines.append(f"# {cmd}")
        else:
            lines.append(cmd)

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only adoption planner for repo-standards."
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=Path,
        help="Path to the target repository",
    )
    parser.add_argument(
        "--standards",
        required=True,
        type=Path,
        help="Path to the repo-standards repository",
    )
    parser.add_argument(
        "--mode",
        choices=("new", "existing"),
        required=True,
        help="Adoption mode: new repository or existing migration",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "shell"),
        default="markdown",
        help="Output format (default: markdown)",
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

    result = detect_repo(repo, standards)

    if args.format == "shell":
        print(format_shell(repo, standards, args.mode, result), end="")
    else:
        print(format_markdown(repo, standards, args.mode, result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
