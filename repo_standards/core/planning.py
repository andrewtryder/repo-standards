"""Wizard planning and apply orchestration."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from . import engine  # noqa: F401
from .ai_files import discover_ai_files
from .cicd import review_workflows, standardizable_workflows
from .cicd import mixed_workflows, plan_mixed_workflow_cleanup
from .state import WizardState, save_state
from apply_repo_standards import (
    Action,
    apply_actions,
    build_plan,
    check_rulesync_outputs,
    format_summary_markdown,
    reusable_ci_workflow_for,
    resolve_policy_fields,
    run_assessment,
    run_rulesync,
)


WizardActionType = Literal[
    "CREATE",
    "DELETE",
    "REPLACE",
    "UPDATE",
    "MERGE",
    "KEEP",
    "WARN",
    "BLOCK",
]


PRECOMMIT_CONFIG = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
"""


@dataclass(frozen=True)
class WizardAction:
    action: WizardActionType
    path: str
    detail: str = ""


@dataclass
class WizardPlan:
    state: WizardState
    engine_summary: Any
    actions: list[WizardAction] = field(default_factory=list)

    def by_type(self, action_type: WizardActionType) -> list[WizardAction]:
        return [action for action in self.actions if action.action == action_type]

    @property
    def blocked(self) -> bool:
        return bool(self.by_type("BLOCK"))


def _workflow_strategy(state: WizardState) -> str:
    if state.cicd_standardization_confirmed and _can_generate_reusable_ci(state):
        return "reusable"
    return "reusable" if state.mode == "new" else "copied"


def _adoption_level(state: WizardState) -> str:
    if state.cicd_standardization_confirmed and _can_generate_reusable_ci(state):
        return "checks"
    return "baseline"


def _can_generate_reusable_ci(state: WizardState) -> bool:
    return reusable_ci_workflow_for(state.repo_path, state.detection) is not None


def _engine_action_to_wizard(action: Action) -> WizardAction:
    action_type = action.action
    if action_type == "SKIP":
        return WizardAction("KEEP", action.path, action.detail)
    if action_type in {"CREATE", "UPDATE", "MERGE", "WARN", "BLOCK"}:
        return WizardAction(action_type, action.path, action.detail)
    return WizardAction("WARN", action.path, action.detail)


def build_wizard_plan(state: WizardState, *, for_apply: bool = False) -> WizardPlan:
    repo = state.repo_path
    standards = state.standards_path
    policy_fields = resolve_policy_fields(
        repo,
        state.mode,
        state.governance.visibility,
        None if state.governance.license == "other" else state.governance.license,
    )
    summary = build_plan(
        repo,
        standards,
        mode=state.mode,
        profile=state.detection.get("recommended_profile") or None,
        workflow_strategy=_workflow_strategy(state),
        rules_strategy="profile",
        adoption_level=_adoption_level(state),
        update_existing=state.cicd_standardization_confirmed,
        force=False,
        allow_generated_output_rewrite=state.ai_cleanup_confirmed,
        cleanup_generated_artifacts=False,
        replace_check_workflows=state.cicd_standardization_confirmed,
        migrate_existing_agent_rules=False,
        for_apply=for_apply,
        will_run_rulesync=state.run_rulesync,
        policy_fields=policy_fields,
        format_touched=False,
        format_existing_docs=False,
        add_license=False,
    )
    summary.interactive = True
    summary.confirmed_decisions.extend(_confirmed_decisions(state))
    actions = [_engine_action_to_wizard(action) for action in summary.actions]

    actions.extend(_ai_cleanup_actions(state))
    actions.extend(_workflow_review_actions(state))
    actions.extend(_precommit_actions(state))

    if state.governance.codeowners_recommended:
        actions.append(WizardAction("WARN", ".github/CODEOWNERS", "CODEOWNERS recommended."))
    if state.governance.security_policy:
        actions.append(WizardAction("WARN", "SECURITY.md", "Security policy recommended."))

    return WizardPlan(state=state, engine_summary=summary, actions=actions)


def _confirmed_decisions(state: WizardState) -> list[str]:
    decisions = [
        f"Mode: {state.mode}",
        f"Visibility: {state.governance.visibility}",
        f"License: {state.governance.license}",
    ]
    if state.ai_cleanup_confirmed:
        decisions.append("AI cleanup confirmation: replace-ai-files")
    if state.cicd_standardization_confirmed:
        decisions.append("CI standardization confirmation: standardize-ci")
    if state.mixed_workflow_cleanup_confirmed:
        decisions.append("Mixed workflow cleanup confirmation: split-mixed-workflows")
    if state.install_precommit_confirmed:
        decisions.append("Install local pre-commit hooks")
    return decisions


def _ai_cleanup_actions(state: WizardState) -> list[WizardAction]:
    repo = state.repo_path
    found = discover_ai_files(repo)
    if not found:
        return []
    if not state.ai_cleanup_confirmed:
        return [
            WizardAction(
                "BLOCK",
                item.path,
                'AI/editor file cleanup requires typing "replace-ai-files".',
            )
            for item in found
        ]
    return [
        WizardAction("DELETE", item.path, "Remove before regenerating from Rulesync.")
        for item in found
    ]


def _workflow_review_actions(state: WizardState) -> list[WizardAction]:
    reviews = review_workflows(state.repo_path)
    can_generate_reusable_ci = _can_generate_reusable_ci(state)
    actions: list[WizardAction] = []
    for review in reviews:
        if review.path in standardizable_workflows(reviews):
            if state.cicd_standardization_confirmed and can_generate_reusable_ci:
                actions.append(
                    WizardAction("REPLACE", review.path, f"{review.classification}: {review.reason}")
                )
            else:
                actions.append(
                    WizardAction(
                        "WARN",
                        review.path,
                        f"{review.classification}: replacement requires standardize-ci and reusable CI support.",
                    )
                )
        else:
            if (
                review.path in mixed_workflows(reviews)
                and review.classification == "UNKNOWN_REVIEW_REQUIRED"
            ):
                cleanup = plan_mixed_workflow_cleanup(state.repo_path, review.path)
                if state.mixed_workflow_cleanup_confirmed and cleanup.can_update:
                    actions.append(
                        WizardAction(
                            "UPDATE",
                            review.path,
                            "Remove check-only jobs now covered by repo-standards CI: "
                            + ", ".join(cleanup.removable_jobs),
                        )
                    )
                elif cleanup.can_update:
                    actions.append(
                        WizardAction(
                            "WARN",
                            review.path,
                            'Mixed workflow can be trimmed after typing "split-mixed-workflows"; '
                            f"candidate jobs: {', '.join(cleanup.removable_jobs)}.",
                        )
                    )
                else:
                    actions.append(
                        WizardAction(
                            "KEEP",
                            review.path,
                            f"{review.classification}: {cleanup.reason}",
                        )
                    )
            else:
                actions.append(
                    WizardAction("KEEP", review.path, f"{review.classification}: {review.reason}")
                )
    return actions


def _precommit_actions(state: WizardState) -> list[WizardAction]:
    if not state.add_precommit_config:
        return []
    target = state.repo_path / ".pre-commit-config.yaml"
    if target.is_file():
        return [WizardAction("KEEP", ".pre-commit-config.yaml", "Existing pre-commit config preserved.")]
    return [WizardAction("CREATE", ".pre-commit-config.yaml", "Recommended quality gate hooks.")]


def action_groups(plan: WizardPlan) -> dict[str, list[WizardAction]]:
    order = ("CREATE", "DELETE", "REPLACE", "UPDATE", "MERGE", "KEEP", "WARN", "BLOCK")
    return {kind: plan.by_type(kind) for kind in order}


def write_precommit_config(repo: Path) -> None:
    target = repo / ".pre-commit-config.yaml"
    if not target.exists():
        target.write_text(PRECOMMIT_CONFIG, encoding="utf-8")


def apply_wizard_plan(plan: WizardPlan) -> tuple[WizardPlan, int]:
    state = plan.state
    repo = state.repo_path
    standards = state.standards_path
    if plan.blocked:
        return plan, 1

    state.phase = "applying"
    save_state(state)

    for action in plan.by_type("DELETE"):
        target = repo / action.path
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    apply_actions(plan.engine_summary, standards, repo)
    apply_wizard_replacements(plan, standards, repo)
    apply_mixed_workflow_cleanup(plan, repo)
    if state.add_precommit_config:
        write_precommit_config(repo)
    if state.install_precommit_confirmed:
        subprocess.run(["pre-commit", "install"], cwd=repo, check=False)

    if state.run_rulesync:
        plan.engine_summary.rulesync_ran = True
        ok, output = run_rulesync(repo)
        plan.engine_summary.rulesync_output = output
        plan.engine_summary.rulesync_result = "passed" if ok else "failed"
        if ok:
            check_rulesync_outputs(plan.engine_summary, repo)
        else:
            plan.engine_summary.actions.append(Action("BLOCK", "rulesync", "Rulesync failed."))
            plan.actions.append(WizardAction("BLOCK", "rulesync", "Rulesync failed."))

    if state.run_assessment:
        plan.engine_summary.assessment_ran = True
        code, output = run_assessment(repo, standards)
        plan.engine_summary.assessment_detail = output
        plan.engine_summary.assessment_result = "passed" if code == 0 else f"exit {code}"

    summary_path = repo / ".repo-standards-migration-summary.md"
    summary_path.write_text(format_summary_markdown(plan.engine_summary), encoding="utf-8")

    state.phase = "complete"
    save_state(state)
    return plan, 0 if not plan.by_type("BLOCK") else 1


def apply_wizard_replacements(plan: WizardPlan, standards: Path, repo: Path) -> None:
    for action in plan.by_type("REPLACE"):
        target = repo / action.path
        target.parent.mkdir(parents=True, exist_ok=True)
        name = Path(action.path).name

        if action.path == ".github/workflows/ci.yml":
            content = reusable_ci_workflow_for(repo, plan.engine_summary.detection)
            if content is not None:
                target.write_text(content, encoding="utf-8")
            continue

        if name == "release-please.yml":
            language = plan.engine_summary.detection.get("language")
            if (repo / "release-please-config.json").is_file() or (
                repo / ".release-please-manifest.json"
            ).is_file():
                template = standards / "templates" / "workflows" / "release-please.manifest.yml"
            elif language == "typescript":
                template = standards / "templates" / "workflows" / "release-please.node.yml"
            else:
                template = standards / "templates" / "workflows" / "release-please.simple.yml"
            if template.is_file():
                target.write_bytes(template.read_bytes())
            continue

        template = standards / "templates" / "workflows" / name
        if template.is_file():
            target.write_bytes(template.read_bytes())


def apply_mixed_workflow_cleanup(plan: WizardPlan, repo: Path) -> None:
    if not plan.state.mixed_workflow_cleanup_confirmed:
        return
    for rel_path in mixed_workflows(review_workflows(repo)):
        cleanup = plan_mixed_workflow_cleanup(repo, rel_path)
        if cleanup.can_update:
            (repo / rel_path).write_text(cleanup.updated_text, encoding="utf-8")
