"""Shared helpers for Python pip dev requirements files."""

from __future__ import annotations

import re
from pathlib import Path

PYTHON_DEV_REQUIREMENT_FILES = (
    "requirements-dev.txt",
    "requirements-test.txt",
    "requirements_test.txt",
    "dev-requirements.txt",
)

DEFAULT_PYTHON_DEV_REQUIREMENTS = ("pytest", "coverage", "ruff")

_PRIMARY_DEV_FILE = "requirements-dev.txt"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def parse_requirement_package_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("-"):
        return None
    name = re.split(r"[<>=!;\[]", stripped, maxsplit=1)[0].strip()
    return name.lower().replace("_", "-") if name else None


def requirement_names_in_text(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        parsed = parse_requirement_package_name(line)
        if parsed:
            names.add(parsed)
    return names


def primary_python_dev_requirements_path(repo: Path) -> Path | None:
    preferred = repo / _PRIMARY_DEV_FILE
    if preferred.is_file():
        return preferred
    for name in PYTHON_DEV_REQUIREMENT_FILES:
        if name == _PRIMARY_DEV_FILE:
            continue
        path = repo / name
        if path.is_file():
            return path
    return None


def has_python_dev_requirements(repo: Path) -> bool:
    return primary_python_dev_requirements_path(repo) is not None


def extra_python_dev_requirements(repo: Path) -> list[str]:
    runtime_text = (
        read_text(repo / "requirements.txt").lower()
        if (repo / "requirements.txt").is_file()
        else ""
    )
    extras: list[str] = []
    if "fastapi" in runtime_text:
        extras.append("httpx")
    return extras


def missing_python_dev_packages(repo: Path, dev_path: Path | None = None) -> list[str]:
    path = dev_path or primary_python_dev_requirements_path(repo)
    if path is None:
        return list(DEFAULT_PYTHON_DEV_REQUIREMENTS) + extra_python_dev_requirements(repo)

    present = requirement_names_in_text(read_text(path))
    missing: list[str] = []
    for pkg in DEFAULT_PYTHON_DEV_REQUIREMENTS:
        if pkg not in present:
            missing.append(pkg)
    for pkg in extra_python_dev_requirements(repo):
        if pkg not in present:
            missing.append(pkg)
    return missing


def python_dev_requirements_content(repo: Path) -> str:
    requirements = list(DEFAULT_PYTHON_DEV_REQUIREMENTS) + extra_python_dev_requirements(repo)
    return "\n".join(requirements) + "\n"


def merge_python_dev_requirements_text(existing: str, missing: list[str]) -> str:
    if not missing:
        return existing if existing.endswith("\n") else existing + "\n"
    text = existing.rstrip("\n")
    text += "\n\n# Dev tooling expected by repo-standards\n"
    text += "\n".join(missing) + "\n"
    return text
