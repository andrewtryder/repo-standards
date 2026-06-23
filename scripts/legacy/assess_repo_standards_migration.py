#!/usr/bin/env python3
"""
assess_repo_standards_migration.py

Assess one repository against Repo Standards v1 (superseded by v3).

Example:
  python3 /path/to/repo-standards/scripts/assess_repo_standards_migration.py \
    --repo /path/to/example-repo \
    --standards /path/to/repo-standards \
    --base-ref main \
    --run-safe-checks

Outputs:
  <standards>/assessments/<repo>.standards-assessment.md
  <standards>/assessments/<repo>.standards-assessment.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_FILES = [
    ".repo-policy.yml",
    "rulesync.jsonc",
    ".rulesync/rules/00-org.md",
    ".rulesync/rules/10-repo.md",
    ".rulesync/rules/20-quality-gates.md",
    ".rulesync/rules/30-deploy.md",
    "AGENTS.md",
]

AI_OUTPUTS = ["AGENTS.md", ".cursor", ".agents"]

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
            files.add(rel)

    if base_ref:
        diff = run(["git", "diff", "--name-only", f"{base_ref}...HEAD"], repo, timeout=30)
        if diff["ok"]:
            for line in diff["stdout"].splitlines():
                if line.strip():
                    files.add(line.strip())

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


def python_state(repo: Path) -> dict[str, Any]:
    pyproject = read_text(repo / "pyproject.toml") if exists(repo, "pyproject.toml") else ""
    return {
        "has_pyproject": exists(repo, "pyproject.toml"),
        "has_requirements": exists(repo, "requirements.txt"),
        "has_pre_commit": exists(repo, ".pre-commit-config.yaml") or exists(repo, ".pre-commit-config.yml"),
        "has_ruff_config": exists(repo, "ruff.toml") or exists(repo, ".ruff.toml") or "ruff" in pyproject.lower(),
        "mentions_pytest": "pytest" in pyproject.lower() or exists(repo, "pytest.ini"),
        "mentions_coverage": "coverage" in pyproject.lower() or "pytest-cov" in pyproject.lower(),
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


def score_report(state: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    score = 100
    blockers: list[str] = []
    warnings: list[str] = []

    ai = state["ai"]
    wf = state["workflows"]
    pkg = state["package"]
    py = state["python"]
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

    if py["has_pyproject"] or py["has_requirements"]:
        if not py["has_ruff_config"]:
            score -= 4
            warnings.append("Python area does not appear to use Ruff")
        if not py["mentions_pytest"]:
            score -= 4
            warnings.append("Python area does not appear to use pytest")

    if not wf["mentions_coverage"]:
        warnings.append("Coverage not detected in workflows; acceptable if still report-only")
    if not docs["readme_mentions_checks"]:
        score -= 3
        warnings.append("README does not appear to document checks")
    if not docs["readme_mentions_deploy_or_release"]:
        warnings.append("README does not appear to document deploy/release behavior")
    if not docs["readme_mentions_ai"]:
        warnings.append("README does not mention AI/editor instructions")

    if changed["secretish_files"]:
        score -= 20
        blockers.append("Secret-like files appear changed or untracked")
    if changed["risky_deploy_files"]:
        warnings.append("Deploy/release files changed; manually verify this was intentional")

    return max(score, 0), sorted(set(blockers)), sorted(set(warnings))


def make_recommendations(state: dict[str, Any]) -> tuple[list[str], list[str]]:
    recs: list[str] = []
    feedback: list[str] = []

    ai = state["ai"]
    wf = state["workflows"]
    pkg = state["package"]
    changed = state["changed"]

    if not ai["has_repo_policy"]:
        recs.append("Add `.repo-policy.yml` from the TypeScript Cloudflare template and tailor commands.")
    if not ai["has_rulesync_config"]:
        recs.append("Add `rulesync.jsonc` from the standards template.")
    if not ai["has_rulesync_rules_dir"]:
        recs.append("Add `.rulesync/rules/*` as the canonical AI/editor source.")
    if not all([ai["has_agents_md"], ai["has_cursor_rules"], ai["has_antigravity_rules"]]):
        recs.append("Run Rulesync and commit generated `AGENTS.md`, `.cursor/rules`, and `.agents/rules`.")
    if not wf["has_ai_rules_workflow"]:
        recs.append("Add AI rules drift-check workflow.")
    if not wf["has_semantic_pr_workflow"]:
        recs.append("Add semantic pull request title workflow.")
    if not wf["has_release_please"]:
        recs.append("If this repo ships releases, add or normalize Release Please in a follow-up PR.")
    if changed["risky_deploy_files"]:
        recs.append("Review deploy/release workflow changes. First standards PR should usually avoid deploy changes.")

    if wf["has_release_please"] and not any("release-please" in f for f in wf["files"]):
        feedback.append("Release Please exists but the workflow filename is non-standard; decide whether to allow that in the blueprint.")
    if pkg["package_manager"] and not str(pkg["package_manager"]).startswith("npm"):
        feedback.append(f"Repo uses `{pkg['package_manager']}`; blueprint should preserve repo-local package managers.")
    if changed["risky_deploy_files"]:
        feedback.append("If deploy files frequently change during first migrations, split deploy guidance into a separate migration phase.")
    if not feedback:
        feedback.append("No repo-standards blueprint changes suggested by this assessment.")

    return recs, feedback


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# {report['repo']['name']} Standards Migration Assessment")
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

    for section, data in [
        ("AI/editor rules", report["state"]["ai"]),
        ("Workflows", report["state"]["workflows"]),
        ("Package state", {k: v for k, v in report["state"]["package"].items() if k != "scripts"}),
        ("Python state", report["state"]["python"]),
        ("Docs", report["state"]["docs"]),
    ]:
        lines.append("")
        lines.append(f"## {section}")
        lines.append("")
        for k, v in data.items():
            lines.append(f"- `{k}`: `{v}`")

    scripts = report["state"]["package"].get("scripts") or {}
    if scripts:
        lines.append("")
        lines.append("## Package scripts")
        lines.append("")
        for name in sorted(scripts):
            lines.append(f"- `{name}`: `{scripts[name]}`")

    lines.append("")
    lines.append("## Changed files")
    lines.append("")
    changed = report["state"]["changed"]["files"]
    if changed:
        risky = set(report["state"]["changed"]["risky_deploy_files"])
        for f in changed:
            marker = " ⚠️ deploy/release-related" if f in risky else ""
            lines.append(f"- `{f}`{marker}")
    else:
        lines.append("- No changed files detected")

    lines.append("")
    lines.append("## Command results")
    lines.append("")
    if report["commands"]:
        for r in report["commands"]:
            status = "PASS" if r["ok"] else "FAIL"
            lines.append(f"### {status}: `{r['cmd']}`")
            if r["stdout"]:
                lines.append("")
                lines.append("```txt")
                lines.append(r["stdout"][-3000:])
                lines.append("```")
            if r["stderr"]:
                lines.append("")
                lines.append("```txt")
                lines.append(r["stderr"][-3000:])
                lines.append("```")
            lines.append("")
    else:
        lines.append("- No commands run. Use `--run-safe-checks` to execute local checks.")

    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    lines.extend([f"- {x}" for x in report["recommendations"]] or ["- None"])

    lines.append("")
    lines.append("## Standards feedback")
    lines.append("")
    lines.extend([f"- {x}" for x in report["standards_feedback"]] or ["- None"])

    path.write_text("\n".join(lines), encoding="utf-8")


def assess(repo: Path, standards: Path, base_ref: str | None, run_safe_checks: bool) -> dict[str, Any]:
    changed = changed_files(repo, base_ref)
    state = {
        "package": package_state(repo),
        "python": python_state(repo),
        "workflows": workflows_state(repo),
        "ai": ai_state(repo),
        "docs": docs_state(repo),
        "changed": {
            "files": changed,
            "risky_deploy_files": [f for f in changed if DEPLOY_RE.search(f)],
            "secretish_files": [f for f in changed if SECRETISH_RE.search(f)],
        },
    }

    commands = []
    if run_safe_checks:
        for cmd in safe_commands(repo, state["package"], state["ai"]):
            timeout = 300 if cmd[0] in {"npm", "pnpm", "yarn"} else 120
            commands.append(run(cmd, repo, timeout=timeout))

    score, blockers, warnings = score_report(state)
    if any(not c["ok"] for c in commands):
        score = max(0, score - 10)
        blockers.append("One or more safe verification commands failed")

    recs, feedback = make_recommendations(state)

    if blockers:
        verdict = "Not ready to merge. Address blockers first."
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
        "score": {"value": score, "blockers": sorted(set(blockers)), "warnings": warnings},
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

    md_path = output_dir / f"{repo.name}.standards-assessment.md"
    json_path = output_dir / f"{repo.name}.standards-assessment.json"

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
