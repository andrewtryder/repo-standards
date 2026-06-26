"""Detection wrappers and wizard module recommendations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import engine  # noqa: F401
from detect_repo_standard import detect_repo, recommended_templates


def detect_repository(repo: Path, standards: Path) -> dict[str, Any]:
    result = detect_repo(repo, standards)
    if is_home_assistant(repo):
        result["recommended_profile"] = "python-home-assistant"
        result["recommended_templates"] = recommended_templates("python-home-assistant")
    if has_firebase(repo, result):
        result["deployment_provider"] = "firebase"
    modules = recommend_modules(repo, result)
    return {**result, "modules": modules}


def is_home_assistant(repo: Path) -> bool:
    manifest_paths = list(repo.glob("custom_components/*/manifest.json"))
    return any(path.is_file() for path in manifest_paths)


def has_firebase(repo: Path, detection: dict[str, Any] | None = None) -> bool:
    if detection and detection.get("deployment_provider") == "firebase":
        return True
    if (repo / "firebase.json").is_file() or (repo / ".firebaserc").is_file():
        return True
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        for path in list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml")):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            if "firebase" in text or "firebase deploy" in text:
                return True
    return False


def package_private(repo: Path) -> bool | None:
    pkg = repo / "package.json"
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = data.get("private")
    return value if isinstance(value, bool) else None


def recommend_modules(repo: Path, detection: dict[str, Any]) -> list[str]:
    modules = ["core", "ai-agents"]
    language = detection.get("language")
    provider = detection.get("deployment_provider")

    if language == "python":
        modules.append("python")
    elif language == "typescript":
        modules.append("typescript-node")
    elif language == "mixed":
        modules.append("mixed-special")

    if is_home_assistant(repo):
        modules.append("home-assistant")
    if provider == "cloudflare":
        modules.append("cloudflare-worker")
    if provider == "gcp":
        modules.append("gcp")
    if provider == "railway":
        modules.append("railway")
    if has_firebase(repo, detection):
        modules.append("firebase")

    modules.extend(["github-actions", "pre-commit", "dependabot"])
    return list(dict.fromkeys(modules))


def quality_gates(detection: dict[str, Any]) -> list[str]:
    language = detection.get("language")
    if language == "python":
        return [
            "ruff format --check .",
            "ruff check .",
            "pytest",
            "coverage run -m pytest && coverage report",
        ]
    if language == "typescript":
        return [
            "npm run format:check",
            "npm run lint",
            "npm run typecheck",
            "npm test",
            "npm run test:coverage",
            "npm run build",
        ]
    return ["manual review required"]
