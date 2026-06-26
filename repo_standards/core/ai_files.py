"""Discovery of existing AI/editor instruction files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AI_FILE_CANDIDATES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    ".cursor",
    ".agents",
    ".antigravity",
)

CANONICAL_SOURCES = (
    ".repo-policy.yml",
    "rulesync.jsonc",
    ".rulesync/rules/*.md",
)

GENERATED_OUTPUTS = (
    "AGENTS.md",
    ".cursor/rules/*.mdc",
    ".agents/rules/*.md",
    ".agents/memories/*.md",
)


@dataclass(frozen=True)
class AiFile:
    path: str
    kind: str
    standard: bool


def discover_ai_files(repo: Path) -> list[AiFile]:
    files: list[AiFile] = []
    for rel in AI_FILE_CANDIDATES:
        path = repo / rel
        if path.exists():
            kind = "directory" if path.is_dir() else "file"
            standard = rel in {"AGENTS.md", ".cursor", ".agents"}
            files.append(AiFile(rel, kind, standard))
    return files


def cleanup_paths(repo: Path) -> list[Path]:
    return [repo / item.path for item in discover_ai_files(repo)]

