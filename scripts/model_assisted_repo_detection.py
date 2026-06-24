#!/usr/bin/env python3
"""Optional GitHub Models-assisted advisory classifier for repo detection."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from detect_repo_standard import detect_repo  # noqa: E402

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".venv",
    ".venv-docs",
    "venv",
    "htmlcov",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

SENSITIVE_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
    "*secret*",
    "*credential*",
    "*token*",
]

ALLOWED_PROFILES = {
    "typescript-library",
    "typescript-cloudflare-worker",
    "typescript-app",
    "python-service",
    "python-home-assistant",
    "mixed-special",
}

WORKFLOW_TERMS = [
    "wrangler",
    "cloudflare",
    "gcloud",
    "google-github-actions",
    "cloud run",
    "cloud functions",
    "artifact registry",
    "railway",
    "docker",
    "release-please",
    "pages",
    "firebase",
    "vercel",
    "fly",
]

DEPLOY_INDICATOR_FILES = [
    "wrangler.toml",
    "wrangler.json",
    "wrangler.jsonc",
    "railway.json",
    "cloudbuild.yaml",
    "cloudbuild.yml",
    "app.yaml",
    "fly.toml",
    "vercel.json",
    "firebase.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
]

FILE_INDICATOR_PATTERNS = [
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "tsconfig.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
    "uv.lock",
    "poetry.lock",
    ".repo-policy.yml",
    "rulesync.jsonc",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
]

MAX_SUMMARY_JSON = 12000
MAX_PACKAGE_SCRIPTS = 30
MAX_WORKFLOW_SIGNALS = 50
MAX_README_HEADINGS = 30
MAX_FILE_INDICATORS = 200

DEFAULT_MODEL = "openai/gpt-4o-mini"
API_URL = "https://models.github.ai/inference/chat/completions"


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
    for env_path in (
        standards_root / ".env",
        Path.cwd() / ".env",
        repo / ".env",
    ):
        load_dotenv(env_path)


def get_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def is_sensitive(name: str) -> bool:
    lowered = name.lower()
    basename = Path(name).name.lower()
    for pattern in SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(lowered, pattern):
            return True
    return False


def iter_repo_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if is_sensitive(str(rel)):
            continue
        files.append(rel)
    return files


def read_text_limited(path: Path, limit: int = 256_000) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > limit:
        data = data[:limit]
    return data.decode("utf-8", errors="ignore")


def collect_file_indicators(repo: Path, files: list[Path]) -> list[str]:
    indicators: list[str] = []
    for pattern in FILE_INDICATOR_PATTERNS:
        if (repo / pattern).is_file():
            indicators.append(pattern)
    source_prefixes = ("scripts/", "src/", "lib/", "tests/", "test/", "app/")
    for rel in files:
        rel_str = str(rel)
        if rel.suffix == ".py" and rel_str.startswith(source_prefixes):
            if rel_str not in indicators:
                indicators.append(rel_str)
        if rel.suffix in (".ts", ".tsx") and "src" in rel.parts:
            if rel_str not in indicators:
                indicators.append(rel_str)
        if len(indicators) >= MAX_FILE_INDICATORS:
            break
    return sorted(set(indicators))[:MAX_FILE_INDICATORS]


def collect_package_json(repo: Path) -> dict[str, Any]:
    pkg_path = repo / "package.json"
    if not pkg_path.is_file() or is_sensitive("package.json"):
        return {}
    try:
        data = json.loads(read_text_limited(pkg_path, 64_000))
    except json.JSONDecodeError:
        return {"parse_error": "invalid JSON"}
    if not isinstance(data, dict):
        return {}

    result: dict[str, Any] = {}
    for key in ("type", "private", "main", "module", "exports", "engines"):
        if key in data:
            result[key] = data[key]

    scripts = data.get("scripts")
    if isinstance(scripts, dict):
        script_names = sorted(scripts.keys())[:MAX_PACKAGE_SCRIPTS]
        result["scripts"] = {name: scripts[name] for name in script_names}

    for dep_key in ("dependencies", "devDependencies"):
        deps = data.get(dep_key)
        if isinstance(deps, dict):
            result[dep_key] = sorted(deps.keys())

    return result


def collect_python_indicators(repo: Path) -> list[str]:
    indicators: list[str] = []
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        indicators.append("pyproject.toml")
        content = read_text_limited(pyproject, 64_000)
        for match in re.finditer(r"^\[tool\.([^\]]+)\]", content, re.MULTILINE):
            tool_name = match.group(1).strip()
            entry = f"tool.{tool_name}"
            if entry not in indicators:
                indicators.append(entry)
    for name in (
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        "uv.lock",
        "poetry.lock",
    ):
        if (repo / name).is_file():
            indicators.append(name)
    return indicators


def collect_workflow_signals(repo: Path) -> list[str]:
    signals: list[str] = []
    workflows_dir = repo / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return signals

    for path in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        if not path.is_file() or is_sensitive(path.name):
            continue
        rel = path.relative_to(repo)
        content = read_text_limited(path, 128_000).lower()
        hits = [term for term in WORKFLOW_TERMS if term in content]
        if hits:
            signals.append(f"{rel}: {', '.join(hits)}")
        else:
            signals.append(str(rel))
        if len(signals) >= MAX_WORKFLOW_SIGNALS:
            break
    return signals[:MAX_WORKFLOW_SIGNALS]


def collect_deploy_indicators(repo: Path) -> list[str]:
    found: list[str] = []
    for name in DEPLOY_INDICATOR_FILES:
        if (repo / name).is_file():
            found.append(name)
    return found


def collect_readme_headings(repo: Path) -> list[str]:
    readme = repo / "README.md"
    if not readme.is_file():
        return []
    headings: list[str] = []
    for line in read_text_limited(readme, 64_000).splitlines():
        match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append(f"{'#' * level} {text}")
        if len(headings) >= MAX_README_HEADINGS:
            break
    return headings


def build_safe_summary(repo: Path, deterministic: dict[str, Any]) -> dict[str, Any]:
    files = iter_repo_files(repo)
    summary: dict[str, Any] = {
        "file_indicators": collect_file_indicators(repo, files),
        "package_json_scripts": collect_package_json(repo),
        "python_indicators": collect_python_indicators(repo),
        "workflow_signals": collect_workflow_signals(repo),
        "deploy_indicators": collect_deploy_indicators(repo),
        "readme_headings": collect_readme_headings(repo),
        "deterministic_detection": {
            "language": deterministic.get("language"),
            "package_manager": deterministic.get("package_manager"),
            "deployment_provider": deterministic.get("deployment_provider"),
            "recommended_profile": deterministic.get("recommended_profile"),
            "confidence": deterministic.get("confidence"),
            "evidence": deterministic.get("evidence", [])[:30],
        },
    }

    encoded = json.dumps(summary, indent=2, sort_keys=True)
    if len(encoded) > MAX_SUMMARY_JSON:
        while len(encoded) > MAX_SUMMARY_JSON and summary["file_indicators"]:
            summary["file_indicators"].pop()
            encoded = json.dumps(summary, indent=2, sort_keys=True)
        if len(encoded) > MAX_SUMMARY_JSON:
            evidence = summary["deterministic_detection"].get("evidence", [])
            while len(encoded) > MAX_SUMMARY_JSON and evidence:
                evidence.pop()
                encoded = json.dumps(summary, indent=2, sort_keys=True)
        if len(encoded) > MAX_SUMMARY_JSON:
            summary["summary_truncated"] = True
    return summary


def load_prompt(standards_root: Path) -> str:
    prompt_path = standards_root / "prompts" / "repo-detection-advisor.prompt.md"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def call_github_models(
    *,
    token: str,
    model: str,
    system_prompt: str,
    user_content: str,
    timeout: float,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
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
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"GitHub Models API request failed with status {exc.code}: {body_text}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub Models API request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub Models API returned non-JSON response") from exc

    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("GitHub Models API response missing choices")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("GitHub Models API response missing message content")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model response is not valid JSON: {content[:200]}"
        ) from exc


def validate_model_advice(
    advice: dict[str, Any],
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    validated: dict[str, Any] = {
        "repo_kind": str(advice.get("repo_kind", "unknown")),
        "recommended_profile": advice.get("recommended_profile", ""),
        "confidence": advice.get("confidence", 0.0),
        "reasoning_summary": str(advice.get("reasoning_summary", "")),
        "manual_review": [],
        "warnings": [],
    }

    profile = validated["recommended_profile"]
    if profile not in ALLOWED_PROFILES:
        det_profile = deterministic.get("recommended_profile", "mixed-special")
        validated["recommended_profile"] = det_profile
        validated["warnings"].append(
            "Model returned invalid profile; using deterministic recommendation."
        )

    confidence = validated["confidence"]
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        validated["confidence"] = 0.0
        validated["warnings"].append("Model returned invalid confidence; set to 0.0.")

    for key in ("manual_review", "warnings"):
        value = advice.get(key, [])
        if isinstance(value, list):
            validated[key] = [str(item) for item in value]
        elif value:
            validated[key] = [str(value)]

    return validated


def build_final_recommendation(
    deterministic: dict[str, Any],
    model_advice: dict[str, Any] | None,
) -> dict[str, Any]:
    det_profile = deterministic.get("recommended_profile", "mixed-special")
    if model_advice is None:
        return {
            "recommended_profile": det_profile,
            "source": "deterministic_only",
            "requires_human_review": True,
        }

    model_profile = model_advice.get("recommended_profile", det_profile)
    if model_profile == det_profile:
        return {
            "recommended_profile": det_profile,
            "source": "deterministic_and_model_agree",
            "requires_human_review": True,
        }

    warnings = list(model_advice.get("warnings", []))
    warnings.append(
        f"Model recommended `{model_profile}` but deterministic detector "
        f"recommends `{det_profile}`; using deterministic recommendation."
    )
    model_advice["warnings"] = warnings

    return {
        "recommended_profile": det_profile,
        "source": "deterministic_preferred_model_disagrees",
        "requires_human_review": True,
    }


def build_output(
    repo: Path,
    deterministic: dict[str, Any],
    model_advice: dict[str, Any] | None,
    safe_summary: dict[str, Any] | None,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    det_subset = {
        "language": deterministic.get("language"),
        "package_manager": deterministic.get("package_manager"),
        "deployment_provider": deterministic.get("deployment_provider"),
        "recommended_profile": deterministic.get("recommended_profile"),
        "confidence": deterministic.get("confidence"),
    }
    output: dict[str, Any] = {
        "deterministic": det_subset,
        "final_recommendation": build_final_recommendation(deterministic, model_advice),
    }
    if dry_run:
        output["safe_summary"] = safe_summary or {}
    else:
        output["model_advice"] = model_advice or {}
    return output


def format_markdown(repo: Path, output: dict[str, Any], *, dry_run: bool) -> str:
    det = output["deterministic"]
    final = output["final_recommendation"]
    lines = [
        "# Model-assisted repo detection",
        "",
        f"Repo: `{repo.resolve()}`",
        "",
        "## Deterministic detection",
        "",
        f"- Recommended profile: `{det.get('recommended_profile')}`",
        f"- Language: `{det.get('language')}`",
        f"- Package manager: `{det.get('package_manager')}`",
        f"- Deployment provider: `{det.get('deployment_provider')}`",
        f"- Confidence: `{det.get('confidence')}`",
        "",
    ]

    if dry_run:
        lines.extend(
            [
                "## Safe summary (dry run)",
                "",
                "The following summary would be sent to the model. "
                "No API call was made.",
                "",
                "```json",
                json.dumps(output.get("safe_summary", {}), indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    else:
        advice = output.get("model_advice", {})
        lines.extend(
            [
                "## Model advice",
                "",
                f"- Repo kind: `{advice.get('repo_kind', 'n/a')}`",
                f"- Recommended profile: `{advice.get('recommended_profile', 'n/a')}`",
                f"- Confidence: `{advice.get('confidence', 'n/a')}`",
                "",
            ]
        )
        summary = advice.get("reasoning_summary", "")
        if summary:
            lines.extend([summary, ""])

        warnings = advice.get("warnings", [])
        if warnings:
            lines.extend(["### Warnings", ""])
            lines.extend(f"- {item}" for item in warnings)
            lines.append("")

        manual = advice.get("manual_review", [])
        if manual:
            lines.extend(["## Manual review", ""])
            lines.extend(f"- {item}" for item in manual)
            lines.append("")

    lines.extend(
        [
            "## Final recommendation",
            "",
            f"- Profile: `{final.get('recommended_profile')}`",
            f"- Source: `{final.get('source')}`",
            f"- Requires human review: `{final.get('requires_human_review')}`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Optional GitHub Models-assisted advisory classifier for repo detection. "
            "Read-only; does not modify the target repository."
        )
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
        help="Path to repo-standards root",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"GitHub Models model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--dry-run-summary",
        action="store_true",
        help="Print safe summary and deterministic result without API call",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: 30)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    standards_root = args.standards.resolve()

    if not repo.is_dir():
        print(f"Error: --repo must be an existing directory: {repo}", file=sys.stderr)
        return 1
    if not standards_root.is_dir():
        print(
            f"Error: --standards must be an existing directory: {standards_root}",
            file=sys.stderr,
        )
        return 1

    load_env_files(standards_root, repo)
    deterministic = detect_repo(repo, standards_root)
    safe_summary = build_safe_summary(repo, deterministic)

    model_advice: dict[str, Any] | None = None
    if args.dry_run_summary:
        model_advice = None
    else:
        token = get_token()
        if not token:
            print(
                "Error: GITHUB_TOKEN or GH_TOKEN is required for model-assisted "
                "detection. Use --dry-run-summary to preview without a token.",
                file=sys.stderr,
            )
            return 1
        try:
            system_prompt = load_prompt(standards_root)
            user_content = json.dumps(safe_summary, indent=2, sort_keys=True)
            raw_advice = call_github_models(
                token=token,
                model=args.model,
                system_prompt=system_prompt,
                user_content=user_content,
                timeout=args.timeout,
            )
            if not isinstance(raw_advice, dict):
                print("Error: Model response must be a JSON object.", file=sys.stderr)
                return 1
            model_advice = validate_model_advice(raw_advice, deterministic)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            message = str(exc)
            print(f"Error: {message}", file=sys.stderr)
            if "status 404" in message or "model" in message.lower():
                print(
                    f"Hint: Model `{args.model}` may be unavailable. "
                    "Pass a different model ID with --model.",
                    file=sys.stderr,
                )
            return 1

    output = build_output(
        repo,
        deterministic,
        model_advice,
        safe_summary,
        dry_run=args.dry_run_summary,
    )

    if args.format == "json":
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(format_markdown(repo, output, dry_run=args.dry_run_summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
