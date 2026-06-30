"""Shared helpers for Release Please workflow adoption."""

from __future__ import annotations

import re
from pathlib import Path

RELEASE_PLEASE_WORKFLOW_REL = ".github/workflows/release-please.yml"

DEFAULT_CHANGELOG = """# Changelog

## [Unreleased]

"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def parse_release_please_enabled(policy_text: str) -> bool | None:
    if not policy_text.strip():
        return None
    match = re.search(r"(?m)^\s*release_please:\s*(true|false)\b", policy_text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def parse_release_strategy(policy_text: str) -> str | None:
    if not policy_text.strip():
        return None
    match = re.search(
        r"(?m)^release:\s*\n(?:(?!^\S)[^\n]*\n)*?^\s+strategy:\s*(\S+)",
        policy_text,
        re.MULTILINE,
    )
    if match:
        return match.group(1).strip().lower()
    return None


def has_release_please_workflow(repo: Path) -> bool:
    workflows = repo / ".github" / "workflows"
    if not workflows.is_dir():
        return False
    return any(
        path.is_file() and "release-please" in path.name.lower()
        for path in workflows.iterdir()
    )


def is_publishable_node_package(repo: Path) -> bool:
    package_json = repo / "package.json"
    if not package_json.is_file():
        return False
    text = read_text(package_json)
    if '"private": true' in text.replace(" ", ""):
        return False
    return '"version"' in text


def release_please_template_path(
    standards: Path,
    repo: Path,
    *,
    selected_profile: str,
    language: str | None,
    policy_text: str,
) -> Path:
    workflows = standards / "templates" / "workflows"
    if (repo / "release-please-config.json").is_file() or (
        repo / ".release-please-manifest.json"
    ).is_file():
        return workflows / "release-please.manifest.yml"

    strategy = parse_release_strategy(policy_text)
    if strategy == "node":
        return workflows / "release-please.node.yml"
    if strategy == "manifest":
        return workflows / "release-please.manifest.yml"

    if selected_profile in {"typescript-library", "typescript-cloudflare-worker"}:
        return workflows / "release-please.node.yml"
    if selected_profile == "mixed-special":
        if (repo / "release-please-config.json").is_file() or (
            repo / ".release-please-manifest.json"
        ).is_file():
            return workflows / "release-please.manifest.yml"
        return workflows / "release-please.simple.yml"
    if language == "typescript" and is_publishable_node_package(repo):
        return workflows / "release-please.node.yml"
    return workflows / "release-please.simple.yml"


def release_please_enabled_for_repo(
    repo: Path,
    standards: Path,
    *,
    selected_profile: str,
    rendered_policy: str | None,
) -> bool:
    for policy_text in (
        rendered_policy or "",
        read_text(repo / ".repo-policy.yml"),
        read_text(standards / "templates" / f"repo-policy.{selected_profile}.yml"),
    ):
        enabled = parse_release_please_enabled(policy_text)
        if enabled is not None:
            return enabled
    return False


def uses_simple_release_template(template_path: Path) -> bool:
    return template_path.name == "release-please.simple.yml"
