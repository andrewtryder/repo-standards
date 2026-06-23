#!/usr/bin/env python3
"""
assess_repo_standards_migration_v2.py

Stricter post-migration assessment for a single repository adopting Repo Standards v1.

Adds checks that v1 missed:
- Generated coverage artifacts in the diff.
- Agent memory files in the diff.
- Suspicious non-dot `agents/` directory.
- Rulesync output that appears to write only AGENTS.md despite claiming Cursor/Antigravity support.
- npm audit vulnerability count as a warning.
- ESLint warnings count as a warning.
- Coverage below report-only baseline as a warning, not a blocker.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENERATED_ARTIFACT_RE = re.compile(
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

COVERAGE_ALL_FILES_RE = re.compile(
    r"All files\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)"
)

ESLINT_PROBLEMS_RE = re.compile(r"✖\s+(\d+)\s+problems?\s+\((\d+)\s+errors?,\s+(\d+)\s+warnings?\)")

NPM_AUDIT_RE = re.compile(r"(\d+)\s+vulnerabilities\s+\(([^)]+)\)")


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


def exists(repo: Path, rel: str) -> bool:
    return (repo / rel).exists()


def changed_files(repo: Path, base_ref: str | None) -> list[str]:
    files: set[str] = set()

    status = run(["git", "status", "--porcelain"], repo, timeout=30)
    if status["ok"]:
        for line in status["stdout"].splitlines():
            if not line.strip():
                continue
            rel = line[3:].strip()
            if " -> " in rel:
                rel = rel.split(" -> ", 1)[1]
            files.add(rel.rstrip("/"))

    if base_ref:
        diff = run(["git", "diff", "--name-only", f"{base_ref}...HEAD"], repo, timeout=30)
        if diff["ok"]:
            for line in diff["stdout"].splitlines():
                if line.strip():
                    files.add(line.strip().rstrip("/"))

    return sorted(files)


def package_state(repo: Path) -> dict[str, Any]:
    package = read_json(repo / "package.json") if exists(repo, "package.json") else {}
    scripts = package.get("scripts") or {}

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
        "scripts": scripts,
        "has_rulesync_dependency": "rulesync" in deps,
        "has_commitlint_dependency": "@commitlint/cli" in deps or "commitlint" in deps,
        "has_husky": "husky" in deps or exists(repo, ".husky"),
        "has_lint_staged": "lint-staged" in deps or "lint-staged" in package,
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
    rulesync = read_text(repo / "rulesync.jsonc") if exists(repo, "rulesync.jsonc") else ""
    rules_dir = repo / ".rulesync" / "rules"

    rule_files = []
    if rules_dir.exists():
        rule_files = sorted(p.relative_to(repo).as_posix() for p in rules_dir.rglob("*") if p.is_file())

    return {
        "has_repo_policy": exists(repo, ".repo-policy.yml"),
        "has_rulesync_config": exists(repo, "rulesync.jsonc"),
        "has_rulesync_rules_dir": rules_dir.exists(),
        "has_agents_md": exists(repo, "AGENTS.md"),
        "has_cursor_rules": exists(repo, ".cursor") or exists(repo, ".cursorrules"),
        "has_antigravity_rules": exists(repo, ".agents"),
        "rulesync_mentions_agentsmd": "agentsmd" in rulesync.lower() or "agents" in rulesync.lower(),
        "rulesync_mentions_cursor": "cursor" in rulesync.lower(),
        "rulesync_mentions_antigravity": "antigravity" in rulesync.lower(),
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
    rulesync_stdout = ""

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

        if "test:coverage" in c["cmd"]:
            m = COVERAGE_ALL_FILES_RE.search(out)
            if m:
                coverage = {
                    "statements": float(m.group(1)),
                    "branches": float(m.group(2)),
                    "functions": float(m.group(3)),
                    "lines": float(m.group(4)),
                }

        if "rulesync" in c["cmd"]:
            rulesync_stdout = c.get("stdout", "")

    return {
        "eslint_errors": eslint_errors,
        "eslint_warnings": eslint_warnings,
        "npm_vulnerabilities": npm_vulnerabilities,
        "npm_vulnerability_detail": npm_vulnerability_detail,
        "coverage": coverage,
        "rulesync_stdout": rulesync_stdout,
        "rulesync_only_agents_md": bool(rulesync_stdout)
        and "AGENTS.md" in rulesync_stdout
        and ".cursor" not in rulesync_stdout
        and ".agents" not in rulesync_stdout,
    }


def score_report(state: dict[str, Any], command_analysis: dict[str, Any], commands: list[dict[str, Any]]) -> tuple[int, list[str], list[str]]:
    score = 100
    blockers: list[str] = []
    warnings: list[str] = []

    ai = state["ai"]
    wf = state["workflows"]
    pkg = state["package"]
    docs = state["docs"]
    changed = state["changed"]

    required = [
        ("Missing .repo-policy.yml", ai["has_repo_policy"]),
        ("Missing rulesync.jsonc", ai["has_rulesync_config"]),
        ("Missing .rulesync/rules directory", ai["has_rulesync_rules_dir"]),
        ("Missing AGENTS.md", ai["has_agents_md"]),
        ("Missing Cursor rules output", ai["has_cursor_rules"]),
        ("Missing Antigravity rules output", ai["has_antigravity_rules"]),
        ("Missing AI rules sync workflow", wf["has_ai_rules_workflow"]),
        ("Missing semantic PR / conventional commit enforcement", wf["has_semantic_pr_workflow"]),
        ("Missing README.md", docs["has_readme"]),
    ]

    for msg, ok in required:
        if not ok:
            score -= 8
            blockers.append(msg)

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
        if not pkg["has_rulesync_dependency"]:
            warnings.append("rulesync is not pinned as a devDependency; acceptable initially, but pin later")

    if changed["generated_artifacts"]:
        score -= 12
        blockers.append("Generated coverage/build artifacts are in the diff; remove them or add/update .gitignore")
    if changed["agent_memories"]:
        score -= 8
        blockers.append(".agents/memories is in the diff; agent memory should not be committed")
    if changed["suspicious_agents_paths"]:
        score -= 6
        warnings.append("Suspicious non-dot `agents/` path detected; confirm it is intentional")
    if changed["secretish_files"]:
        score -= 20
        blockers.append("Secret-like files appear changed or untracked")
    if changed["risky_deploy_files"]:
        warnings.append("Deploy/release files changed; manually verify this was intentional")

    if command_analysis["eslint_warnings"]:
        warnings.append(f"ESLint passed but reported {command_analysis['eslint_warnings']} warnings")
    if command_analysis["npm_vulnerabilities"]:
        warnings.append(
            f"npm audit reported {command_analysis['npm_vulnerabilities']} vulnerabilities ({command_analysis['npm_vulnerability_detail']})"
        )
    if command_analysis["coverage"]:
        cov = command_analysis["coverage"]
        if cov["lines"] < 50:
            warnings.append(f"Coverage is very low: {cov['lines']}% lines, {cov['branches']}% branches; keep report-only")
    elif wf["mentions_coverage"]:
        warnings.append("Coverage workflow/script detected, but coverage summary was not parsed")

    if command_analysis["rulesync_only_agents_md"] and ai["rulesync_mentions_cursor"] and ai["rulesync_mentions_antigravity"]:
        warnings.append("Rulesync output only mentioned AGENTS.md; verify `.cursor` and `.agents` are generated by current config, not stale files")

    if not docs["readme_mentions_checks"]:
        score -= 3
        warnings.append("README does not appear to document checks")
    if not docs["readme_mentions_deploy_or_release"]:
        warnings.append("README does not appear to document deploy/release behavior")
    if not docs["readme_mentions_ai"]:
        warnings.append("README does not mention AI/editor instructions")

    if any(not c["ok"] for c in commands):
        score = max(0, score - 10)
        blockers.append("One or more safe verification commands failed")

    return max(score, 0), sorted(set(blockers)), sorted(set(warnings))


def make_recommendations(state: dict[str, Any], command_analysis: dict[str, Any]) -> tuple[list[str], list[str]]:
    recs: list[str] = []
    feedback: list[str] = []

    changed = state["changed"]
    wf = state["workflows"]

    if changed["generated_artifacts"]:
        recs.append("Remove generated coverage/build artifacts from the PR and add `coverage/` to `.gitignore` if missing.")
    if changed["agent_memories"]:
        recs.append("Remove `.agents/memories/` from the PR and add `.agents/memories/` to `.gitignore`.")
    if changed["suspicious_agents_paths"]:
        recs.append("Inspect `agents/` without a leading dot; move/remove it unless a tool explicitly requires that path.")
    if command_analysis["rulesync_only_agents_md"]:
        recs.append("Verify Rulesync target config: current output mentions only `AGENTS.md`, not `.cursor` or `.agents`.")
    if command_analysis["coverage"] and command_analysis["coverage"]["lines"] < 50:
        recs.append("Keep coverage as report-only for this repo; do not add a threshold until coverage is improved.")
    if command_analysis["eslint_warnings"]:
        recs.append("Track existing ESLint warnings as technical debt; do not fix them in the standards PR unless trivial.")
    if command_analysis["npm_vulnerabilities"]:
        recs.append("Open a separate dependency-audit PR; do not mix audit fixes into the standards PR.")
    if not wf["has_release_please"]:
        recs.append("If this repo ships releases, add Release Please in a follow-up PR.")

    if changed["generated_artifacts"]:
        feedback.append("Update repo-standards to explicitly forbid committing generated coverage artifacts in standards PRs.")
    if changed["agent_memories"]:
        feedback.append("Update repo-standards to explicitly forbid committing `.agents/memories/`.")
    if changed["suspicious_agents_paths"]:
        feedback.append("Clarify in repo-standards that Antigravity rules belong under `.agents/`, not `agents/`, unless a repo has a specific exception.")
    if command_analysis["rulesync_only_agents_md"]:
        feedback.append("Update the Rulesync template or docs if Cursor/Antigravity files are not actually generated by the current template.")
    if not feedback:
        feedback.append("No repo-standards blueprint changes suggested by this stricter assessment.")

    return recs, feedback


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# {report['repo']['name']} Standards Migration Assessment v2")
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
    files = changed_files(repo, base_ref)
    state = {
        "package": package_state(repo),
        "workflows": workflows_state(repo),
        "ai": ai_state(repo),
        "docs": docs_state(repo),
        "changed": {
            "files": files,
            "generated_artifacts": [f for f in files if GENERATED_ARTIFACT_RE.search(f)],
            "agent_memories": [f for f in files if AGENT_MEMORY_RE.search(f)],
            "suspicious_agents_paths": [f for f in files if SUSPICIOUS_AGENTS_RE.search(f)],
            "risky_deploy_files": [f for f in files if DEPLOY_RE.search(f)],
            "secretish_files": [f for f in files if SECRETISH_RE.search(f)],
        },
    }

    commands = []
    if run_safe_checks:
        for cmd in safe_commands(repo, state["package"], state["ai"]):
            timeout = 300 if cmd[0] in {"npm", "pnpm", "yarn"} else 120
            commands.append(run(cmd, repo, timeout=timeout))

    command_analysis = analyze_command_outputs(commands)
    score, blockers, warnings = score_report(state, command_analysis, commands)
    recs, feedback = make_recommendations(state, command_analysis)

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

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else standards / "assessments"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = assess(repo, standards, args.base_ref, args.run_safe_checks)

    md_path = output_dir / f"{repo.name}.standards-assessment-v2.md"
    json_path = output_dir / f"{repo.name}.standards-assessment-v2.json"

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
