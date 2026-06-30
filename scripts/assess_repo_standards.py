#!/usr/bin/env python3
"""
assess_repo_standards.py

Post-migration assessment for a single repository adopting Repo Standards V1.0.

Based on pilot findings from nab-api:
- Coverage A/M is a blocker; D is acceptable cleanup (with .gitignore check).
- .agents/memories/ is valid generated output when antigravity-ide is configured.
- Rulesync output file existence is checked directly, not via stdout parsing.
- Non-dot agents/ continues to be flagged.
- ESLint, npm audit, low coverage are warnings, not blockers.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from check_code_quality_standards import analyze_repo as analyze_code_quality
from python_dev_requirements import (
    PYTHON_DEV_REQUIREMENT_FILES,
    missing_python_dev_packages,
    primary_python_dev_requirements_path,
)
from release_please_workflow import (
    has_release_please_workflow,
    parse_release_please_enabled,
)


COVERAGE_ARTIFACT_RE = re.compile(
    r"^(coverage|\.coverage|htmlcov|\.nyc_output|\.vitest-coverage|dist/.*\.test\.js|dist/.*\.test\.map)(/|$)",
    re.IGNORECASE,
)

AGENT_MEMORY_RE = re.compile(r"^\.agents/memories(/|$)", re.IGNORECASE)
SUSPICIOUS_AGENTS_RE = re.compile(r"^agents/", re.IGNORECASE)

DEPLOY_RE = re.compile(
    r"(^\.github/workflows/.*(deploy|release|publish|cloudflare|wrangler|pages|firebase|fly|railway|worker).*\.ya?ml$)"
    r"|(^wrangler\.(toml|json)$)"
    r"|(^Dockerfile$)"
    r"|(^fly\.toml$)"
    r"|(^railway\.json$)"
    r"|(^firebase\.json$)"
    r"|(^\.firebaserc$)",
    re.IGNORECASE,
)

SECRETISH_RE = re.compile(
    r"(^|/)(\.env(\..*)?|.*secret.*|.*secrets.*|.*credential.*|.*credentials.*|.*token.*|.*key.*\.pem|id_rsa|id_ed25519)$",
    re.IGNORECASE,
)

SECRETISH_SAFE_PATHS = {
    ".github/workflows/secret-scan.yml",
    ".github/workflows/secret-scan.yaml",
    "templates/workflows/secret-scan.yml",
    "templates/workflows/secret-scan.yaml",
}

SECRETISH_IGNORED_PREFIXES = (
    "node_modules/",
    "coverage/",
    "htmlcov/",
    "dist/",
    "build/",
    ".venv/",
    "venv/",
    "__pycache__/",
)


def is_secretish_path(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    if normalized in SECRETISH_SAFE_PATHS:
        return False
    if any(normalized.startswith(prefix) for prefix in SECRETISH_IGNORED_PREFIXES):
        return False
    return bool(SECRETISH_RE.search(normalized))

COVERAGE_ALL_FILES_RE = re.compile(
    r"All files\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)"
)

ESLINT_PROBLEMS_RE = re.compile(r"✖\s+(\d+)\s+problems?\s+\((\d+)\s+errors?,\s+(\d+)\s+warnings?\)")

NPM_AUDIT_RE = re.compile(r"(\d+)\s+vulnerabilities\s+\(([^)]+)\)")


def _has_secret_scan_workflow(repo: Path) -> bool:
    """Check if any workflow file references a secret scanning tool."""
    workflows = repo / ".github" / "workflows"
    if not workflows.exists():
        return False
    for p in workflows.glob("*"):
        if p.is_file() and p.suffix.lower() in {".yml", ".yaml"}:
            text = read_text(p).lower()
            if "trufflehog" in text or "secret" in text or "gitleaks" in text:
                return True
    return False


def _has_pr_template(repo: Path) -> bool:
    """Check for a pull request template."""
    return (
        exists(repo, ".github/PULL_REQUEST_TEMPLATE.md")
        or exists(repo, "PULL_REQUEST_TEMPLATE.md")
        or exists(repo, ".github/pull_request_template.md")
    )


def _has_license(repo: Path) -> bool:
    """Check for a license file."""
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md"):
        if exists(repo, name):
            return True
    return False


def _read_repo_policy_fields(repo: Path) -> tuple[str | None, str | None]:
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
        license_value = lic_match.group(1).strip().lower()
    return visibility, license_value


def _license_warning_needed(
    visibility: str | None, license_value: str | None, has_license_file: bool
) -> bool:
    if has_license_file or not license_value:
        return False
    closed = {"proprietary", "none", "unlicensed"}
    open_source = {
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
    vis = (visibility or "private").strip().lower()
    lic = license_value.strip().lower()
    if lic in closed:
        return vis == "public"
    return lic in open_source


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": p.returncode,
            "ok": p.returncode == 0,
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
        }
    except Exception as exc:
        return {
            "cmd": " ".join(cmd),
            "returncode": None,
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
        }


def read_text(path: Path, limit: int = 400_000) -> str:
    try:
        return path.read_bytes()[:limit].decode("utf-8", errors="replace")
    except Exception:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


NODE_DEV_TOOL_PACKAGES = {
    "@commitlint/cli",
    "@commitlint/config-conventional",
    "@eslint/js",
    "@vitest/coverage-v8",
    "commitlint",
    "eslint",
    "husky",
    "jest",
    "lint-staged",
    "mocha",
    "prettier",
    "rulesync",
    "typescript",
    "typescript-eslint",
    "vitest",
}


def is_node_dev_tool_package(name: str) -> bool:
    return (
        name in NODE_DEV_TOOL_PACKAGES
        or name.startswith("@types/")
        or name.startswith("eslint-")
        or name.startswith("@eslint/")
    )


def exists(repo: Path, rel: str) -> bool:
    return (repo / rel).exists()


def changed_files_with_status(repo: Path, base_ref: str | None) -> dict[str, str]:
    """Return a dict mapping file path -> git status letter (A, M, D, ?, etc.)."""
    file_map: dict[str, str] = {}

    status = run(["git", "status", "--porcelain"], repo, timeout=30)
    if status["ok"]:
        for line in status["stdout"].splitlines():
            if not line.strip():
                continue
            xy = line[:2].strip()
            rel = line[3:].strip()
            if " -> " in rel:
                rel = rel.split(" -> ", 1)[1]
            file_map[rel.rstrip("/")] = xy

    if base_ref:
        diff = run(["git", "diff", "--name-status", f"{base_ref}...HEAD"], repo, timeout=30)
        if diff["ok"]:
            for line in diff["stdout"].splitlines():
                if not line.strip():
                    continue
                parts = line.strip().split("\t", 1)
                if len(parts) == 2:
                    status_letter = parts[0][0]  # A, M, D, R, etc.
                    rel = parts[1].rstrip("/")
                    if rel not in file_map:
                        file_map[rel] = status_letter

    return file_map


def classify_coverage_changes(
    changed_map: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    """Classify coverage changes into added/modified vs deleted.

    Returns (added_or_modified, deleted, all_coverage_paths).
    """
    added_or_modified: list[str] = []
    deleted: list[str] = []
    all_cov: list[str] = []

    for fpath, status in changed_map.items():
        if COVERAGE_ARTIFACT_RE.search(fpath):
            all_cov.append(fpath)
            if status in ("A", "M", "??"):
                added_or_modified.append(fpath)
            elif status == "D":
                deleted.append(fpath)

    return added_or_modified, deleted, all_cov


def package_state(repo: Path) -> dict[str, Any]:
    package = read_json(repo / "package.json") if exists(repo, "package.json") else {}
    scripts = package.get("scripts") or {}

    runtime_deps = package.get("dependencies") or {}
    dev_deps = package.get("devDependencies") or {}
    deps: dict[str, str] = {}
    for section in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        deps.update(package.get(section) or {})

    package_manager = package.get("packageManager")
    if not package_manager:
        if exists(repo, "package-lock.json"):
            package_manager = "npm"
        elif exists(repo, "pnpm-lock.yaml"):
            package_manager = "pnpm"
        elif exists(repo, "yarn.lock"):
            package_manager = "yarn"
        elif exists(repo, "bun.lock") or exists(repo, "bun.lockb"):
            package_manager = "bun"

    return {
        "has_package_json": bool(package),
        "package_manager": package_manager,
        "has_nvmrc": exists(repo, ".nvmrc"),
        "has_dependabot": exists(repo, ".github/dependabot.yml"),
        "has_secret_scan_workflow": _has_secret_scan_workflow(repo),
        "scripts": scripts,
        "has_rulesync_dependency": "rulesync" in deps,
        "has_commitlint_dependency": "@commitlint/cli" in deps or "commitlint" in deps,
        "has_husky": "husky" in deps or exists(repo, ".husky"),
        "has_lint_staged": "lint-staged" in deps or "lint-staged" in package,
        "runtime_dependencies": sorted(runtime_deps.keys()),
        "dev_dependencies": sorted(dev_deps.keys()),
        "misplaced_dev_dependencies": sorted(
            name for name in runtime_deps if is_node_dev_tool_package(name)
        ),
        "tools": sorted(
            name for name in [
                "typescript",
                "eslint",
                "prettier",
                "vitest",
                "jest",
                "mocha",
                "rulesync",
                "@commitlint/cli",
                "husky",
                "lint-staged",
            ]
            if name in deps
        ),
    }


def python_dependency_state(repo: Path) -> dict[str, Any]:
    policy_text = read_text(repo / ".repo-policy.yml") if exists(repo, ".repo-policy.yml") else ""
    has_runtime_requirements = exists(repo, "requirements.txt")
    dev_files = [name for name in PYTHON_DEV_REQUIREMENT_FILES if exists(repo, name)]
    uses_pip_requirements = (
        has_runtime_requirements
        or "package_manager: pip-requirements" in policy_text
    )
    dev_path = primary_python_dev_requirements_path(repo)
    missing_dev_packages = (
        missing_python_dev_packages(repo, dev_path) if dev_path is not None else []
    )
    return {
        "uses_pip_requirements": uses_pip_requirements,
        "has_requirements_txt": has_runtime_requirements,
        "has_dev_requirements": bool(dev_files),
        "dev_requirement_files": dev_files,
        "missing_requirements_dev": uses_pip_requirements and not dev_files,
        "missing_dev_packages": missing_dev_packages,
    }


def workflow_texts(repo: Path) -> dict[str, str]:
    workflows = repo / ".github" / "workflows"
    if not workflows.exists():
        return {}
    out = {}
    for p in sorted(workflows.glob("*")):
        if p.is_file() and p.suffix.lower() in {".yml", ".yaml"}:
            out[p.relative_to(repo).as_posix()] = read_text(p)
    return out


def workflows_state(repo: Path) -> dict[str, Any]:
    workflows = workflow_texts(repo)
    joined = "\n".join(workflows.values()).lower()

    def mentions(*terms: str) -> bool:
        return any(term.lower() in joined for term in terms)

    return {
        "workflow_count": len(workflows),
        "files": sorted(workflows.keys()),
        "has_ai_rules_workflow": any("ai-rules" in f or "agent" in f for f in workflows),
        "has_semantic_pr_workflow": mentions("semantic-pull-request", "commitlint", "conventional commit"),
        "has_release_please": mentions("release-please"),
        "mentions_lint": bool(re.search(r"\b(lint|eslint|ruff|flake8|pylint)\b", joined)),
        "mentions_typecheck": bool(re.search(r"\b(typecheck|tsc|mypy|pyright)\b", joined)),
        "mentions_test": bool(re.search(r"\b(test|pytest|vitest|jest|mocha)\b", joined)),
        "mentions_coverage": bool(re.search(r"\b(coverage|codecov|lcov|cov)\b", joined)),
        "mentions_deploy": bool(re.search(r"\b(deploy|publish|wrangler|cloudflare|firebase|fly|railway|docker)\b", joined)),
    }


def ai_state(repo: Path) -> dict[str, Any]:
    rulesync_raw = read_text(repo / "rulesync.jsonc") if exists(repo, "rulesync.jsonc") else ""
    rulesync_config = read_json(repo / "rulesync.jsonc") if exists(repo, "rulesync.jsonc") else {}
    rules_dir = repo / ".rulesync" / "rules"

    rule_files = []
    if rules_dir.exists():
        rule_files = sorted(p.relative_to(repo).as_posix() for p in rules_dir.rglob("*") if p.is_file())

    # Detect whether antigravity-ide target is enabled
    targets = rulesync_config.get("targets", {})
    has_antigravity_target = "antigravity-ide" in targets

    # Verify Rulesync output file existence (more reliable than parsing stdout)
    cursor_rules = sorted(
        p.relative_to(repo).as_posix() for p in (repo / ".cursor" / "rules").rglob("*") if p.is_file()
    ) if exists(repo, ".cursor") else []

    agents_rules = sorted(
        p.relative_to(repo).as_posix() for p in (repo / ".agents" / "rules").rglob("*") if p.is_file()
    ) if exists(repo, ".agents") else []

    agents_memories = sorted(
        p.relative_to(repo).as_posix() for p in (repo / ".agents" / "memories").rglob("*") if p.is_file()
    ) if exists(repo, ".agents") else []

    return {
        "has_repo_policy": exists(repo, ".repo-policy.yml"),
        "has_rulesync_config": exists(repo, "rulesync.jsonc"),
        "has_rulesync_rules_dir": rules_dir.exists(),
        "has_agents_md": exists(repo, "AGENTS.md"),
        "has_cursor_rules_dir": exists(repo, ".cursor") or exists(repo, ".cursorrules"),
        "has_agents_rules_dir": exists(repo, ".agents") and any(
            (repo / ".agents" / "rules").rglob("*")
        ) if exists(repo, ".agents") else False,
        "has_agents_memories_dir": exists(repo, ".agents") and any(
            (repo / ".agents" / "memories").rglob("*")
        ) if exists(repo, ".agents") else False,
        "cursor_rule_files": cursor_rules,
        "agents_rule_files": agents_rules,
        "agents_memory_files": agents_memories,
        "rulesync_mentions_agentsmd": "agentsmd" in rulesync_raw.lower() or "agents" in rulesync_raw.lower(),
        "rulesync_mentions_cursor": "cursor" in rulesync_raw.lower(),
        "rulesync_mentions_antigravity": "antigravity" in rulesync_raw.lower(),
        "has_antigravity_target_in_config": has_antigravity_target,
        "rule_files": rule_files,
    }


def docs_state(repo: Path) -> dict[str, Any]:
    text = read_text(repo / "README.md").lower() if exists(repo, "README.md") else ""
    return {
        "has_readme": exists(repo, "README.md"),
        "has_docs_dir": exists(repo, "docs"),
        "readme_mentions_local_dev": "local" in text or "development" in text,
        "readme_mentions_checks": "check" in text or "lint" in text or "test" in text,
        "readme_mentions_deploy_or_release": "deploy" in text or "release" in text or "publish" in text,
        "readme_mentions_ai": "agent" in text or "cursor" in text or "ai" in text,
    }


def safe_commands(repo: Path, pkg: dict[str, Any], ai: dict[str, Any]) -> list[list[str]]:
    commands: list[list[str]] = []
    scripts = pkg["scripts"]

    if pkg["has_package_json"]:
        pm = str(pkg["package_manager"] or "npm")
        if pm.startswith("npm") or pm == "npm":
            commands.append(["npm", "ci"] if exists(repo, "package-lock.json") else ["npm", "install"])
            for script in ["lint", "typecheck", "test", "test:coverage", "build"]:
                if script in scripts:
                    commands.append(["npm", "run", script])
        elif pm.startswith("pnpm") or pm == "pnpm":
            commands.append(["pnpm", "install", "--frozen-lockfile"])
            for script in ["lint", "typecheck", "test", "test:coverage", "build"]:
                if script in scripts:
                    commands.append(["pnpm", "run", script])
        elif pm.startswith("yarn") or pm == "yarn":
            commands.append(["yarn", "install", "--frozen-lockfile"])
            for script in ["lint", "typecheck", "test", "test:coverage", "build"]:
                if script in scripts:
                    commands.append(["yarn", script])

    if ai["has_rulesync_config"]:
        if pkg["has_rulesync_dependency"]:
            commands.append(["npx", "rulesync", "generate"])
        else:
            commands.append(["npx", "-y", "rulesync", "generate"])

    commands.append(["git", "diff", "--check"])
    return commands


def analyze_command_outputs(commands: list[dict[str, Any]]) -> dict[str, Any]:
    eslint_warnings = 0
    eslint_errors = 0
    npm_vulnerabilities = None
    npm_vulnerability_detail = None
    coverage = None

    for c in commands:
        out = f"{c.get('stdout', '')}\n{c.get('stderr', '')}"

        if c["cmd"].startswith("npm run lint"):
            m = ESLINT_PROBLEMS_RE.search(out)
            if m:
                eslint_errors += int(m.group(2))
                eslint_warnings += int(m.group(3))

        if c["cmd"] == "npm ci":
            m = NPM_AUDIT_RE.search(out)
            if m:
                npm_vulnerabilities = int(m.group(1))
                npm_vulnerability_detail = m.group(2)

        if "test:coverage" in c["cmd"] or "coverage" in c["cmd"]:
            m = COVERAGE_ALL_FILES_RE.search(out)
            if m:
                coverage = {
                    "statements": float(m.group(1)),
                    "branches": float(m.group(2)),
                    "functions": float(m.group(3)),
                    "lines": float(m.group(4)),
                }

    return {
        "eslint_errors": eslint_errors,
        "eslint_warnings": eslint_warnings,
        "npm_vulnerabilities": npm_vulnerabilities,
        "npm_vulnerability_detail": npm_vulnerability_detail,
        "coverage": coverage,
    }


def check_gitignore_contains_coverage(repo: Path) -> bool:
    """Check if .gitignore contains a 'coverage/' entry (or similar)."""
    gitignore_text = read_text(repo / ".gitignore").lower() if exists(repo, ".gitignore") else ""
    return bool(re.search(r"^\s*coverage/\s*$", gitignore_text, re.MULTILINE))


def has_gitignore(repo: Path) -> bool:
    """Check if .gitignore exists."""
    return exists(repo, ".gitignore")


def has_editorconfig(repo: Path) -> bool:
    """Check if .editorconfig exists."""
    return exists(repo, ".editorconfig")


def has_env_example(repo: Path) -> bool:
    """Check if .env.example exists."""
    return exists(repo, ".env.example")


def has_security_md(repo: Path) -> bool:
    """Check if SECURITY.md exists."""
    return exists(repo, "SECURITY.md")


def has_issue_templates(repo: Path) -> bool:
    """Check if issue templates exist."""
    issue_templates_dir = repo / ".github" / "ISSUE_TEMPLATE"
    if not issue_templates_dir.exists():
        return False
    return any(p.is_file() for p in issue_templates_dir.glob("*"))


def has_adr_template_or_decisions_dir(repo: Path) -> bool:
    """Check for ADR template or decisions directory."""
    # Check for ADR template
    if exists(repo, "templates/docs/decisions/ADR-000-template.md"):
        return True
    # Check for decisions directory with ADR files
    decisions_dir = repo / "docs" / "decisions"
    if decisions_dir.exists():
        return any(p.is_file() for p in decisions_dir.glob("ADR-*.md"))
    return False


def check_gitignore_excludes_env(repo: Path) -> bool:
    """Check if .gitignore excludes .env and .env.* but not .env.example."""
    gitignore_text = read_text(repo / ".gitignore").lower() if exists(repo, ".gitignore") else ""
    # Should exclude .env and .env.*
    excludes_env = bool(re.search(r"^\s*\.env\s*$", gitignore_text, re.MULTILINE))
    excludes_env_star = bool(re.search(r"^\s*\.env\.\*\s*$", gitignore_text, re.MULTILINE))
    # Should NOT exclude .env.example
    excludes_example = bool(re.search(r"^\s*\.env\.example\s*$", gitignore_text, re.MULTILINE))
    return excludes_env and excludes_env_star and not excludes_example


def release_state(repo: Path) -> dict[str, Any]:
    policy_text = read_text(repo / ".repo-policy.yml") if exists(repo, ".repo-policy.yml") else ""
    policy_enabled = parse_release_please_enabled(policy_text)
    has_workflow = has_release_please_workflow(repo)
    return {
        "policy_release_please": policy_enabled,
        "has_workflow": has_workflow,
    }


def score_report(
    state: dict[str, Any],
    command_analysis: dict[str, Any],
    commands: list[dict[str, Any]],
    coverage_added_or_modified: list[str],
    coverage_deleted: list[str],
) -> tuple[int, list[str], list[str]]:
    score = 100
    blockers: list[str] = []
    warnings: list[str] = []

    ai = state["ai"]
    wf = state["workflows"]
    pkg = state["package"]
    pydeps = state["python_dependencies"]
    docs = state["docs"]
    changed = state["changed"]
    gi = state["gitignore"]
    gov = state["governance"]
    code_quality = state.get("code_quality", {})
    has_coverage_in_gitignore = gi["has_coverage"]

    # Required files and workflows
    required = [
        ("Missing .repo-policy.yml", ai["has_repo_policy"]),
        ("Missing rulesync.jsonc", ai["has_rulesync_config"]),
        ("Missing .rulesync/rules directory", ai["has_rulesync_rules_dir"]),
        ("Missing AGENTS.md", ai["has_agents_md"]),
        ("Missing Cursor rules output (.cursor/rules/*)", ai["has_cursor_rules_dir"]),
        ("Missing Antigravity rules output (.agents/rules/*)", ai["has_agents_rules_dir"]),
        ("Missing AI rules sync workflow", wf["has_ai_rules_workflow"]),
        ("Missing semantic PR / conventional commit enforcement", wf["has_semantic_pr_workflow"]),
        ("Missing README.md", docs["has_readme"]),
        ("Missing .gitignore", gi["has_gitignore"]),
    ]

    for msg, ok in required:
        if not ok:
            score -= 8
            blockers.append(msg)

    release = state.get("release", {})
    if release.get("policy_release_please") is True and not release.get("has_workflow"):
        score -= 8
        blockers.append(
            "Missing Release Please workflow (.github/workflows/release-please.yml) "
            "required by .repo-policy.yml"
        )

    # Coverage changes: A/M is blocker, D is acceptable (warn if .gitignore missing)
    if coverage_added_or_modified:
        score -= 12
        blockers.append(
            f"Coverage/build artifacts added or modified in diff: {coverage_added_or_modified}. "
            "These must not be committed in a standards migration PR."
        )

    if coverage_deleted:
        if has_coverage_in_gitignore:
            warnings.append(
                f"Deleted coverage artifacts detected ({len(coverage_deleted)} files). "
                "This is acceptable cleanup when coverage/ is in .gitignore."
            )
        else:
            warnings.append(
                f"Deleted coverage artifacts detected ({len(coverage_deleted)} files) "
                "but coverage/ is not in .gitignore. Add coverage/ to .gitignore."
            )

    # Antigravity memories: not a blocker when antigravity-ide is configured
    if changed["agent_memories"]:
        if ai["has_antigravity_target_in_config"]:
            warnings.append(
                ".agents/memories/ is in the diff, but antigravity-ide target is configured. "
                "This is valid generated output."
            )
        else:
            score -= 4
            warnings.append(
                ".agents/memories/ is in the diff but antigravity-ide target is NOT configured in rulesync.jsonc. "
                "Manual review required."
            )

    # Non-dot agents path
    if changed["suspicious_agents_paths"]:
        score -= 6
        warnings.append("Suspicious non-dot `agents/` path detected; confirm it is intentional and documented")

    # Secrets and deploy files
    if changed["secretish_files"]:
        score -= 20
        blockers.append(
            "Secret-like files appear changed or untracked: "
            + ", ".join(changed["secretish_files"])
            if changed["secretish_files"]
            else "Secret-like files appear changed or untracked"
        )
    if changed["risky_deploy_files"]:
        warnings.append("Deploy/release files changed; manually verify this was intentional")

    # Package state
    if pkg["has_package_json"]:
        if "lint" not in pkg["scripts"]:
            score -= 4
            warnings.append("Node repo has no lint script")
        if "test" not in pkg["scripts"]:
            score -= 4
            warnings.append("Node repo has no test script")
        if "build" not in pkg["scripts"]:
            score -= 2
            warnings.append("Node repo has no build script")
        if not pkg["has_nvmrc"]:
            warnings.append("Node repo missing `.nvmrc`; recommended but not yet required")
        if pkg["misplaced_dev_dependencies"]:
            warnings.append(
                "Node dev tooling packages should be in devDependencies, not dependencies: "
                + ", ".join(pkg["misplaced_dev_dependencies"])
            )
    if not pkg["has_rulesync_dependency"]:
        if pkg["has_package_json"]:
            warnings.append(
                "Rulesync is mandatory but is not pinned in devDependencies; install it with "
                "`npm install -D rulesync` or the equivalent package-manager command."
            )
        else:
            warnings.append(
                "Rulesync is mandatory but no tooling package.json pins it; non-Node repos "
                "should add a private tooling-only package.json with rulesync in devDependencies."
            )
    if pydeps["missing_requirements_dev"]:
        warnings.append(
            "Python pip repo missing `requirements-dev.txt`; keep test/lint/coverage tools "
            "separate from runtime `requirements.txt`."
        )
    if pydeps["missing_dev_packages"]:
        warnings.append(
            "Python dev requirements file is missing repo-standards tooling packages: "
            + ", ".join(pydeps["missing_dev_packages"])
        )
    if not pkg["has_dependabot"]:
        warnings.append("Missing `.github/dependabot.yml`; recommended but not yet required")
    if not pkg["has_secret_scan_workflow"]:
        warnings.append("Missing secret scanning workflow; recommended but not yet required")

    # Governance files (warnings only for existing repos)
    if not gov["has_contributing"]:
        warnings.append("Missing `CONTRIBUTING.md`; recommended but not yet required")
    if not gov["has_pr_template"]:
        warnings.append("Missing pull request template (`.github/PULL_REQUEST_TEMPLATE.md`); recommended but not yet required")
    if not gov["has_license"]:
        visibility = gov.get("policy_visibility")
        license_value = gov.get("policy_license")
        if _license_warning_needed(visibility, license_value, False):
            if license_value in {"proprietary", "none", "unlicensed"} and visibility == "public":
                warnings.append(
                    "Public repository declares a closed license in `.repo-policy.yml`; "
                    "review visibility and license."
                )
            else:
                warnings.append(
                    "Missing `LICENSE` or `LICENSE.md` for declared open-source license in "
                    "`.repo-policy.yml`; add a license intentionally or adjust policy."
                )

    # Repository health baseline (warnings initially for existing repos)
    if not gi["has_editorconfig"]:
        warnings.append("Missing `.editorconfig`; recommended but not yet required")
    if not gi["has_env_example"]:
        warnings.append("Missing `.env.example`; recommended but not yet required")
    if not gi["has_security_md"]:
        warnings.append("Missing `SECURITY.md`; recommended but not yet required")
    if not gi["has_issue_templates"]:
        warnings.append("Missing issue templates (`.github/ISSUE_TEMPLATE/`); optional but recommended")
    if not gi["has_adr_template_or_decisions_dir"]:
        warnings.append("Missing ADR directory or template; optional recommendation only")

    # Check .gitignore properly excludes .env but not .env.example
    if gi["has_gitignore"] and not gi["excludes_env_not_example"]:
        warnings.append(".gitignore should exclude .env and .env.* but not .env.example")

    # Docs check
    if not docs["readme_mentions_checks"]:
        score -= 3
        warnings.append("README does not appear to document checks")
    if not docs["readme_mentions_deploy_or_release"]:
        warnings.append("README does not appear to document deploy/release behavior")
    if not docs["readme_mentions_ai"]:
        warnings.append("README does not mention AI/editor instructions")

    # Technical debt: warnings only
    for finding in code_quality.get("findings", []):
        if finding.get("status") in {"WARN", "FAIL"}:
            warnings.append(f"Code quality standards: {finding.get('message')}")

    if command_analysis["eslint_warnings"]:
        warnings.append(
            f"ESLint passed but reported {command_analysis['eslint_warnings']} warnings "
            f"(and {command_analysis['eslint_errors']} errors if any)"
        )
    if command_analysis["npm_vulnerabilities"]:
        warnings.append(
            f"npm audit reported {command_analysis['npm_vulnerabilities']} vulnerabilities "
            f"({command_analysis['npm_vulnerability_detail']})"
        )
    if command_analysis["coverage"]:
        cov = command_analysis["coverage"]
        if cov["lines"] < 50:
            warnings.append(
                f"Coverage is low: {cov['lines']}% lines, {cov['branches']}% branches. "
                "Keep coverage as report-only."
            )
    elif wf["mentions_coverage"]:
        warnings.append("Coverage workflow/script detected, but coverage summary was not parsed")

    # Command failures
    if any(not c["ok"] for c in commands):
        score = max(0, score - 10)
        blockers.append("One or more safe verification commands failed")

    return max(score, 0), sorted(set(blockers)), sorted(set(warnings))


def make_recommendations(
    state: dict[str, Any],
    command_analysis: dict[str, Any],
    coverage_added_or_modified: list[str],
    coverage_deleted: list[str],
) -> tuple[list[str], list[str]]:
    recs: list[str] = []
    feedback: list[str] = []

    changed = state["changed"]
    wf = state["workflows"]
    ai = state["ai"]
    pkg = state["package"]
    pydeps = state["python_dependencies"]

    if coverage_added_or_modified:
        recs.append("Remove generated coverage/build artifacts from the PR and add `coverage/` to `.gitignore`.")
    if coverage_deleted and not state["gitignore"]["has_coverage"]:
        recs.append("Add `coverage/` to `.gitignore` and stage the deletion of previously tracked coverage files.")
    if changed["suspicious_agents_paths"]:
        recs.append("Inspect `agents/` without a leading dot; move/remove it unless a tool explicitly requires that path.")
    if command_analysis["coverage"] and command_analysis["coverage"]["lines"] < 50:
        recs.append("Keep coverage as report-only for this repo; do not add a threshold until coverage is improved.")
    if command_analysis["eslint_warnings"]:
        recs.append("Track existing ESLint warnings as technical debt; do not fix them in the standards PR unless trivial.")
    if command_analysis["npm_vulnerabilities"]:
        recs.append("Open a separate dependency-audit PR; do not mix audit fixes into the standards PR.")
    if not wf["has_release_please"]:
        recs.append(
            "If this repo ships releases, add Release Please via "
            "`apply_repo_standards.py` or copy `templates/workflows/release-please.*.yml`."
        )
    if pydeps["missing_requirements_dev"]:
        recs.append(
            "Add `requirements-dev.txt` with dev-only tools such as pytest, coverage, "
            "ruff, and test helpers; keep runtime dependencies in `requirements.txt`."
        )
    if pydeps["missing_dev_packages"]:
        recs.append(
            "Add missing dev packages to `requirements-dev.txt`: "
            + ", ".join(pydeps["missing_dev_packages"])
        )
    if pkg["misplaced_dev_dependencies"]:
        recs.append(
            "Move Node tooling packages from `dependencies` to `devDependencies`: "
            + ", ".join(pkg["misplaced_dev_dependencies"])
        )

    if not ai["has_rulesync_config"]:
        recs.append("Add `rulesync.jsonc` from the standards template.")
    if not ai["has_rulesync_rules_dir"]:
        recs.append("Add `.rulesync/rules/*` as the canonical AI/editor source.")
    if ai["has_rulesync_config"] and not state["package"]["has_rulesync_dependency"]:
        if state["package"]["has_package_json"]:
            recs.append("Install Rulesync as a dev dependency, then run `npx rulesync generate`.")
        else:
            recs.append(
                "Add a private tooling-only `package.json`, install Rulesync in devDependencies, "
                "then run `npm run rulesync`."
            )
    if not ai["has_agents_md"]:
        recs.append("Run Rulesync and commit generated files.")
    if not ai["has_cursor_rules_dir"]:
        recs.append("Verify Cursor rules are generated by Rulesync.")
    if not ai["has_agents_rules_dir"]:
        recs.append("Verify Antigravity rules are generated by Rulesync.")

    if changed["agent_memories"] and not ai["has_antigravity_target_in_config"]:
        recs.append("Review .agents/memories/ -- if intentional, add antigravity-ide to rulesync.jsonc targets.")
    if not feedback:
        feedback.append("No repo-standards blueprint changes suggested by this assessment.")

    return recs, feedback


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# {report['repo']['name']} Standards Migration Assessment v3")
    lines.append("")
    lines.append(f"Generated: `{report['generated_at']}`")
    lines.append(f"Repo: `{report['repo']['path']}`")
    lines.append(f"Standards repo: `{report['standards']['path']}`")
    lines.append(f"Score: **{report['score']['value']}/100**")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append(report["verdict"])
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    lines.extend([f"- {x}" for x in report["score"]["blockers"]] or ["- None detected"])
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    lines.extend([f"- {x}" for x in report["score"]["warnings"]] or ["- None detected"])

    lines.append("")
    lines.append("## Changed-file hygiene")
    lines.append("")
    for key in ["generated_artifacts", "agent_memories", "suspicious_agents_paths", "risky_deploy_files", "secretish_files"]:
        values = report["state"]["changed"].get(key) or []
        lines.append(f"### {key}")
        lines.extend([f"- `{x}`" for x in values] or ["- None"])
        lines.append("")

    lines.append("## Coverage detail")
    lines.append("")
    lines.append(f"- Added or modified: {report['coverage_detail']['added_or_modified']}")
    lines.append(f"- Deleted: {report['coverage_detail']['deleted']}")
    lines.append(f"- .gitignore has coverage/: {report['coverage_detail']['gitignore_has_coverage']}")
    lines.append("")

    lines.append("## Command analysis")
    lines.append("")
    for k, v in report["command_analysis"].items():
        lines.append(f"- `{k}`: `{v}`")

    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    lines.extend([f"- {x}" for x in report["recommendations"]] or ["- None"])

    lines.append("")
    lines.append("## Standards feedback")
    lines.append("")
    lines.extend([f"- {x}" for x in report["standards_feedback"]] or ["- None"])

    lines.append("")
    lines.append("## Full state")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["state"], indent=2, sort_keys=True))
    lines.append("```")

    path.write_text("\n".join(lines), encoding="utf-8")


def assess(repo: Path, standards: Path, base_ref: str | None, run_safe_checks: bool) -> dict[str, Any]:
    changed_map = changed_files_with_status(repo, base_ref)
    coverage_added_or_modified, coverage_deleted, all_coverage_paths = classify_coverage_changes(changed_map)
    files = sorted(changed_map.keys())

    policy_visibility, policy_license = _read_repo_policy_fields(repo)
    state = {
        "package": package_state(repo),
        "python_dependencies": python_dependency_state(repo),
        "release": release_state(repo),
        "workflows": workflows_state(repo),
        "ai": ai_state(repo),
        "docs": docs_state(repo),
        "gitignore": {
            "has_coverage": check_gitignore_contains_coverage(repo),
            "has_gitignore": has_gitignore(repo),
            "has_editorconfig": has_editorconfig(repo),
            "has_env_example": has_env_example(repo),
            "has_security_md": has_security_md(repo),
            "has_issue_templates": has_issue_templates(repo),
            "has_adr_template_or_decisions_dir": has_adr_template_or_decisions_dir(repo),
            "excludes_env_not_example": check_gitignore_excludes_env(repo) if has_gitignore(repo) else False,
        },
        "governance": {
            "has_contributing": exists(repo, "CONTRIBUTING.md"),
            "has_pr_template": _has_pr_template(repo),
            "has_license": _has_license(repo),
            "policy_visibility": policy_visibility,
            "policy_license": policy_license,
        },
        "code_quality": analyze_code_quality(repo, strict=False, run_tools=False),
        "changed": {
            "files": files,
            "generated_artifacts": all_coverage_paths,
            "agent_memories": [f for f in files if AGENT_MEMORY_RE.search(f)],
            "suspicious_agents_paths": [f for f in files if SUSPICIOUS_AGENTS_RE.search(f)],
            "risky_deploy_files": [f for f in files if DEPLOY_RE.search(f)],
            "secretish_files": [f for f in files if is_secretish_path(f)],
        },
    }

    commands = []
    if run_safe_checks:
        for cmd in safe_commands(repo, state["package"], state["ai"]):
            timeout = 300 if cmd[0] in {"npm", "pnpm", "yarn"} else 120
            commands.append(run(cmd, repo, timeout=timeout))

    command_analysis = analyze_command_outputs(commands)
    score, blockers, warnings = score_report(
        state, command_analysis, commands,
        coverage_added_or_modified, coverage_deleted,
    )
    recs, feedback = make_recommendations(state, command_analysis, coverage_added_or_modified, coverage_deleted)

    if blockers:
        verdict = "Not ready to merge. Clean up blockers first."
    elif score >= 90:
        verdict = "Looks ready for review. Remaining items are warnings or follow-up work."
    elif score >= 75:
        verdict = "Mostly aligned, but review warnings before merging."
    else:
        verdict = "Partially aligned. Revise before review."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": {"name": repo.name, "path": str(repo)},
        "standards": {"path": str(standards)},
        "state": state,
        "commands": commands,
        "command_analysis": command_analysis,
        "score": {"value": score, "blockers": blockers, "warnings": warnings},
        "verdict": verdict,
        "recommendations": recs,
        "standards_feedback": feedback,
        "coverage_detail": {
            "added_or_modified": coverage_added_or_modified,
            "deleted": coverage_deleted,
            "gitignore_has_coverage": state["gitignore"]["has_coverage"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--standards", required=True)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--output-dir")
    parser.add_argument("--run-safe-checks", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    standards = Path(args.standards).expanduser().resolve()

    if not repo.is_dir():
        raise SystemExit(f"Repo path is not a directory: {repo}")
    if not standards.is_dir():
        raise SystemExit(f"Standards path is not a directory: {standards}")

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else standards / "assessments" / "generated"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    report = assess(repo, standards, args.base_ref, args.run_safe_checks)

    md_path = output_dir / f"{repo.name}.standards-assessment-v3.md"
    json_path = output_dir / f"{repo.name}.standards-assessment-v3.json"

    write_markdown(report, md_path)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Score: {report['score']['value']}/100")
    print(f"Verdict: {report['verdict']}")
    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")

    if report["score"]["blockers"]:
        print("\nBlockers:")
        for blocker in report["score"]["blockers"]:
            print(f"- {blocker}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
