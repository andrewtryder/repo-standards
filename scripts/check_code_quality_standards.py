#!/usr/bin/env python3
"""Read-only file-pattern-aware code quality standards analyzer."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".venv-docs",
    "venv",
    "node_modules",
    "coverage",
    "htmlcov",
    "dist",
    "build",
    "site",
    "generated",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}


@dataclass(frozen=True)
class Area:
    key: str
    name: str
    patterns: tuple[str, ...]
    gate: str
    tools: tuple[str, ...]
    guidance: str


@dataclass
class Finding:
    area: str
    status: str
    message: str
    files: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    command: str | None = None
    returncode: int | None = None


AREAS = [
    Area(
        "python",
        "Python",
        ("*.py",),
        "lint, test, coverage",
        ("ruff", "pytest", "coverage"),
        "Use Ruff for format/lint and pytest/coverage when configured.",
    ),
    Area(
        "javascript",
        "TypeScript/JavaScript",
        ("*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.cjs"),
        "format_check, lint, typecheck, test, build",
        ("prettier", "eslint", "typescript"),
        "Use repo package scripts or equivalent tools.",
    ),
    Area(
        "shell",
        "Shell",
        ("*.sh", "*.bash"),
        "lint",
        ("shellcheck",),
        "Use ShellCheck when shell files are present.",
    ),
    Area(
        "yaml",
        "YAML",
        ("*.yml", "*.yaml"),
        "lint",
        ("yamllint", "prettier"),
        "Use yamllint or a compatible formatter/checker.",
    ),
    Area(
        "github_actions",
        "GitHub Actions",
        (".github/workflows/*.yml", ".github/workflows/*.yaml"),
        "lint / workflow validation",
        ("actionlint",),
        "Use actionlint for workflow syntax and expression checks.",
    ),
    Area(
        "markdown",
        "Markdown",
        ("*.md",),
        "docs",
        ("markdownlint", "mdformat", "prettier"),
        "Use markdownlint, mdformat, Prettier, or docs checks.",
    ),
    Area(
        "docker",
        "Docker",
        ("Dockerfile", "Dockerfile.*"),
        "lint / build",
        ("hadolint",),
        "Use hadolint where Dockerfiles are part of the repo.",
    ),
    Area(
        "make",
        "Make",
        ("Makefile", "*.mk"),
        "lint",
        ("checkmake",),
        "Use checkmake if Make linting is adopted.",
    ),
    Area(
        "data",
        "JSON / JSONC / TOML",
        ("*.json", "*.jsonc", "*.toml"),
        "lint",
        ("prettier", "taplo"),
        "Use parser validation, Prettier, taplo, or repo-local checks.",
    ),
]


def read_text(path: Path, limit: int = 600_000) -> str:
    try:
        return path.read_bytes()[:limit].decode("utf-8", errors="replace")
    except Exception:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


def iter_files(repo: Path) -> list[Path]:
    if (repo / ".git").exists():
        try:
            completed = subprocess.run(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            completed = None
        if completed and completed.returncode == 0:
            files = [
                repo / line
                for line in completed.stdout.splitlines()
                if line and (repo / line).is_file()
            ]
            if files:
                return sorted(files)

    files: list[Path] = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        root_path = Path(root)
        for name in names:
            files.append(root_path / name)
    return sorted(files)


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern) for pattern in patterns)


def repo_context(repo: Path) -> dict[str, Any]:
    package = read_json(repo / "package.json")
    scripts = package.get("scripts") or {}
    deps: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps.update(package.get(section) or {})

    texts = []
    for rel in (
        ".repo-policy.yml",
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        "pyproject.toml",
        "ruff.toml",
        ".yamllint.yml",
        ".yamllint.yaml",
        ".markdownlint.json",
        ".markdownlint.yml",
        "eslint.config.js",
        "eslint.config.mjs",
        ".eslintrc",
        ".eslintrc.json",
    ):
        path = repo / rel
        if path.is_file():
            texts.append(read_text(path))
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        for path in sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml")):
            texts.append(read_text(path))

    policy = read_text(repo / ".repo-policy.yml")
    profile = None
    for line in policy.splitlines():
        if line.strip().startswith("profile:"):
            profile = line.split(":", 1)[1].strip().strip('"\'')
            break

    return {
        "profile": profile,
        "scripts": scripts,
        "deps": deps,
        "text": "\n".join(texts).lower(),
    }


def area_files(repo: Path, files: list[Path], area: Area) -> list[str]:
    found: list[str] = []
    for path in files:
        rel = path.relative_to(repo).as_posix()
        if matches(rel, area.patterns):
            found.append(rel)
    return found


def configured_tools(area: Area, context: dict[str, Any], command_overrides: dict[str, str]) -> list[str]:
    haystack = context["text"]
    scripts = context["scripts"]
    deps = context["deps"]
    configured: set[str] = set()

    if command_overrides.get(area.key):
        configured.add("workflow-input-command")

    for tool in area.tools:
        if tool in deps or tool.lower() in haystack:
            configured.add(tool)

    script_terms = {
        "python": ("lint", "format", "test", "coverage"),
        "javascript": ("lint", "format", "format:check", "typecheck", "test", "build"),
        "shell": ("lint:shell", "shellcheck"),
        "yaml": ("lint:yaml", "yamllint"),
        "github_actions": ("actionlint", "lint:actions"),
        "markdown": ("docs", "lint:md", "markdownlint"),
        "docker": ("lint:docker", "hadolint"),
        "make": ("lint:make", "checkmake"),
        "data": ("lint:json", "lint:toml", "format:check"),
    }
    for name, command in scripts.items():
        combined = f"{name} {command}".lower()
        if any(term in combined for term in script_terms.get(area.key, ())):
            configured.add("package-script")

    if area.key == "data":
        configured.add("parser-validation")
    if area.key == "markdown" and ("docs-check" in haystack or "mkdocs build" in haystack):
        configured.add("docs-check")
    if area.key == "yaml" and ("yaml.safe_load" in haystack or "validate yaml" in haystack):
        configured.add("parser-validation")

    return sorted(configured)


def check_json_files(repo: Path, rel_files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    bad: list[str] = []
    for rel in rel_files:
        if rel.endswith(".json"):
            try:
                json.loads(read_text(repo / rel))
            except Exception:
                bad.append(rel)
    if bad:
        findings.append(Finding("data", "FAIL", "JSON parser validation failed.", files=bad[:20]))
    return findings


def command_for_area(area: Area, rel_files: list[str]) -> list[str] | None:
    if area.key == "python" and shutil.which("ruff"):
        return ["ruff", "check", "."]
    if area.key == "shell" and shutil.which("shellcheck"):
        return ["shellcheck", *rel_files]
    if area.key == "yaml" and shutil.which("yamllint"):
        return ["yamllint", "."]
    if area.key == "github_actions" and shutil.which("actionlint"):
        return ["actionlint"]
    if area.key == "docker" and shutil.which("hadolint"):
        return ["hadolint", *rel_files]
    if area.key == "make" and shutil.which("checkmake"):
        return ["checkmake", *rel_files]
    return None


def run_tool(repo: Path, area: Area, rel_files: list[str], strict: bool, command_override: str | None) -> Finding:
    if command_override:
        proc = subprocess.run(
            command_override,
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=False,
        )
        status = "PASS" if proc.returncode == 0 else "FAIL"
        return Finding(
            area.key,
            status,
            f"{area.name}: ran configured workflow input command.",
            files=rel_files[:10],
            command=command_override,
            returncode=proc.returncode,
        )

    cmd = command_for_area(area, rel_files)
    if not cmd:
        status = "WARN" if strict else "SKIP"
        return Finding(area.key, status, f"{area.name}: external check tool is not installed.", files=rel_files[:10])
    proc = subprocess.run(cmd, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    status = "PASS" if proc.returncode == 0 else "FAIL"
    return Finding(
        area.key,
        status,
        f"{area.name}: ran {' '.join(cmd)}.",
        files=rel_files[:10],
        command=" ".join(cmd),
        returncode=proc.returncode,
    )


def analyze_repo(
    repo: Path,
    strict: bool = False,
    run_tools: bool = False,
    enabled_areas: set[str] | None = None,
    command_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    files = iter_files(repo)
    context = repo_context(repo)
    findings: list[Finding] = []
    command_overrides = command_overrides or {}

    for area in AREAS:
        if enabled_areas is not None and area.key not in enabled_areas:
            findings.append(Finding(area.key, "SKIP", f"{area.name}: disabled by workflow/input configuration."))
            continue

        rel_files = area_files(repo, files, area)
        if not rel_files:
            findings.append(Finding(area.key, "SKIP", f"{area.name}: no matching files found."))
            continue

        tools = configured_tools(area, context, command_overrides)
        if tools:
            findings.append(
                Finding(
                    area.key,
                    "PASS",
                    f"{area.name}: matching files found and tooling/configuration was detected.",
                    files=rel_files[:10],
                    tools=tools,
                )
            )
        else:
            findings.append(
                Finding(
                    area.key,
                    "FAIL" if strict else "WARN",
                    f"{area.name}: matching files found but no matching tooling/configuration was detected.",
                    files=rel_files[:10],
                )
            )

        if area.key == "data":
            findings.extend(check_json_files(repo, rel_files))
        if run_tools:
            findings.append(run_tool(repo, area, rel_files, strict, command_overrides.get(area.key)))

    counts: dict[str, int] = {"PASS": 0, "WARN": 0, "SKIP": 0, "FAIL": 0}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1

    return {
        "repo": str(repo),
        "profile": context["profile"],
        "strict": strict,
        "run_tools": run_tools,
        "enabled_areas": sorted(enabled_areas) if enabled_areas is not None else "all",
        "counts": counts,
        "findings": [finding.__dict__ for finding in findings],
    }


def write_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Code Quality Standards Check",
        "",
        f"- Repo: `{report['repo']}`",
        f"- Profile: `{report['profile'] or 'unknown'}`",
        f"- Strict: `{report['strict']}`",
        f"- Run tools: `{report['run_tools']}`",
        f"- Enabled areas: `{report['enabled_areas']}`",
        "",
        "## Summary",
        "",
    ]
    for status in ("PASS", "WARN", "SKIP", "FAIL"):
        lines.append(f"- `{status}`: {report['counts'].get(status, 0)}")
    lines.extend(["", "## Findings", ""])
    for finding in report["findings"]:
        lines.append(f"- [{finding['status']}] {finding['message']}")
        if finding.get("tools"):
            lines.append(f"  Tools/config: `{', '.join(finding['tools'])}`")
        if finding.get("files"):
            sample = ", ".join(f"`{path}`" for path in finding["files"][:5])
            lines.append(f"  Files: {sample}")
        if finding.get("command"):
            lines.append(f"  Command: `{finding['command']}` -> `{finding.get('returncode')}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--run-tools", action="store_true")
    parser.add_argument(
        "--areas",
        help="Comma-separated area keys to check. Defaults to all areas.",
    )
    parser.add_argument("--python-lint-command", default="")
    parser.add_argument("--shell-lint-command", default="")
    parser.add_argument("--yaml-lint-command", default="")
    parser.add_argument("--markdown-check-command", default="")
    parser.add_argument("--docker-lint-command", default="")
    parser.add_argument("--make-lint-command", default="")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        raise SystemExit(f"Repo path is not a directory: {repo}")

    enabled_areas = None
    if args.areas:
        enabled_areas = {item.strip() for item in args.areas.split(",") if item.strip()}

    command_overrides = {
        "python": args.python_lint_command,
        "shell": args.shell_lint_command,
        "yaml": args.yaml_lint_command,
        "markdown": args.markdown_check_command,
        "docker": args.docker_lint_command,
        "make": args.make_lint_command,
    }
    report = analyze_repo(
        repo,
        strict=args.strict,
        run_tools=args.run_tools,
        enabled_areas=enabled_areas,
        command_overrides={key: value for key, value in command_overrides.items() if value},
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(write_markdown(report), end="")

    return 1 if report["counts"].get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
