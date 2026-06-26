"""Persistent state for the Textual migration wizard."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


STATE_FILE = ".repo-standards-migration-state.json"

Visibility = Literal["public", "private"]
License = Literal["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "proprietary", "none", "other"]


@dataclass
class GovernanceAnswers:
    visibility: Visibility = "private"
    license: License = "proprietary"
    multi_developer: bool = True
    public_contributors: bool = False
    github_pages_docs: bool = False
    user_facing_docs: bool = False
    issue_templates: bool = False
    pr_template: bool = True
    security_policy: bool = True
    codeowners_recommended: bool = True


@dataclass
class WizardState:
    repo: str = ""
    standards: str = ""
    mode: Literal["existing", "new"] = "existing"
    base_ref: str = "main"
    phase: str = "welcome"
    governance: GovernanceAnswers = field(default_factory=GovernanceAnswers)
    detection: dict[str, Any] = field(default_factory=dict)
    modules: list[str] = field(default_factory=list)
    ai_files: list[str] = field(default_factory=list)
    ai_cleanup_confirmed: bool = False
    cicd_standardization_confirmed: bool = False
    mixed_workflow_cleanup_confirmed: bool = False
    install_precommit_confirmed: bool = False
    add_precommit_config: bool = True
    run_rulesync: bool = True
    run_assessment: bool = True
    workflow_review: list[dict[str, Any]] = field(default_factory=list)
    ai_advisory: dict[str, Any] = field(default_factory=dict)
    deploy_workflows_preserved: list[str] = field(default_factory=list)

    @property
    def repo_path(self) -> Path:
        return Path(self.repo).expanduser().resolve()

    @property
    def standards_path(self) -> Path:
        return Path(self.standards).expanduser().resolve()


def state_path(repo: Path) -> Path:
    return repo / STATE_FILE


def _decode_governance(data: dict[str, Any]) -> GovernanceAnswers:
    values = data.get("governance", data)
    if not isinstance(values, dict):
        values = {}
    fields = GovernanceAnswers.__dataclass_fields__
    filtered = {key: values[key] for key in fields if key in values}
    return GovernanceAnswers(**filtered)


def load_state(repo: Path) -> WizardState | None:
    path = state_path(repo)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid wizard state: {path}")
    fields = WizardState.__dataclass_fields__
    filtered = {key: data[key] for key in fields if key in data}
    filtered["governance"] = _decode_governance(data)
    return WizardState(**filtered)


def save_state(state: WizardState) -> Path:
    repo = state.repo_path
    repo.mkdir(parents=True, exist_ok=True)
    path = state_path(repo)
    path.write_text(
        json.dumps(asdict(state), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
