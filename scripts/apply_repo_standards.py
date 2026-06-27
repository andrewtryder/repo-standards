#!/usr/bin/env python3
"""Safely apply repo-standards to a target repository. Dry-run by default."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from detect_repo_standard import (  # noqa: E402
    PROFILE_POLICY_TEMPLATES,
    detect_repo,
    recommended_templates,
)

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

def yaml_string(value: str) -> str:
    return json.dumps(value)


def render_node_ci_workflow(commands: dict[str, str]) -> str:
    values = {
        "install_command": commands.get("install", "npm ci"),
        "format_check_command": commands.get(
            "format_check",
            "npm run format:check --if-present",
        ),
        "lint_command": commands.get("lint", "npm run lint --if-present"),
        "typecheck_command": commands.get(
            "typecheck",
            "npm run typecheck --if-present",
        ),
        "test_command": commands.get("test", "npm test --if-present"),
        "coverage_command": commands.get(
            "coverage",
            "npm run test:coverage --if-present",
        ),
        "build_command": commands.get("build", "npm run build --if-present"),
    }
    rendered = "\n".join(
        f"      {key}: {yaml_string(value)}" for key, value in values.items()
    )
    return f"""name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  node-ci:
    uses: andrewtryder/repo-standards/.github/workflows/node-ci.reusable.yml@v1.0.0
    with:
      node_version: "24"
{rendered}
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
    uses: andrewtryder/repo-standards/.github/workflows/python-ci.reusable.yml@v1.0.0
    with:
      python_version: "3.12"
      install_command: "python -m pip install -r requirements.txt -r requirements-dev.txt"
      format_check_command: "ruff format --check ."
      lint_command: "ruff check ."
      test_command: "coverage run -m pytest"
      coverage_args: ""
"""

PYTHON_HOME_ASSISTANT_CI_WORKFLOW = """name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  python-ci:
    uses: andrewtryder/repo-standards/.github/workflows/python-ci.reusable.yml@v1.0.0
    with:
      python_version: "3.12"
      install_command: "python -m pip install -r requirements.txt -r requirements_test.txt"
      format_check_command: "ruff format --check ."
      lint_command: "ruff check ."
      test_command: "coverage run -m pytest"
      coverage_args: ""
"""


def reusable_ci_workflow_for(repo: Path, detection: dict[str, Any]) -> str | None:
    """Return the reusable CI caller content for supported detected languages."""
    language = detection.get("language")
    if language == "typescript":
        return render_node_ci_workflow(infer_commands(repo, detection))
    if language == "python":
        if (
            detection.get("recommended_profile") == "python-home-assistant"
            and (repo / "requirements_test.txt").is_file()
        ):
            return PYTHON_HOME_ASSISTANT_CI_WORKFLOW
        return PYTHON_CI_WORKFLOW
    return None

STANDARDS_OWNED_WORKFLOW_NAMES = {
    "semantic-pull-request.yml",
    "ai-rules-check.yml",
    "docs-check.yml",
    "secret-scan.yml",
}

PROTECTED_WORKFLOW_TERMS = [
    "deploy",
    "release",
    "publish",
    "npm publish",
    "pnpm publish",
    "yarn npm publish",
    "release-please",
    "pages",
    "github-pages",
    "configure-pages",
    "upload-pages-artifact",
    "deploy-pages",
    "wrangler deploy",
    "cloudflare",
    "gcloud",
    "google-github-actions",
    "cloud run",
    "cloud functions",
    "artifact registry",
    "railway",
    "firebase",
    "flyctl",
    "docker push",
    "ghcr.io",
]

CHECK_WORKFLOW_TERMS = [
    "npm ci",
    "npm install",
    "pnpm install",
    "yarn install",
    "bun install",
    "pip install",
    "uv sync",
    "poetry install",
    "lint",
    "eslint",
    "ruff",
    "flake8",
    "pylint",
    "typecheck",
    "tsc --noemit",
    "mypy",
    "pyright",
    "test",
    "pytest",
    "vitest",
    "jest",
    "mocha",
    "coverage",
    "build",
    "prettier",
    "format",
]

AI_API_URL = "https://models.github.ai/inference/chat/completions"
DEFAULT_AI_MODEL = "openai/gpt-4o-mini"

RULESYNC_MIGRATION_FRONTMATTER = """---
targets: ["*"]
description: "Migrated generated agent rule for this repository"
globs: ["*"]
---

"""

OPEN_SOURCE_LICENSES = {
    "mit",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "mpl-2.0",
    "gpl-3.0",
    "lgpl-3.0",
    "agpl-3.0",
    "isc",
}

CLOSED_LICENSES = {"proprietary", "none", "unlicensed"}

SUPPORTED_LICENSE_TEMPLATES = {"mit": "LICENSE"}

LICENSE_CANONICAL = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "mpl-2.0": "MPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "lgpl-3.0": "LGPL-3.0",
    "agpl-3.0": "AGPL-3.0",
    "isc": "ISC",
    "proprietary": "proprietary",
    "none": "none",
}

FORMAT_TOUCHED_CANDIDATES = {
    "rulesync.jsonc",
    ".repo-policy.yml",
    "AGENTS.md",
    "CONTRIBUTING.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".editorconfig",
}

FORMAT_EXISTING_DOC_CANDIDATES = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
)

PRIMARY_ACTION_TYPES = frozenset({"CREATE", "UPDATE", "MERGE", "BLOCK"})


def has_primary_action(summary: "MigrationSummary", path: str) -> bool:
    return any(
        action.path == path and action.action in PRIMARY_ACTION_TYPES
        for action in summary.actions
    )


def add_action(summary: "MigrationSummary", action: Action) -> None:
    if action.action in PRIMARY_ACTION_TYPES:
        summary.actions = [
            existing
            for existing in summary.actions
            if not (
                existing.path == action.path
                and existing.action in {"SKIP", "WARN"}
            )
        ]
    elif action.action == "SKIP" and has_primary_action(summary, action.path):
        return
    summary.actions.append(action)


def is_home_assistant_repo(repo: Path) -> bool:
    return any(path.is_file() for path in repo.glob("custom_components/*/manifest.json"))


def has_firebase_repo(repo: Path, detection: dict[str, Any]) -> bool:
    if detection.get("deployment_provider") == "firebase":
        return True
    if (repo / "firebase.json").is_file() or (repo / ".firebaserc").is_file():
        return True
    workflows = repo / ".github" / "workflows"
    if not workflows.is_dir():
        return False
    for path in list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml")):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if "firebase" in text:
            return True
    return False


def normalize_detection(repo: Path, detection: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(detection)
    if is_home_assistant_repo(repo):
        normalized["recommended_profile"] = "python-home-assistant"
        normalized["recommended_templates"] = recommended_templates("python-home-assistant")
    if has_firebase_repo(repo, normalized):
        normalized["deployment_provider"] = "firebase"
    return normalized


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
    adoption_level: str = "baseline"
    interactive: bool = False
    replace_check_workflows: bool = False
    migrate_existing_agent_rules: bool = False
    workflow_classifications: list[dict[str, Any]] = field(default_factory=list)
    migrated_agent_rule_targets: list[str] = field(default_factory=list)
    confirmed_decisions: list[str] = field(default_factory=list)
    ai_assessment: dict[str, Any] | None = None
    ai_assessment_result: str = "skipped"
    commit_requested: bool = False
    rendered_repo_policy: str | None = None
    will_run_rulesync: bool = True
    install_rulesync: bool = False
    rulesync_install_result: str = "skipped"
    rulesync_install_output: str = ""
    recommendations: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    rulesync_ran: bool = False
    rulesync_result: str = "skipped"
    rulesync_output: str = ""
    assessment_ran: bool = False
    assessment_result: str = "skipped"
    assessment_detail: str = ""
    policy_visibility: str = ""
    policy_license: str = ""
    visibility_source: str = ""
    license_source: str = ""
    format_touched: bool = False
    format_existing_docs: bool = False
    formatting_result: str = "skipped"
    touched_paths: list[str] = field(default_factory=list)
    add_license: bool = False

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


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env_files(standards_root: Path, repo: Path) -> None:
    for env_path in (standards_root / ".env", Path.cwd() / ".env", repo / ".env"):
        load_dotenv(env_path)


def get_github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def confirm(prompt: str, default: bool = False) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    try:
        answer = input(f"{prompt}{suffix}: ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def effective_workflow_strategy(adoption_level: str, workflow_strategy: str) -> str:
    if adoption_level == "reusable-ci":
        return "reusable"
    return workflow_strategy


def classify_workflow(path: Path, repo: Path) -> dict[str, Any]:
    rel = path.relative_to(repo).as_posix()
    content = read_text(path).lower() if path.is_file() else ""
    matched_protected = [t for t in PROTECTED_WORKFLOW_TERMS if t in content]
    matched_check = [t for t in CHECK_WORKFLOW_TERMS if t in content]
    name = path.name.lower()

    if path.name in STANDARDS_OWNED_WORKFLOW_NAMES:
        return {
            "path": rel,
            "classification": "standards-owned",
            "reason": "Known repo-standards check workflow.",
            "matched_terms": [],
        }

    if any(token in name for token in ("deploy", "release", "publish", "pages")):
        classification = "protected-deploy"
        if "release" in name or "release-please" in content:
            classification = "protected-release"
        elif "publish" in name:
            classification = "protected-publish"
        elif "pages" in name:
            classification = "protected-pages"
        return {
            "path": rel,
            "classification": classification,
            "reason": "Filename indicates operational workflow.",
            "matched_terms": matched_protected,
        }

    if matched_protected and matched_check:
        return {
            "path": rel,
            "classification": "mixed-operational",
            "reason": "Workflow combines checks with deploy/release/publish behavior; preserve and review manually.",
            "matched_terms": matched_protected + matched_check,
        }

    if matched_protected:
        classification = "protected-provider"
        if any(t in content for t in ("wrangler", "cloudflare")):
            classification = "protected-provider"
        return {
            "path": rel,
            "classification": classification,
            "reason": "Workflow contains protected operational signals.",
            "matched_terms": matched_protected,
        }

    if matched_check:
        return {
            "path": rel,
            "classification": "replaceable-check",
            "reason": "Workflow appears to run install/lint/typecheck/test/build only.",
            "matched_terms": matched_check,
        }

    return {
        "path": rel,
        "classification": "unknown",
        "reason": "Could not confidently classify workflow.",
        "matched_terms": [],
    }


def classify_all_workflows(repo: Path) -> list[dict[str, Any]]:
    workflows = repo / ".github" / "workflows"
    if not workflows.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for path in sorted(workflows.iterdir()):
        if path.suffix.lower() in {".yml", ".yaml"} and path.is_file():
            results.append(classify_workflow(path, repo))
    return results


def load_package_scripts(repo: Path) -> dict[str, str]:
    pkg_path = repo / "package.json"
    if not pkg_path.is_file():
        return {}
    try:
        data = json.loads(read_text(pkg_path))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def load_package_data(repo: Path) -> dict[str, Any]:
    pkg_path = repo / "package.json"
    if not pkg_path.is_file():
        return {}
    try:
        data = json.loads(read_text(pkg_path))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def has_package_dependency(repo: Path, name: str) -> bool:
    package = load_package_data(repo)
    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        deps = package.get(section, {})
        if isinstance(deps, dict) and name in deps:
            return True
    return False


def package_manager_for_repo(repo: Path, detection: dict[str, Any]) -> str:
    package_manager = detection.get("package_manager")
    if package_manager == "pnpm" or (repo / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if package_manager == "yarn" or (repo / "yarn.lock").is_file():
        return "yarn"
    if (
        package_manager == "bun"
        or (repo / "bun.lock").is_file()
        or (repo / "bun.lockb").is_file()
    ):
        return "bun"
    return "npm"


def rulesync_install_command(repo: Path, detection: dict[str, Any]) -> list[str] | None:
    if not (repo / "package.json").is_file():
        return None
    package_manager = package_manager_for_repo(repo, detection)
    if package_manager == "pnpm":
        return ["pnpm", "add", "-D", "rulesync"]
    if package_manager == "yarn":
        return ["yarn", "add", "-D", "rulesync"]
    if package_manager == "bun":
        return ["bun", "add", "-d", "rulesync"]
    return ["npm", "install", "-D", "rulesync"]


def rulesync_install_command_text(repo: Path, detection: dict[str, Any]) -> str | None:
    command = rulesync_install_command(repo, detection)
    return " ".join(command) if command else None


def infer_commands(repo: Path, detection: dict[str, Any]) -> dict[str, str]:
    commands: dict[str, str] = {}
    language = detection.get("language")
    package_manager = detection.get("package_manager")

    if language == "typescript" or package_manager in {"npm", "pnpm", "yarn", "bun"}:
        scripts = load_package_scripts(repo)
        if package_manager == "pnpm" or (repo / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif package_manager == "yarn" or (repo / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (
            package_manager == "bun"
            or (repo / "bun.lock").is_file()
            or (repo / "bun.lockb").is_file()
        ):
            package_manager = "bun"
        elif (repo / "package-lock.json").is_file():
            package_manager = "npm"
        else:
            package_manager = "npm"

        if package_manager == "npm" and (repo / "package-lock.json").is_file():
            commands["install"] = "npm ci"
        elif package_manager == "pnpm":
            commands["install"] = "pnpm install --frozen-lockfile"
        elif package_manager == "yarn":
            commands["install"] = "yarn install --frozen-lockfile"
        elif package_manager == "bun":
            commands["install"] = "bun install --frozen-lockfile"
        else:
            commands["install"] = "npm install"

        run_prefix = {
            "npm": "npm run",
            "pnpm": "pnpm run",
            "yarn": "yarn run",
            "bun": "bun run",
        }.get(package_manager, "npm run")
        absent_fallback = {
            "npm": "npm run {script} --if-present",
            "pnpm": "pnpm run {script} --if-present",
            "yarn": ":",
            "bun": ":",
        }.get(package_manager, "npm run {script} --if-present")

        script_map = {
            "format_check": "format:check",
            "lint": "lint",
            "typecheck": "typecheck",
            "coverage": "test:coverage",
            "build": "build",
        }
        for cmd_key, script_name in script_map.items():
            if script_name in scripts:
                commands[cmd_key] = f"{run_prefix} {script_name}"
            else:
                commands[cmd_key] = absent_fallback.format(script=script_name)
        if "test" in scripts:
            if package_manager == "npm":
                commands["test"] = "npm test"
            else:
                commands["test"] = f"{run_prefix} test"
        elif package_manager in {"npm", "pnpm"}:
            commands["test"] = f"{package_manager} test --if-present"
        else:
            commands["test"] = ":"
    elif language == "python":
        commands["install"] = "python -m pip install -r requirements.txt -r requirements-dev.txt"
        commands["format_check"] = "ruff format --check ."
        commands["lint"] = "ruff check ."
        commands["test"] = "coverage run -m pytest"
        commands["coverage"] = "coverage report"

    return commands


@dataclass
class PolicyFields:
    visibility: str
    license: str
    visibility_source: str
    license_source: str


def canonical_license(value: str) -> str:
    normalized = value.strip().lower()
    return LICENSE_CANONICAL.get(normalized, value.strip())


def parse_existing_policy(repo: Path) -> tuple[str | None, str | None]:
    policy = repo / ".repo-policy.yml"
    if not policy.is_file():
        return None, None
    text = read_text(policy)
    visibility = None
    license_value = None
    vis_match = re.search(r'(?m)^visibility:\s*["\']?([^"\'\n#]+)', text)
    if vis_match:
        visibility = vis_match.group(1).strip().lower()
    lic_match = re.search(r'(?m)^license:\s*["\']?([^"\'\n#]+)', text)
    if lic_match:
        license_value = canonical_license(lic_match.group(1))
    return visibility, license_value


def parse_github_remote_slug(repo: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    url = completed.stdout.strip()
    if not url:
        return None
    patterns = [
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)",
        r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def infer_github_visibility(repo: Path) -> tuple[str | None, str]:
    slug = parse_github_remote_slug(repo)
    if not slug:
        return None, "unavailable"
    for json_fields in ("isPrivate", "visibility"):
        try:
            completed = subprocess.run(
                ["gh", "repo", "view", slug, "--json", json_fields],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None, "unavailable"
        if completed.returncode != 0:
            continue
        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError:
            continue
        if json_fields == "isPrivate":
            if data.get("isPrivate") is True:
                return "private", "github"
            if data.get("isPrivate") is False:
                return "public", "github"
        else:
            visibility = str(data.get("visibility", "")).lower()
            if visibility in {"private", "public", "internal"}:
                return "private" if visibility != "public" else "public", "github"
    return None, "unavailable"


def resolve_policy_fields(
    repo: Path,
    mode: str,
    cli_visibility: str | None,
    cli_license: str | None,
) -> PolicyFields:
    existing_visibility, existing_license = parse_existing_policy(repo)

    if cli_visibility:
        visibility = cli_visibility.lower()
        visibility_source = "cli"
    elif existing_visibility:
        visibility = existing_visibility
        visibility_source = "existing-policy"
    else:
        inferred, _source = infer_github_visibility(repo)
        if inferred:
            visibility = inferred
            visibility_source = "github"
        elif mode == "existing":
            visibility = "private"
            visibility_source = "default"
        else:
            visibility = "public"
            visibility_source = "default"

    if cli_license:
        license_value = canonical_license(cli_license)
        license_source = "cli"
    elif existing_license and not cli_license:
        license_value = existing_license
        license_source = "existing-policy"
    elif visibility_source == "github":
        license_value = "proprietary" if visibility == "private" else "MIT"
        license_source = "github"
    elif mode == "existing":
        license_value = "proprietary"
        license_source = "default"
    else:
        license_value = "MIT"
        license_source = "default"

    return PolicyFields(
        visibility=visibility,
        license=license_value,
        visibility_source=visibility_source,
        license_source=license_source,
    )


def parse_policy_from_text(text: str) -> tuple[str | None, str | None]:
    visibility = None
    license_value = None
    vis_match = re.search(r'(?m)^visibility:\s*["\']?([^"\'\n#]+)', text)
    if vis_match:
        visibility = vis_match.group(1).strip().lower()
    lic_match = re.search(r'(?m)^license:\s*["\']?([^"\'\n#]+)', text)
    if lic_match:
        license_value = canonical_license(lic_match.group(1))
    return visibility, license_value


def license_warning_needed(
    visibility: str | None, license_value: str | None, has_license_file: bool
) -> tuple[bool, str]:
    if has_license_file or not license_value:
        return False, ""
    lic = license_value.strip().lower()
    vis = (visibility or "private").strip().lower()
    if lic in CLOSED_LICENSES:
        if vis == "public":
            return True, (
                ".repo-policy.yml declares a public repository with a closed license "
                f"({license_value}); review visibility and license before merge."
            )
        return False, ""
    if lic in OPEN_SOURCE_LICENSES:
        if vis == "private":
            return True, (
                f".repo-policy.yml declares license {license_value} but LICENSE/LICENSE.md "
                "is missing. Add a license intentionally or adjust .repo-policy.yml."
            )
        return True, (
            f".repo-policy.yml declares license {license_value} but LICENSE/LICENSE.md "
            "is missing. Add a license intentionally or adjust .repo-policy.yml."
        )
    return False, ""


def render_repo_policy_template(
    template_text: str,
    repo: Path,
    detection: dict[str, Any],
    policy_fields: PolicyFields,
) -> str:
    text = template_text
    repo_name = repo.name
    profile = detection.get("recommended_profile", "mixed-special")
    package_manager = detection.get("package_manager", "unknown")
    deploy_provider = detection.get("deployment_provider", "none")

    text = re.sub(r"^name: .*$", f"name: {repo_name}", text, count=1, flags=re.MULTILINE)
    text = re.sub(
        r"^profile: .*$", f"profile: {profile}", text, count=1, flags=re.MULTILINE
    )
    text = re.sub(
        r"^visibility: .*$",
        f"visibility: {policy_fields.visibility}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^license: .*$",
        f"license: {policy_fields.license}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if package_manager != "unknown":
        text = re.sub(
            r"^package_manager: .*$",
            f"package_manager: {package_manager}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    if deploy_provider not in {"none", "unknown"}:
        text = re.sub(
            r"^  provider: .*$",
            f"  provider: {deploy_provider}",
            text,
            count=1,
            flags=re.MULTILINE,
        )

    commands = infer_commands(repo, detection)
    for key, value in commands.items():
        text = re.sub(
            rf"^  {key}: .*$",
            f"  {key}: {value}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def agent_rule_to_rulesync_name(path: Path) -> str:
    name = path.name
    if re.match(r"^\d{2}-", name):
        return name
    if name == "conventional-commits.md":
        return "05-conventional-commits.md"
    return f"05-{name}"


def plan_agent_rule_migration(
    summary: MigrationSummary,
    repo: Path,
    selected_rules: list[Path],
    migrate: bool,
) -> None:
    if not migrate:
        return

    expected_sources = {rule.name for rule in selected_rules}
    agents_rules = repo / ".agents" / "rules"
    if not agents_rules.is_dir():
        return

    for agent_file in sorted(agents_rules.glob("*.md")):
        generated_name = agent_file.name
        expected_agent = f".agents/rules/{generated_name}"
        if expected_agent in expected_generated_agent_rules(selected_rules):
            continue

        target_name = agent_rule_to_rulesync_name(agent_file)
        if target_name in expected_sources:
            continue

        rel = f".rulesync/rules/{target_name}"
        target = repo / rel
        if target.is_file():
            add_action(summary, Action("SKIP", rel, "Rulesync source already exists."))
        else:
            add_action(
                summary,
                Action(
                    "CREATE",
                    rel,
                    f"Migrate generated agent rule from {expected_agent}.",
                ),
            )
        summary.migrated_agent_rule_targets.append(target_name)
        summary.selected_rules.append(target_name)


def apply_agent_rule_migration(summary: MigrationSummary, repo: Path) -> None:
    agents_rules = repo / ".agents" / "rules"
    rules_dir = repo / ".rulesync" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    for target_name in summary.migrated_agent_rule_targets:
        source_agent = None
        for agent_file in agents_rules.glob("*.md"):
            if agent_rule_to_rulesync_name(agent_file) == target_name:
                source_agent = agent_file
                break
        if source_agent is None:
            continue
        body = read_text(source_agent).strip()
        if body.startswith("---"):
            parts = body.split("\n---\n", 1)
            if len(parts) == 2:
                body = parts[1].strip()
        content = RULESYNC_MIGRATION_FRONTMATTER + body + "\n"
        (rules_dir / target_name).write_text(content, encoding="utf-8")


def plan_check_workflow_replacement(
    summary: MigrationSummary,
    repo: Path,
    adoption_level: str,
    replace_check_workflows: bool,
    workflow_strategy: str,
    language: str,
    update_existing: bool,
    force: bool,
) -> None:
    if adoption_level not in {"checks", "full"}:
        return

    for wf in summary.workflow_classifications:
        if wf["classification"] != "replaceable-check":
            continue
        rel = wf["path"]
        target_rel = rel if rel.endswith("ci.yml") else ".github/workflows/ci.yml"
        if has_primary_action(summary, target_rel):
            continue
        if replace_check_workflows:
            ci_content = reusable_ci_workflow_for(repo, summary.detection)
            if ci_content is None:
                continue
            plan_inline_file(
                summary,
                rel_path=target_rel,
                content=ci_content,
                target=repo / target_rel,
                update_existing=update_existing or replace_check_workflows,
                force=force,
            )
        else:
            add_action(
                summary,
                Action(
                    "SKIP",
                    rel,
                    "Existing check-only workflow may be replaced after review.",
                ),
            )
            add_action(
                summary,
                Action(
                    "WARN",
                    rel,
                    "Existing check-only workflow may be replaced after review.",
                ),
            )


def build_ai_safe_summary(summary: MigrationSummary, repo: Path) -> dict[str, Any]:
    scripts = load_package_scripts(repo)
    return {
        "detection": {
            "language": summary.detection.get("language"),
            "package_manager": summary.detection.get("package_manager"),
            "deployment_provider": summary.detection.get("deployment_provider"),
            "recommended_profile": summary.detection.get("recommended_profile"),
            "confidence": summary.detection.get("confidence"),
        },
        "adoption_level": summary.adoption_level,
        "workflow_classifications": summary.workflow_classifications,
        "package_script_names": sorted(scripts.keys()),
        "package_commands": infer_commands(repo, summary.detection),
        "existing_generated_outputs": summary.existing_generated_outputs,
        "tracked_generated_artifacts": summary.tracked_generated_artifacts[:30],
        "selected_rules": summary.selected_rules,
        "planned_actions": [
            {"action": a.action, "path": a.path, "detail": a.detail}
            for a in summary.actions
            if a.action in {"CREATE", "UPDATE", "MERGE", "WARN", "BLOCK"}
        ][:50],
    }


def call_migration_ai_assessment(
    standards: Path,
    safe_summary: dict[str, Any],
    model: str,
    timeout: float = 30.0,
) -> tuple[dict[str, Any] | None, str]:
    token = get_github_token()
    if not token:
        return None, "no token"

    prompt_path = standards / "prompts" / "migration-assessment-advisor.prompt.md"
    if not prompt_path.is_file():
        return None, "prompt missing"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": read_text(prompt_path)},
            {
                "role": "user",
                "content": json.dumps(safe_summary, indent=2, sort_keys=True),
            },
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        AI_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        return json.loads(content), "passed"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as exc:
        return None, f"failed: {exc}"


def plan_repo_policy(
    summary: MigrationSummary,
    standards: Path,
    repo: Path,
    detection: dict[str, Any],
    selected_profile: str,
    force: bool,
    policy_fields: PolicyFields,
) -> None:
    rel = ".repo-policy.yml"
    policy_source = policy_template_path(standards, selected_profile)
    target = repo / rel
    template_text = read_text(policy_source)
    det = {**detection, "recommended_profile": selected_profile, "profile": selected_profile}
    rendered = render_repo_policy_template(template_text, repo, det, policy_fields)
    summary.rendered_repo_policy = rendered
    summary.policy_visibility = policy_fields.visibility
    summary.policy_license = policy_fields.license
    summary.visibility_source = policy_fields.visibility_source
    summary.license_source = policy_fields.license_source

    if not target.is_file():
        add_action(
            summary,
            Action("CREATE", rel, f"From {policy_source.name} with repo-specific values."),
        )
        return

    if target.read_text(encoding="utf-8") == rendered:
        add_action(summary, Action("SKIP", rel, "Already matches rendered policy."))
        return

    if force:
        add_action(summary, Action("UPDATE", rel, "Overwrite .repo-policy.yml with --force."))
    else:
        add_action(
            summary,
            Action("SKIP", rel, ".repo-policy.yml is authoritative; review manually."),
        )
        add_action(
            summary,
            Action("WARN", rel, "Existing .repo-policy.yml preserved; use --force to overwrite."),
        )


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


def rulesync_source_rule_names(repo: Path, selected_rules: list[Path]) -> set[str]:
    names = {rule.name for rule in selected_rules}
    rules_dir = repo / ".rulesync" / "rules"
    if rules_dir.is_dir():
        names.update(path.name for path in rules_dir.glob("*.md") if path.is_file())
    return names


def agent_output_represented(agent_rel: str, source_names: set[str]) -> bool:
    gen_name = Path(agent_rel).name
    if gen_name in source_names:
        return True
    mapped = agent_rule_to_rulesync_name(Path(gen_name))
    if mapped in source_names:
        return True
    for source in source_names:
        if source.startswith("05-") and gen_name == source[3:]:
            return True
    return False


def cursor_output_represented(cursor_rel: str, source_names: set[str]) -> bool:
    stem = Path(cursor_rel).stem
    if f"{stem}.md" in source_names:
        return True
    if stem == "conventional-commits" and "05-conventional-commits.md" in source_names:
        return True
    for source in source_names:
        if Path(source).stem == stem:
            return True
    return False


def preflight_generated_outputs(
    summary: MigrationSummary,
    repo: Path,
    standards: Path,
    selected_rules: list[Path],
    *,
    for_apply: bool,
    will_run_rulesync: bool,
) -> None:
    source_names = rulesync_source_rule_names(repo, selected_rules)
    if summary.migrate_existing_agent_rules:
        source_names.update(summary.migrated_agent_rule_targets)

    orphaned: list[str] = []
    for rel in existing_generated_agent_rules(repo):
        if agent_output_represented(rel, source_names):
            continue
        if summary.migrate_existing_agent_rules:
            mapped = agent_rule_to_rulesync_name(Path(rel).name)
            if mapped in source_names or (repo / ".rulesync" / "rules" / mapped).is_file():
                continue
        orphaned.append(rel)
        summary.existing_generated_outputs.append(rel)
        add_action(
            summary,
            Action(
                "WARN",
                rel,
                "Existing generated agent rule is not represented in selected "
                "Rulesync source and may be removed by Rulesync.",
            ),
        )
        summary.recommendations.append(
            f"Review whether `{rel}` should be migrated into "
            f"`.rulesync/rules/{agent_rule_to_rulesync_name(Path(rel))}` "
            "before running Rulesync."
        )

    for rel in existing_generated_cursor_rules(repo):
        if cursor_output_represented(rel, source_names):
            continue
        summary.existing_generated_outputs.append(rel)
        add_action(
            summary,
            Action(
                "WARN",
                rel,
                "Existing generated Cursor rule is not represented in selected "
                "Rulesync source and may be removed by Rulesync.",
            ),
        )

    if rulesync_delete_enabled(repo, standards):
        add_action(
            summary,
            Action(
                "WARN",
                "rulesync.jsonc",
                'rulesync.jsonc has delete=true; existing generated output may be deleted.',
            ),
        )

    if orphaned and not summary.generated_output_rewrite_allowed and for_apply and will_run_rulesync:
        for rel in orphaned:
            orphan_name = Path(rel).name
            mapped = agent_rule_to_rulesync_name(Path(orphan_name))
            covered = mapped in source_names or (
                repo / ".rulesync" / "rules" / mapped
            ).is_file()
            if summary.migrate_existing_agent_rules and covered:
                continue
            add_action(
                summary,
                Action(
                    "BLOCK",
                    rel,
                    "Rulesync may remove existing generated output; use "
                    "--allow-generated-output-rewrite or --migrate-existing-agent-rules.",
                ),
            )


def has_license_file(repo: Path) -> bool:
    return (repo / "LICENSE").is_file() or (repo / "LICENSE.md").is_file()


def resolve_license_value(summary: MigrationSummary, repo: Path) -> str | None:
    if summary.policy_license:
        return summary.policy_license
    policy_text = summary.rendered_repo_policy
    if not policy_text and (repo / ".repo-policy.yml").is_file():
        policy_text = read_text(repo / ".repo-policy.yml")
    if not policy_text:
        return None
    _, license_value = parse_policy_from_text(policy_text)
    return license_value


def plan_license_file(
    summary: MigrationSummary,
    repo: Path,
    standards: Path,
    *,
    add_license: bool,
    force: bool,
) -> None:
    license_value = resolve_license_value(summary, repo)
    if not license_value:
        return

    lic = license_value.strip().lower()
    if has_license_file(repo):
        if force:
            add_action(
                summary,
                Action(
                    "WARN",
                    "LICENSE",
                    "Existing license file found; not overwriting.",
                ),
            )
        else:
            add_action(
                summary,
                Action("SKIP", "LICENSE", "Existing license file found."),
            )
        return

    if add_license:
        if lic in CLOSED_LICENSES:
            add_action(
                summary,
                Action(
                    "BLOCK",
                    "LICENSE",
                    f"--add-license cannot be used with license {license_value}.",
                ),
            )
            return
        template_name = SUPPORTED_LICENSE_TEMPLATES.get(lic)
        if not template_name:
            add_action(
                summary,
                Action(
                    "BLOCK",
                    "LICENSE",
                    "--add-license currently supports MIT only; add LICENSE manually "
                    "or add a template.",
                ),
            )
            return
        source = standards / template_name
        if not source.is_file():
            add_action(
                summary,
                Action(
                    "BLOCK",
                    "LICENSE",
                    f"License template missing in standards repo: {template_name}",
                ),
            )
            return
        add_action(summary, Action("CREATE", "LICENSE", "From repo-standards LICENSE."))
        return

    visibility = summary.policy_visibility
    if not visibility:
        policy_text = summary.rendered_repo_policy
        if policy_text:
            visibility, _ = parse_policy_from_text(policy_text)
    if lic in OPEN_SOURCE_LICENSES:
        needed, _ = license_warning_needed(
            visibility, license_value, has_license_file(repo)
        )
        if needed:
            add_action(
                summary,
                Action(
                    "WARN",
                    "LICENSE",
                    f".repo-policy.yml declares license {license_value} but LICENSE/LICENSE.md "
                    "is missing. Add --add-license to create it intentionally or adjust "
                    ".repo-policy.yml.",
                ),
            )
        return
    needed, message = license_warning_needed(
        visibility, license_value, has_license_file(repo)
    )
    if needed:
        add_action(summary, Action("WARN", "LICENSE", message))


def plan_policy_source_warnings(summary: MigrationSummary) -> None:
    if summary.visibility_source == "default" or summary.license_source == "default":
        add_action(
            summary,
            Action(
                "WARN",
                ".repo-policy.yml",
                f"visibility/license defaulted to {summary.policy_visibility}/"
                f"{summary.policy_license}; review before merge.",
            ),
        )
        if summary.visibility_source == "default":
            add_action(
                summary,
                Action(
                    "WARN",
                    ".repo-policy.yml",
                    "Could not infer GitHub visibility; defaulted to private/proprietary "
                    "for existing repository migration.",
                ),
            )


def collect_touched_format_paths(summary: MigrationSummary) -> list[str]:
    paths: list[str] = []
    for action in summary.actions:
        if action.action not in {"CREATE", "UPDATE"}:
            continue
        if action.path in FORMAT_TOUCHED_CANDIDATES:
            paths.append(action.path)
        elif action.path.startswith(".github/workflows/") and action.path.endswith(
            (".yml", ".yaml")
        ):
            paths.append(action.path)
    return sorted(set(paths))


def collect_existing_doc_paths(repo: Path) -> list[str]:
    paths: list[str] = []
    for rel in FORMAT_EXISTING_DOC_CANDIDATES:
        if (repo / rel).is_file():
            paths.append(rel)
    docs_dir = repo / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.rglob("*.md")):
            paths.append(path.relative_to(repo).as_posix())
    return sorted(set(paths))


def plan_formatting_recommendations(summary: MigrationSummary, repo: Path) -> None:
    language = summary.detection.get("language")
    if language != "typescript":
        return

    doc_paths = collect_existing_doc_paths(repo)
    if doc_paths:
        summary.recommendations.append(
            "Run with --format-existing-docs if existing Markdown files fail Prettier "
            "after standards checks are introduced."
        )
    if (repo / "CHANGELOG.md").is_file():
        summary.recommendations.append(
            "CHANGELOG.md exists; if format check fails, run "
            "`npx prettier --write CHANGELOG.md` or rerun migration with "
            "--format-existing-docs."
        )


def plan_rulesync_install_recommendation(summary: MigrationSummary, repo: Path) -> None:
    if not (repo / "rulesync.jsonc").is_file() and not has_primary_action(
        summary, "rulesync.jsonc"
    ):
        return
    if has_package_dependency(repo, "rulesync"):
        return

    command = rulesync_install_command_text(repo, summary.detection)
    if command:
        summary.recommendations.append(
            "Rulesync is not installed in this repository. "
            f"Install it with `{command}`, or rerun apply with `--install-rulesync`."
        )
    else:
        summary.recommendations.append(
            "Rulesync is not installed in this repository. "
            "Install it before running Rulesync generation."
        )


def run_prettier(repo: Path, paths: list[str]) -> tuple[str, bool]:
    if not paths:
        return "", True
    try:
        completed = subprocess.run(
            ["npx", "prettier", "--write", *paths],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return f"Prettier unavailable: {exc}", False
    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    ).strip()
    return output, completed.returncode == 0


def apply_formatting(
    summary: MigrationSummary,
    repo: Path,
    *,
    language: str,
    apply_mode: bool,
    skip_format: bool,
    format_touched: bool,
    format_existing_docs: bool,
) -> None:
    if skip_format or not apply_mode:
        summary.formatting_result = "skipped"
        return
    if language != "typescript":
        summary.formatting_result = "skipped"
        return

    paths: list[str] = []
    if format_touched:
        paths.extend(collect_touched_format_paths(summary))
    if format_existing_docs:
        paths.extend(collect_existing_doc_paths(repo))
    paths = sorted(set(paths))
    if not paths:
        summary.formatting_result = "skipped"
        return

    output, ok = run_prettier(repo, paths)
    summary.touched_paths = paths
    if not ok:
        summary.formatting_result = "warned"
        add_action(
            summary,
            Action("WARN", "formatting", f"Prettier formatting incomplete: {output}"),
        )
    else:
        summary.formatting_result = "passed"


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
        add_action(
            summary, Action("BLOCK", rel_path, "Protected path; will not modify.")
        )
        return

    if not source.is_file():
        add_action(
            summary, Action("BLOCK", rel_path, f"Source missing: {source}")
        )
        return

    if not target.is_file():
        add_action(summary, Action("CREATE", rel_path, f"From {source.name}"))
        return

    if files_match(source, target):
        add_action(summary, Action("SKIP", rel_path, "Already matches standards."))
        return

    if authoritative:
        if force:
            add_action(
                summary,
                Action("UPDATE", rel_path, "Overwrite .repo-policy.yml with --force."),
            )
        else:
            add_action(
                summary,
                Action(
                    "SKIP",
                    rel_path,
                    ".repo-policy.yml is authoritative; review manually.",
                ),
            )
            add_action(
                summary,
                Action(
                    "WARN",
                    rel_path,
                    "Existing .repo-policy.yml preserved; use --force to overwrite.",
                ),
            )
        return

    if update_existing or force:
        add_action(
            summary,
            Action("UPDATE", rel_path, "Existing standards-owned file differs."),
        )
    else:
        add_action(
            summary,
            Action(
                "SKIP",
                rel_path,
                "Existing file differs; use --update-existing or --force.",
            ),
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
        add_action(
            summary, Action("BLOCK", rel_path, "Protected path; will not modify.")
        )
        return

    if not target.is_file():
        add_action(summary, Action("CREATE", rel_path, "Generated workflow."))
        return

    if target.read_text(encoding="utf-8") == content:
        add_action(summary, Action("SKIP", rel_path, "Already matches."))
        return

    if update_existing or force:
        add_action(summary, Action("UPDATE", rel_path, "Existing file differs."))
    else:
        add_action(
            summary,
            Action(
                "SKIP",
                rel_path,
                "Existing file differs; use --update-existing or --force.",
            ),
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
    ci_content = reusable_ci_workflow_for(repo, summary.detection)
    if language not in {"typescript", "python"}:
        summary.actions.append(
            Action(
                "WARN",
                ci_rel,
                "Cannot auto-generate reusable CI for this language.",
            )
        )
        return
    if ci_content is None:
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
    adoption_level: str,
    update_existing: bool,
    force: bool,
    allow_generated_output_rewrite: bool,
    cleanup_generated_artifacts: bool,
    replace_check_workflows: bool,
    migrate_existing_agent_rules: bool,
    for_apply: bool,
    will_run_rulesync: bool,
    policy_fields: PolicyFields,
    format_touched: bool,
    format_existing_docs: bool,
    add_license: bool,
) -> MigrationSummary:
    detection = normalize_detection(repo, detect_repo(repo, standards))
    selected_profile = profile or detection["recommended_profile"]
    language = detection["language"]
    selected_rules = selected_rule_files(
        standards, selected_profile, language, rules_strategy
    )
    effective_strategy = effective_workflow_strategy(adoption_level, workflow_strategy)

    summary = MigrationSummary(
        repo=repo,
        mode=mode,
        profile=selected_profile,
        detection=detection,
        workflow_strategy=effective_strategy,
        apply_mode=False,
        rules_strategy=rules_strategy,
        adoption_level=adoption_level,
        selected_rules=[rule.name for rule in selected_rules],
        generated_output_rewrite_allowed=allow_generated_output_rewrite,
        cleanup_generated_artifacts=cleanup_generated_artifacts,
        replace_check_workflows=replace_check_workflows,
        migrate_existing_agent_rules=migrate_existing_agent_rules,
        will_run_rulesync=will_run_rulesync,
        format_touched=format_touched,
        format_existing_docs=format_existing_docs,
        add_license=add_license,
    )

    summary.workflow_classifications = classify_all_workflows(repo)

    plan_repo_policy(
        summary, standards, repo, detection, selected_profile, force, policy_fields
    )
    plan_policy_source_warnings(summary)
    plan_license_file(
        summary, repo, standards, add_license=add_license, force=force
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
    plan_agent_rule_migration(
        summary, repo, selected_rules, migrate_existing_agent_rules
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

    plan_file_copy(
        summary,
        rel_path=".editorconfig",
        source=standards / "templates" / ".editorconfig",
        target=repo / ".editorconfig",
        update_existing=update_existing,
        force=force,
    )

    plan_workflows(
        summary,
        standards,
        repo,
        effective_strategy,
        language,
        update_existing,
        force,
    )

    plan_check_workflow_replacement(
        summary,
        repo,
        adoption_level,
        replace_check_workflows,
        effective_strategy,
        language,
        update_existing,
        force,
    )

    plan_nvmrc(summary, standards, repo, language, force)
    plan_gitignore_merge(summary, repo)

    if adoption_level == "full" or cleanup_generated_artifacts:
        plan_coverage_cleanup(summary, repo, cleanup_generated_artifacts)
    else:
        tracked = tracked_coverage_artifacts(repo)
        summary.tracked_generated_artifacts = tracked

    preflight_generated_outputs(
        summary,
        repo,
        standards,
        selected_rules,
        for_apply=for_apply,
        will_run_rulesync=will_run_rulesync,
    )

    summary.actions.append(
        Action("WARN", repo.as_posix(), "Deploy behavior preserved.")
    )
    summary.actions.append(
        Action("WARN", repo.as_posix(), "Package manager preserved.")
    )

    plan_rulesync_install_recommendation(summary, repo)
    plan_formatting_recommendations(summary, repo)

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
    policy_fields: PolicyFields | None = None,
    add_license: bool = False,
) -> MigrationSummary:
    detection = normalize_detection(repo, detect_repo(repo, standards))
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

    summary.workflow_classifications = classify_all_workflows(repo)
    if policy_fields:
        summary.policy_visibility = policy_fields.visibility
        summary.policy_license = policy_fields.license
        summary.visibility_source = policy_fields.visibility_source
        summary.license_source = policy_fields.license_source
    plan_nvmrc(summary, standards, repo, language, force=False)
    plan_coverage_cleanup(summary, repo, cleanup=False)
    plan_agent_rule_migration(summary, repo, selected_rules, migrate=False)
    summary.add_license = add_license
    plan_license_file(
        summary, repo, standards, add_license=add_license, force=False
    )
    plan_formatting_recommendations(summary, repo)
    preflight_generated_outputs(
        summary,
        repo,
        standards,
        selected_rules,
        for_apply=False,
        will_run_rulesync=False,
    )

    for wf in summary.workflow_classifications:
        if wf["classification"] in {
            "protected-deploy",
            "protected-release",
            "protected-publish",
            "protected-pages",
            "protected-provider",
            "mixed-operational",
        }:
            summary.actions.append(
                Action(
                    "WARN",
                    wf["path"],
                    f"{wf['classification']}: {wf['reason']}",
                )
            )
        elif wf["classification"] == "standards-owned":
            summary.actions.append(
                Action("SKIP", wf["path"], wf["reason"])
            )
        elif wf["classification"] == "replaceable-check":
            summary.actions.append(
                Action("WARN", wf["path"], "Check-only workflow; may be replaceable after review.")
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
    if summary.migrated_agent_rule_targets:
        apply_agent_rule_migration(summary, repo)

    sources: dict[str, Path | None] = {
        "rulesync.jsonc": standards / "templates" / "rulesync.jsonc",
        "CONTRIBUTING.md": standards / "templates" / "CONTRIBUTING.md",
        ".editorconfig": standards / "templates" / ".editorconfig",
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
        ci_content = reusable_ci_workflow_for(repo, summary.detection)

    for action in summary.actions:
        if action.action not in {"CREATE", "UPDATE", "MERGE"}:
            continue

        target = repo / action.path
        if action.action == "MERGE" and action.path == "git index":
            remove_tracked_coverage_from_index(repo, summary.tracked_generated_artifacts)
            continue

        if action.action == "MERGE" and action.path == ".gitignore":
            lines: list[str] = []
            if target.is_file():
                lines = read_text(target).splitlines()
            existing = {line.strip() for line in lines if line.strip()}
            append = [entry for entry in GITIGNORE_MERGE_ENTRIES if entry not in existing]
            if append:
                if lines and lines[-1].strip():
                    lines.append("")
                lines.extend(["# Coverage artifacts", *append])
                target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            continue

        if action.path == ".repo-policy.yml" and summary.rendered_repo_policy:
            execute_create_or_update(None, summary.rendered_repo_policy, target)
            continue

        if action.path.startswith(".rulesync/rules/"):
            rule_name = Path(action.path).name
            if rule_name in summary.migrated_agent_rule_targets:
                continue
            source = standards / "ai" / "rules" / rule_name
            if source.is_file():
                execute_create_or_update(source, None, target)
            continue

        if action.path == ".github/workflows/ci.yml" and ci_content is not None:
            execute_create_or_update(None, ci_content, target)
            continue

        source = sources.get(action.path)
        if source is not None:
            execute_create_or_update(source, None, target)
            if action.path == "rulesync.jsonc" and target.is_file():
                text = read_text(target)
                if text and not text.endswith("\n"):
                    target.write_text(text + "\n", encoding="utf-8")
            continue

        if action.path == "LICENSE":
            license_source = standards / "LICENSE"
            if license_source.is_file():
                execute_create_or_update(license_source, None, target)


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


def install_rulesync(repo: Path, detection: dict[str, Any]) -> tuple[bool, str]:
    command = rulesync_install_command(repo, detection)
    if not command:
        return False, "No package.json found; install Rulesync manually for this project type."
    try:
        completed = subprocess.run(
            command,
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
        f"Adoption level: `{summary.adoption_level}`",
        f"Rules strategy: `{summary.rules_strategy}`",
        f"Interactive mode: `{summary.interactive}`",
        f"Apply mode: `{summary.apply_mode_label}`",
        f"Replace check workflows: `{summary.replace_check_workflows}`",
        f"Generated agent rule migration: `{summary.migrate_existing_agent_rules}`",
        f"Generated-output rewrite allowed: `{summary.generated_output_rewrite_allowed}`",
        f"Cleanup generated artifacts: `{summary.cleanup_generated_artifacts}`",
        f"AI assessment: `{summary.ai_assessment_result}`",
        f"Commit: `{'requested' if summary.commit_requested else 'skipped'}`",
        f"Visibility source: `{summary.visibility_source or 'n/a'}`",
        f"License source: `{summary.license_source or 'n/a'}`",
        f"Formatting touched files: `{summary.format_touched}`",
        f"Formatting existing docs: `{summary.format_existing_docs}`",
        f"Formatting result: `{summary.formatting_result}`",
        f"Add license: `{str(summary.add_license).lower()}`",
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

    formatting_recs = [
        item
        for item in summary.recommendations
        if "CHANGELOG.md" in item or "format-existing-docs" in item
    ]
    lines.extend(
        [
            "",
            "## Formatting",
            "",
            f"- Touched files formatting: `{summary.formatting_result if summary.format_touched else 'skipped'}`",
            f"- Existing docs formatting: `{summary.formatting_result if summary.format_existing_docs else 'skipped'}`",
        ]
    )
    if formatting_recs:
        for item in formatting_recs:
            lines.append(f"- Recommendation: {item}")
    elif summary.formatting_result == "skipped":
        lines.append(
            "- Recommendation: use `--format-touched` or `--format-existing-docs` when "
            "Prettier checks fail after migration."
        )

    if summary.workflow_classifications:
        lines.extend(
            [
                "",
                "## Workflow classification",
                "",
                "| Path | Classification | Reason |",
                "|---|---|---|",
            ]
        )
        for wf in summary.workflow_classifications:
            lines.append(
                f"| `{wf['path']}` | `{wf['classification']}` | {wf['reason']} |"
            )

    if summary.confirmed_decisions:
        lines.extend(["", "## Confirmed decisions", ""])
        lines.extend(f"- {item}" for item in summary.confirmed_decisions)

    if summary.ai_assessment:
        lines.extend(["", "## AI assessment", "", "```json"])
        lines.append(json.dumps(summary.ai_assessment, indent=2, sort_keys=True))
        lines.extend(["```", ""])

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
            f"- Install requested: `{summary.install_rulesync}`",
            f"- Install result: `{summary.rulesync_install_result}`",
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

    if summary.rulesync_install_output:
        lines.extend(
            [
                "## Rulesync install output",
                "",
                "```text",
                summary.rulesync_install_output,
                "```",
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
        "adoption_level": summary.adoption_level,
        "interactive": summary.interactive,
        "replace_check_workflows": summary.replace_check_workflows,
        "migrate_existing_agent_rules": summary.migrate_existing_agent_rules,
        "apply_mode": summary.apply_mode_label,
        "generated_output_rewrite_allowed": summary.generated_output_rewrite_allowed,
        "cleanup_generated_artifacts": summary.cleanup_generated_artifacts,
        "selected_rules": summary.selected_rules,
        "existing_generated_outputs": summary.existing_generated_outputs,
        "tracked_generated_artifacts": summary.tracked_generated_artifacts,
        "workflow_classifications": summary.workflow_classifications,
        "migrated_agent_rule_targets": summary.migrated_agent_rule_targets,
        "confirmed_decisions": summary.confirmed_decisions,
        "ai_assessment": summary.ai_assessment,
        "ai_assessment_result": summary.ai_assessment_result,
        "commit_requested": summary.commit_requested,
        "policy_visibility": summary.policy_visibility,
        "policy_license": summary.policy_license,
        "visibility_source": summary.visibility_source,
        "license_source": summary.license_source,
        "format_touched": summary.format_touched,
        "format_existing_docs": summary.format_existing_docs,
        "formatting_result": summary.formatting_result,
        "touched_paths": summary.touched_paths,
        "add_license": summary.add_license,
        "recommendations": summary.recommendations,
        "detection": summary.detection,
        "actions": [
            {"action": a.action, "path": a.path, "detail": a.detail}
            for a in summary.actions
        ],
        "rulesync": {
            "install_requested": summary.install_rulesync,
            "install_result": summary.rulesync_install_result,
            "install_output": summary.rulesync_install_output,
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
    parser.add_argument(
        "--adoption-level",
        choices=("baseline", "checks", "reusable-ci", "full"),
        default="baseline",
        help="Migration adoption level (default: baseline).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt before risky migration operations.",
    )
    parser.add_argument(
        "--replace-check-workflows",
        action="store_true",
        help="Replace classified check-only workflows.",
    )
    parser.add_argument(
        "--migrate-existing-agent-rules",
        action="store_true",
        help="Migrate existing generated agent rules into Rulesync source.",
    )
    parser.add_argument(
        "--ai-assessment",
        action="store_true",
        help="Run optional GitHub Models advisory migration assessment.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_AI_MODEL,
        help=f"GitHub Models model ID (default: {DEFAULT_AI_MODEL}).",
    )
    parser.add_argument(
        "--dry-run-ai-summary",
        action="store_true",
        help="Print AI assessment safe summary without API call.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Print safe commit guidance after successful apply.",
    )
    parser.add_argument(
        "--commit-message",
        default="chore(standards): adopt repo standards",
        help="Commit message when --commit is used.",
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
        "--install-rulesync",
        action="store_true",
        help="Install Rulesync as a dev dependency before running Rulesync.",
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
        "--skip-format-generated",
        action="store_true",
        help="Skip Prettier formatting of generated or touched files.",
    )
    parser.add_argument(
        "--format-touched",
        action="store_true",
        help="Format migration-touched files with Prettier when available.",
    )
    parser.add_argument(
        "--format-existing-docs",
        action="store_true",
        help="Format existing documentation files with Prettier when available.",
    )
    parser.add_argument(
        "--visibility",
        choices=("public", "private"),
        default=None,
        help="Repository visibility for rendered .repo-policy.yml.",
    )
    parser.add_argument(
        "--license",
        choices=(
            "MIT",
            "Apache-2.0",
            "BSD-3-Clause",
            "ISC",
            "proprietary",
            "none",
        ),
        default=None,
        help="License for rendered .repo-policy.yml.",
    )
    parser.add_argument(
        "--add-license",
        action="store_true",
        help=(
            "Create a LICENSE file when --license is an explicitly supported "
            "open-source license. Currently supports MIT."
        ),
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
    if args.interactive and not sys.stdin.isatty():
        print("Error: --interactive requires a TTY.", file=sys.stderr)
        return 1

    load_env_files(standards, repo)
    apply_mode = args.apply
    will_run_rulesync = apply_mode and not args.skip_rulesync

    replace_check = args.replace_check_workflows
    cleanup = args.cleanup_generated_artifacts
    migrate_rules = args.migrate_existing_agent_rules
    policy_fields = resolve_policy_fields(
        repo, args.mode, args.visibility, args.license
    )

    if args.analyze_existing:
        summary = build_analysis(
            repo,
            standards,
            mode=args.mode,
            profile=args.profile,
            rules_strategy=args.rules_strategy,
            policy_fields=policy_fields,
            add_license=args.add_license,
        )
        summary.adoption_level = args.adoption_level
        if args.dry_run_ai_summary:
            safe = build_ai_safe_summary(summary, repo)
            print(json.dumps(safe, indent=2, sort_keys=True))
            return 0
        if args.ai_assessment:
            safe = build_ai_safe_summary(summary, repo)
            assessment, result = call_migration_ai_assessment(
                standards, safe, args.model
            )
            summary.ai_assessment = assessment
            summary.ai_assessment_result = result
            if assessment is None:
                summary.actions.append(
                    Action("WARN", "ai-assessment", f"AI assessment {result}.")
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
        adoption_level=args.adoption_level,
        update_existing=args.update_existing,
        force=args.force,
        allow_generated_output_rewrite=args.allow_generated_output_rewrite,
        cleanup_generated_artifacts=cleanup,
        replace_check_workflows=replace_check,
        migrate_existing_agent_rules=migrate_rules,
        for_apply=apply_mode,
        will_run_rulesync=will_run_rulesync,
        policy_fields=policy_fields,
        format_touched=args.format_touched,
        format_existing_docs=args.format_existing_docs,
        add_license=args.add_license,
    )
    summary.apply_mode = apply_mode
    summary.interactive = args.interactive
    summary.commit_requested = args.commit
    summary.install_rulesync = args.install_rulesync

    if args.dry_run_ai_summary:
        safe = build_ai_safe_summary(summary, repo)
        print(json.dumps(safe, indent=2, sort_keys=True))
        return 0

    if args.ai_assessment:
        safe = build_ai_safe_summary(summary, repo)
        assessment, result = call_migration_ai_assessment(standards, safe, args.model)
        summary.ai_assessment = assessment
        summary.ai_assessment_result = result
        if assessment is None:
            summary.actions.append(
                Action("WARN", "ai-assessment", f"AI assessment {result}.")
            )

    if args.interactive:
        print(format_summary_markdown(summary))
        if not confirm("Proceed with safe CREATE/MERGE actions?"):
            print("Aborted.", file=sys.stderr)
            return 1
        summary.confirmed_decisions.append("Proceed with safe CREATE/MERGE actions")
        if any(
            wf["classification"] == "replaceable-check"
            for wf in summary.workflow_classifications
        ) and confirm("Replace check-only workflows?", default=False):
            replace_check = True
            summary.confirmed_decisions.append("Replace check-only workflows")
        if summary.tracked_generated_artifacts and confirm(
            "Remove tracked generated artifacts from git index?", default=False
        ):
            cleanup = True
            summary.confirmed_decisions.append("Remove tracked coverage from git index")
        if summary.existing_generated_outputs and confirm(
            "Migrate existing generated agent rules into Rulesync source?", default=False
        ):
            migrate_rules = True
            summary.confirmed_decisions.append("Migrate existing generated agent rules")
        if apply_mode:
            will_run_rulesync = confirm("Run Rulesync?", default=True) and not args.skip_rulesync
            if will_run_rulesync:
                summary.confirmed_decisions.append("Run Rulesync")
        if confirm("Run final assessment?", default=False):
            args.run_assessment = True
            summary.confirmed_decisions.append("Run final assessment")

        summary = build_plan(
            repo,
            standards,
            mode=args.mode,
            profile=args.profile,
            workflow_strategy=args.workflow_strategy,
            rules_strategy=args.rules_strategy,
            adoption_level=args.adoption_level,
            update_existing=args.update_existing,
            force=args.force,
            allow_generated_output_rewrite=args.allow_generated_output_rewrite,
            cleanup_generated_artifacts=cleanup,
            replace_check_workflows=replace_check,
            migrate_existing_agent_rules=migrate_rules,
            for_apply=apply_mode,
            will_run_rulesync=will_run_rulesync,
            policy_fields=policy_fields,
            format_touched=args.format_touched,
            format_existing_docs=args.format_existing_docs,
            add_license=args.add_license,
        )
        summary.apply_mode = apply_mode
        summary.interactive = True
        summary.commit_requested = args.commit
        summary.install_rulesync = args.install_rulesync
        summary.ai_assessment = summary.ai_assessment or None

    if apply_mode:
        blocks = [a for a in summary.by_type("BLOCK")]
        if blocks:
            print("Error: blocked actions prevent apply.", file=sys.stderr)
            for item in blocks:
                print(f"  BLOCK {item.path}: {item.detail}", file=sys.stderr)
            return 1

        apply_actions(summary, standards, repo)
        apply_formatting(
            summary,
            repo,
            language=summary.detection.get("language", ""),
            apply_mode=True,
            skip_format=args.skip_format_generated,
            format_touched=args.format_touched,
            format_existing_docs=args.format_existing_docs,
        )

        if summary.cleanup_generated_artifacts and summary.tracked_generated_artifacts:
            remove_tracked_coverage_from_index(repo, summary.tracked_generated_artifacts)

        if will_run_rulesync and args.install_rulesync and not has_package_dependency(repo, "rulesync"):
            ok, output = install_rulesync(repo, summary.detection)
            summary.rulesync_install_output = output
            if ok:
                summary.rulesync_install_result = "passed"
            else:
                summary.rulesync_install_result = "failed"
                summary.rulesync_result = "skipped"
                summary.actions.append(
                    Action("BLOCK", "rulesync", "Rulesync install failed.")
                )
                print("Error: Rulesync install failed.", file=sys.stderr)
                if output:
                    print(output, file=sys.stderr)

        if will_run_rulesync and summary.rulesync_install_result != "failed":
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

        if args.commit:
            if not args.run_assessment:
                print(
                    "Error: --commit requires --run-assessment for safety checks.",
                    file=sys.stderr,
                )
                return 1
            if summary.assessment_result != "passed":
                print(
                    "Error: assessment did not pass; commit not recommended.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"\nSafe to commit manually:\n  git add .\n  git commit -m \"{args.commit_message}\""
                )
                summary.confirmed_decisions.append("Commit guidance printed")

        summary_path = args.summary_file or (
            repo / ".repo-standards-migration-summary.md"
        )
        summary_path.write_text(format_summary_markdown(summary), encoding="utf-8")
    else:
        summary.rulesync_result = "skipped (dry-run)"
        summary.assessment_result = "skipped (dry-run)"

    if not args.interactive:
        markdown = format_summary_markdown(summary)
        print(markdown)

    if args.json:
        print(json.dumps(summary_to_json(summary), indent=2, sort_keys=True))

    if apply_mode and summary.rulesync_result == "failed":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
