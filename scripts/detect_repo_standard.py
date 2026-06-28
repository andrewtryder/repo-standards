#!/usr/bin/env python3
"""Read-only advisory detector for repo-standards profiles and templates."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "htmlcov",
    "__pycache__",
}

CORE_TEMPLATES = [
    "templates/rulesync.jsonc",
    "ai/rules/*",
    "templates/workflows/semantic-pull-request.yml",
    "templates/workflows/ai-rules-check.yml",
    "templates/workflows/docs-check.yml",
    "templates/workflows/secret-scan.yml",
    "templates/dependabot.yml",
    "templates/CONTRIBUTING.md",
    "templates/.github/PULL_REQUEST_TEMPLATE.md",
]

PROFILE_POLICY_TEMPLATES = {
    "typescript-cloudflare-worker": "templates/repo-policy.typescript-cloudflare.yml",
    "typescript-app": "templates/repo-policy.typescript-app.yml",
    "typescript-library": "templates/repo-policy.typescript-library.yml",
    "python-service": "templates/repo-policy.python-service.yml",
    "python-home-assistant": "templates/repo-policy.python-home-assistant.yml",
    "mixed-special": "templates/repo-policy.mixed-special.yml",
}

TEXT_SCAN_PATHS = [
    "package.json",
    "README.md",
    "wrangler.toml",
    "wrangler.json",
    "wrangler.jsonc",
    "fly.toml",
    "railway.json",
    "cloudbuild.yaml",
    "cloudbuild.yml",
    "app.yaml",
    "pyproject.toml",
]

DEFAULT_RULES: dict[str, Any] = {
    "languages": {
        "typescript": {
            "evidence": [
                {"file": "package.json"},
                {
                    "file_any": [
                        "tsconfig.json",
                        "vite.config.ts",
                        "src/**/*.ts",
                        "src/**/*.tsx",
                    ]
                },
            ],
            "package_managers": {
                "npm": {"evidence": [{"file": "package-lock.json"}]},
                "pnpm": {"evidence": [{"file": "pnpm-lock.yaml"}]},
                "yarn": {"evidence": [{"file": "yarn.lock"}]},
                "bun": {"evidence": [{"file_any": ["bun.lock", "bun.lockb"]}]},
            },
        },
        "python": {
            "evidence": [
                {
                    "file_any": [
                        "pyproject.toml",
                        "requirements.txt",
                        "requirements-dev.txt",
                        "setup.py",
                        "setup.cfg",
                    ]
                },
                {"glob": "**/*.py"},
            ],
        },
    },
    "deploy": {
        "cloudflare": {
            "evidence": [
                {
                    "file_any": [
                        "wrangler.toml",
                        "wrangler.json",
                        "wrangler.jsonc",
                    ]
                },
                {
                    "contains": {
                        "paths": [
                            "package.json",
                            ".github/workflows/*.yml",
                            ".github/workflows/*.yaml",
                        ],
                        "terms": ["wrangler", "cloudflare"],
                    }
                },
            ]
        },
        "gcp": {
            "evidence": [
                {
                    "file_any": [
                        "cloudbuild.yaml",
                        "cloudbuild.yml",
                        "app.yaml",
                    ]
                },
                {
                    "contains": {
                        "paths": [
                            ".github/workflows/*.yml",
                            ".github/workflows/*.yaml",
                        ],
                        "terms": [
                            "gcloud",
                            "google-github-actions",
                            "cloud run",
                            "cloud functions",
                            "app engine",
                            "artifact registry",
                            "workload identity",
                        ],
                    }
                },
            ]
        },
        "railway": {
            "evidence": [
                {"file": "railway.json"},
                {
                    "contains": {
                        "paths": [
                            ".github/workflows/*.yml",
                            ".github/workflows/*.yaml",
                            "README.md",
                        ],
                        "terms": ["railway"],
                    }
                },
            ]
        },
        "fly": {
            "evidence": [
                {"file": "fly.toml"},
                {
                    "contains": {
                        "paths": [
                            ".github/workflows/*.yml",
                            ".github/workflows/*.yaml",
                            "README.md",
                        ],
                        "terms": ["flyctl", "fly.io", "fly deploy"],
                    }
                },
            ]
        },
    },
    "profiles": {
        "typescript-cloudflare-worker": {
            "when": {"language": "typescript", "deploy": "cloudflare"}
        },
        "typescript-app": {"when": {"language": "typescript"}},
        "python-service": {"when": {"language": "python"}},
        "mixed-special": {"when": {"language": "mixed"}},
    },
}


def load_rules(standards_root: Path) -> dict[str, Any]:
    rules_path = standards_root / "profiles" / "detection.yml"
    if not rules_path.is_file():
        return DEFAULT_RULES
    try:
        import yaml
    except ImportError:
        print(
            "Warning: PyYAML not installed; using built-in detection rules.",
            file=sys.stderr,
        )
        return DEFAULT_RULES
    with rules_path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    return loaded if isinstance(loaded, dict) else DEFAULT_RULES


def iter_repo_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        files.append(rel)
    return files


def path_exists(repo: Path, pattern: str, files: list[Path]) -> bool:
    if any(ch in pattern for ch in "*?[]"):
        return any(fnmatch.fnmatch(str(rel), pattern) for rel in files)
    return (repo / pattern).is_file()


def glob_exists(repo: Path, pattern: str, files: list[Path]) -> bool:
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        return any(
            fnmatch.fnmatch(str(rel), pattern)
            or fnmatch.fnmatch(rel.name, suffix)
            or str(rel).endswith(suffix.lstrip("/"))
            for rel in files
        )
    return any(fnmatch.fnmatch(str(rel), pattern) for rel in files)


def read_text_limited(path: Path, limit: int = 512_000) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > limit:
        data = data[:limit]
    return data.decode("utf-8", errors="ignore")


def expand_paths(repo: Path, pattern: str) -> list[Path]:
    if "*" in pattern:
        parent = pattern.rsplit("/", 1)[0] if "/" in pattern else "."
        glob_pattern = pattern.split("/", 1)[-1]
        base = repo / parent if parent != "." else repo
        if not base.exists():
            return []
        return [p for p in base.glob(glob_pattern) if p.is_file()]
    candidate = repo / pattern
    return [candidate] if candidate.is_file() else []


def contains_term(repo: Path, paths: list[str], terms: list[str]) -> list[str]:
    hits: list[str] = []
    lowered_terms = [t.lower() for t in terms]
    for path_pattern in paths:
        for file_path in expand_paths(repo, path_pattern):
            rel = file_path.relative_to(repo)
            content = read_text_limited(file_path).lower()
            for term in lowered_terms:
                if term in content:
                    hits.append(f"{rel} mentions {term}")
    return hits


def evaluate_evidence(
    repo: Path, evidence_items: list[Any], files: list[Path]
) -> list[str]:
    found: list[str] = []
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        if "file" in item:
            target = item["file"]
            if path_exists(repo, target, files):
                found.append(f"{target} exists")
        elif "file_any" in item:
            targets = item["file_any"]
            for target in targets:
                if path_exists(repo, target, files):
                    found.append(f"{target} exists")
                    break
        elif "glob" in item:
            pattern = item["glob"]
            if glob_exists(repo, pattern, files):
                found.append(f"matches glob {pattern}")
        elif "contains" in item:
            spec = item["contains"]
            path_patterns = spec.get("paths", [])
            terms = spec.get("terms", [])
            found.extend(contains_term(repo, path_patterns, terms))
    return found


def detect_language(
    repo: Path, rules: dict[str, Any], files: list[Path]
) -> tuple[str, list[str]]:
    language_rules = rules.get("languages", {})
    hits: dict[str, list[str]] = {}
    for language, spec in language_rules.items():
        evidence = spec.get("evidence", []) if isinstance(spec, dict) else []
        found = evaluate_evidence(repo, evidence, files)
        if found:
            hits[language] = found

    if "typescript" in hits and "python" in hits:
        return "mixed", hits["typescript"] + hits["python"]
    if "typescript" in hits:
        return "typescript", hits["typescript"]
    if "python" in hits:
        return "python", hits["python"]
    return "unknown", []


def detect_package_manager(
    repo: Path, language: str, rules: dict[str, Any], files: list[Path]
) -> tuple[str, list[str]]:
    if language == "typescript":
        pm_rules = (
            rules.get("languages", {})
            .get("typescript", {})
            .get("package_managers", {})
        )
        for manager, spec in pm_rules.items():
            evidence = spec.get("evidence", []) if isinstance(spec, dict) else []
            found = evaluate_evidence(repo, evidence, files)
            if found:
                return manager, found
        return "unknown", []

    if language in {"python", "mixed"}:
        evidence: list[str] = []
        if (repo / "uv.lock").is_file():
            evidence.append("uv.lock exists")
            return "uv", evidence
        if (repo / "poetry.lock").is_file():
            evidence.append("poetry.lock exists")
            return "poetry", evidence
        pyproject = read_text_limited(repo / "pyproject.toml").lower()
        if "poetry" in pyproject and (repo / "pyproject.toml").is_file():
            evidence.append("pyproject.toml mentions poetry")
            return "poetry", evidence
        for req in ("requirements.txt", "requirements-dev.txt"):
            if (repo / req).is_file():
                evidence.append(f"{req} exists")
                return "pip-requirements", evidence

    return "unknown", []


def detect_deploy(
    repo: Path, rules: dict[str, Any], files: list[Path]
) -> tuple[str, list[str]]:
    deploy_rules = rules.get("deploy", {})
    matches: list[tuple[str, list[str]]] = []
    for provider, spec in deploy_rules.items():
        evidence = spec.get("evidence", []) if isinstance(spec, dict) else []
        found = evaluate_evidence(repo, evidence, files)
        if found:
            matches.append((provider, found))

    if not matches:
        return "none", []

    if len(matches) == 1:
        return matches[0]

    # Prefer strongest signal: file-based evidence over content-only
    ranked = sorted(matches, key=lambda item: len(item[1]), reverse=True)
    provider, found = ranked[0]
    combined = found + [
        f"multiple deploy providers detected; selected {provider}"
    ]
    return provider, combined


def recommend_profile(
    language: str, deployment_provider: str, rules: dict[str, Any]
) -> str:
    profile_rules = rules.get("profiles", {})
    candidates: list[str] = []
    for profile, spec in profile_rules.items():
        when = spec.get("when", {}) if isinstance(spec, dict) else {}
        lang_ok = when.get("language") == language
        deploy = when.get("deploy")
        if deploy is not None:
            if lang_ok and deployment_provider == deploy:
                candidates.append(profile)
        elif lang_ok:
            candidates.append(profile)

    priority = [
        "typescript-cloudflare-worker",
        "typescript-library",
        "typescript-app",
        "python-home-assistant",
        "python-service",
        "mixed-special",
    ]
    for profile in priority:
        if profile in candidates:
            return profile

    if language == "typescript" and deployment_provider == "cloudflare":
        return "typescript-cloudflare-worker"
    if language == "typescript":
        return "typescript-app"
    if language == "python":
        return "python-service"
    return "mixed-special"


def is_typescript_library(repo: Path, files: list[Path]) -> bool:
    pkg = repo / "package.json"
    if not pkg.is_file():
        return False
    content = read_text_limited(pkg).lower()
    if '"private": true' in content or '"private":true' in content:
        return False
    if re.search(r'"name"\s*:\s*"@[^/]+/', content):
        return True
    if '"main"' in content or '"exports"' in content or '"module"' in content:
        if "wrangler" not in content:
            return True
    return False


def compute_confidence(language: str, evidence: list[str], profile: str) -> float:
    if language == "unknown":
        return 0.35
    base = 0.55
    base += min(0.35, 0.05 * len(evidence))
    if profile != "mixed-special":
        base += 0.1
    return round(min(base, 0.98), 2)


def manual_review_notes(
    language: str,
    deployment_provider: str,
    profile: str,
    deploy_evidence: list[str],
) -> list[str]:
    notes: list[str] = []
    if language == "unknown" or profile == "mixed-special":
        notes.append("Could not confidently detect language/profile")
    if deployment_provider in {"cloudflare", "gcp", "railway", "fly"}:
        notes.append("Verify deploy workflow should remain repo-specific")
    if "multiple deploy providers detected" in " ".join(deploy_evidence):
        notes.append("Review deploy provider — multiple signals detected")
    notes.append("Confirm `.repo-policy.yml` before adopting the standard")
    return sorted(set(notes))


def recommended_templates(profile: str) -> list[str]:
    policy = PROFILE_POLICY_TEMPLATES.get(
        profile, PROFILE_POLICY_TEMPLATES["mixed-special"]
    )
    templates = [policy, *CORE_TEMPLATES]
    return sorted(set(templates))


def detect_repo(repo: Path, standards_root: Path) -> dict[str, Any]:
    repo = repo.resolve()
    rules = load_rules(standards_root)
    files = iter_repo_files(repo)

    language, lang_evidence = detect_language(repo, rules, files)
    package_manager, pm_evidence = detect_package_manager(
        repo, language, rules, files
    )
    deployment_provider, deploy_evidence = detect_deploy(repo, rules, files)

    profile = recommend_profile(language, deployment_provider, rules)
    if (
        language == "typescript"
        and deployment_provider != "cloudflare"
        and is_typescript_library(repo, files)
    ):
        profile = "typescript-library"

    evidence = sorted(
        set(lang_evidence + pm_evidence + deploy_evidence),
        key=str.lower,
    )
    confidence = compute_confidence(language, evidence, profile)
    manual_review = manual_review_notes(
        language, deployment_provider, profile, deploy_evidence
    )

    return {
        "language": language,
        "package_manager": package_manager,
        "deployment_provider": deployment_provider,
        "recommended_profile": profile,
        "confidence": confidence,
        "evidence": evidence,
        "recommended_templates": recommended_templates(profile),
        "manual_review": manual_review,
    }


def format_markdown(repo: Path, result: dict[str, Any]) -> str:
    lines = [
        "# Repo standard detection",
        "",
        f"Repo: `{repo.resolve()}`",
        "",
        "## Recommendation",
        "",
        f"- Recommended profile: `{result['recommended_profile']}`",
        f"- Language: `{result['language']}`",
        f"- Package manager: `{result['package_manager']}`",
        f"- Deployment provider: `{result['deployment_provider']}`",
        f"- Confidence: `{result['confidence']}`",
        "",
        "## Evidence",
        "",
    ]
    if result["evidence"]:
        lines.extend(f"- {item}" for item in result["evidence"])
    else:
        lines.append("- No strong evidence found")

    lines.extend(["", "## Recommended templates", ""])
    lines.extend(f"- `{item}`" for item in result["recommended_templates"])

    lines.extend(["", "## Manual review", ""])
    lines.extend(f"- {item}" for item in result["manual_review"])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only advisory detector for repo-standards profiles."
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=Path,
        help="Path to the target repository",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--standards",
        type=Path,
        default=None,
        help="Path to repo-standards root (default: parent of scripts/)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo
    if not repo.is_dir():
        print(f"Error: --repo must be an existing directory: {repo}", file=sys.stderr)
        return 1

    standards_root = args.standards or Path(__file__).resolve().parent.parent
    result = detect_repo(repo, standards_root)

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_markdown(repo, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
