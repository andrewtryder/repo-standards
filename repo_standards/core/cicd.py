"""CI/CD workflow review and classification helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import engine  # noqa: F401
from apply_repo_standards import classify_all_workflows


KEEP_DEPLOY = "KEEP_DEPLOY"
KEEP_RELEASE = "KEEP_RELEASE"
REPLACE_STANDARD_CHECK = "REPLACE_STANDARD_CHECK"
REPLACE_DUPLICATE_RELEASE_PLEASE = "REPLACE_DUPLICATE_RELEASE_PLEASE"
REPLACE_DUPLICATE_SECRET_SCAN = "REPLACE_DUPLICATE_SECRET_SCAN"
REPLACE_DUPLICATE_DOCS_CHECK = "REPLACE_DUPLICATE_DOCS_CHECK"
REPLACE_DUPLICATE_AI_RULES_CHECK = "REPLACE_DUPLICATE_AI_RULES_CHECK"
UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"

CHECK_JOB_TERMS = (
    "npm ci",
    "npm install",
    "pnpm install",
    "yarn install",
    "bun install",
    "pip install",
    "lint",
    "eslint",
    "ruff",
    "typecheck",
    "tsc --noemit",
    "test",
    "pytest",
    "vitest",
    "jest",
    "coverage",
    "build",
    "prettier",
    "format",
)

OPERATIONAL_JOB_TERMS = (
    "deploy",
    "release",
    "publish",
    "firebase",
    "gcloud",
    "wrangler",
    "cloudflare",
    "railway",
    "docker push",
    "ghcr.io",
    "pages",
    "release-please",
    "hacs",
    "hassfest",
    "home-assistant/actions",
)


@dataclass(frozen=True)
class WorkflowReview:
    path: str
    classification: str
    reason: str
    matched_terms: list[str]
    deterministic_classification: str


@dataclass(frozen=True)
class MixedWorkflowCleanup:
    path: str
    can_update: bool
    removable_jobs: list[str]
    preserved_jobs: list[str]
    reason: str
    updated_text: str = ""


def map_workflow_classification(item: dict[str, Any]) -> str:
    path = str(item.get("path", ""))
    lower_path = path.lower()
    original = item.get("classification")
    matched_terms = set(item.get("matched_terms", []))

    if "codeql" in lower_path or "dependency-review" in lower_path:
        return UNKNOWN_REVIEW_REQUIRED
    if "release-please" in lower_path and any(
        term in item.get("matched_terms", [])
        for term in ("publish", "npm publish", "pages", "deploy-pages")
    ):
        return KEEP_RELEASE
    if "release-please" in lower_path:
        return REPLACE_DUPLICATE_RELEASE_PLEASE
    if "secret-scan" in lower_path:
        return REPLACE_DUPLICATE_SECRET_SCAN
    if "docs-check" in lower_path or "docs-ai-rule-sync" in lower_path:
        return REPLACE_DUPLICATE_DOCS_CHECK
    if "ai-rules" in lower_path:
        return REPLACE_DUPLICATE_AI_RULES_CHECK
    if original == "standards-owned":
        return REPLACE_STANDARD_CHECK
    if original in {"protected-release", "protected-publish"}:
        return KEEP_RELEASE
    if original in {"protected-deploy", "protected-pages", "protected-provider"}:
        return KEEP_DEPLOY
    if original == "mixed-operational":
        if matched_terms.intersection(
            {
                "cron:",
                "workflow_run",
                "contents: write",
                "secrets.",
                "git push",
                "git commit",
                "heartbeat",
                "newsletter",
                "resend",
            }
        ):
            return KEEP_DEPLOY
        return UNKNOWN_REVIEW_REQUIRED
    if original == "replaceable-check":
        return REPLACE_STANDARD_CHECK
    return UNKNOWN_REVIEW_REQUIRED


def _workflow_text(repo: Path, rel_path: str) -> str:
    path = repo / rel_path
    return path.read_text(encoding="utf-8", errors="ignore").lower() if path.is_file() else ""


def _has_operational_context(text: str) -> bool:
    terms = {
        "cron:",
        "schedule:",
        "workflow_run",
        "contents: write",
        "secrets.",
        "git push",
        "git commit",
        "heartbeat",
        "newsletter",
        "resend",
        "hacs/action",
        "hassfest",
        "home-assistant/actions",
    }
    return any(term in text for term in terms)


def _has_check_context(text: str) -> bool:
    return any(term in text for term in CHECK_JOB_TERMS)


def _has_home_assistant_validation_context(text: str) -> bool:
    return any(
        term in text
        for term in (
            "hacs/action",
            "hassfest",
            "home-assistant/actions",
        )
    )


def review_workflows(repo: Path) -> list[WorkflowReview]:
    reviews: list[WorkflowReview] = []
    for item in classify_all_workflows(repo):
        text = _workflow_text(repo, item["path"])
        classification = map_workflow_classification(item)
        deterministic_classification = item.get("classification", "unknown")
        if classification == REPLACE_STANDARD_CHECK and _has_operational_context(text):
            if _has_home_assistant_validation_context(text) and _has_check_context(text):
                classification = UNKNOWN_REVIEW_REQUIRED
                deterministic_classification = "mixed-operational"
            else:
                classification = KEEP_DEPLOY
        reviews.append(
            WorkflowReview(
                path=item["path"],
                classification=classification,
                reason=item.get("reason", ""),
                matched_terms=list(item.get("matched_terms", [])),
                deterministic_classification=deterministic_classification,
            )
        )
    return reviews


def preserved_deploy_workflows(reviews: list[WorkflowReview]) -> list[str]:
    return [
        item.path
        for item in reviews
        if item.classification in {KEEP_DEPLOY, KEEP_RELEASE, UNKNOWN_REVIEW_REQUIRED}
    ]


def standardizable_workflows(reviews: list[WorkflowReview]) -> list[str]:
    return [
        item.path
        for item in reviews
        if item.classification
        in {
            REPLACE_STANDARD_CHECK,
            REPLACE_DUPLICATE_RELEASE_PLEASE,
            REPLACE_DUPLICATE_SECRET_SCAN,
            REPLACE_DUPLICATE_DOCS_CHECK,
            REPLACE_DUPLICATE_AI_RULES_CHECK,
        }
    ]


def workflow_safe_summary(repo: Path, rel_path: str) -> dict[str, Any]:
    path = repo / rel_path
    text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    lowered = text.lower()
    name = ""
    match = re.search(r"(?m)^name:\s*(.+)$", text)
    if match:
        name = match.group(1).strip().strip("'\"")
    jobs = re.findall(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", text)
    steps = re.findall(r"(?m)^\s*-\s*(?:name|uses|run):\s*(.+)$", text)
    terms = [
        term
        for term in (
            "checkout",
            "setup-node",
            "setup-python",
            "npm",
            "pytest",
            "deploy",
            "publish",
            "firebase",
            "gcloud",
            "wrangler",
            "docker",
            "release-please",
        )
        if term in lowered
    ]
    return {
        "path": rel_path,
        "filename": Path(rel_path).name,
        "workflow_name": name,
        "detected_terms": terms,
        "jobs": jobs[:20],
        "steps_summary": [step.strip().strip("'\"")[:120] for step in steps[:30]],
    }


def mixed_workflows(reviews: list[WorkflowReview]) -> list[str]:
    return [
        item.path
        for item in reviews
        if item.deterministic_classification == "mixed-operational"
    ]


def plan_mixed_workflow_cleanup(repo: Path, rel_path: str) -> MixedWorkflowCleanup:
    try:
        import yaml
    except ImportError:
        return MixedWorkflowCleanup(
            path=rel_path,
            can_update=False,
            removable_jobs=[],
            preserved_jobs=[],
            reason="PyYAML is unavailable; cannot safely rewrite workflow YAML.",
        )

    path = repo / rel_path
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    try:
        data = yaml.load(text, Loader=_github_actions_yaml_loader())
    except yaml.YAMLError as exc:
        return MixedWorkflowCleanup(
            path=rel_path,
            can_update=False,
            removable_jobs=[],
            preserved_jobs=[],
            reason=f"Workflow YAML could not be parsed: {exc}",
        )

    if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
        return MixedWorkflowCleanup(
            path=rel_path,
            can_update=False,
            removable_jobs=[],
            preserved_jobs=[],
            reason="Workflow does not contain a jobs mapping.",
        )

    jobs = data["jobs"]
    removable: list[str] = []
    preserved: list[str] = []
    for job_name, job_spec in jobs.items():
        kind = classify_job(job_name, job_spec)
        if kind == "check":
            removable.append(str(job_name))
        else:
            preserved.append(str(job_name))

    if not removable:
        return MixedWorkflowCleanup(
            path=rel_path,
            can_update=False,
            removable_jobs=[],
            preserved_jobs=preserved,
            reason="No check-only jobs were identified for removal.",
        )
    if not preserved:
        return MixedWorkflowCleanup(
            path=rel_path,
            can_update=False,
            removable_jobs=removable,
            preserved_jobs=[],
            reason="All jobs look check-only; replace this workflow instead of trimming it.",
        )

    updated = dict(data)
    updated_jobs = {
        job_name: _drop_removed_needs(job_spec, set(removable))
        for job_name, job_spec in jobs.items()
        if str(job_name) not in removable
    }
    updated["jobs"] = updated_jobs
    rendered = yaml.safe_dump(updated, sort_keys=False)
    return MixedWorkflowCleanup(
        path=rel_path,
        can_update=True,
        removable_jobs=removable,
        preserved_jobs=preserved,
        reason="Remove check-only jobs; preserve deploy/release jobs.",
        updated_text=rendered,
    )


def classify_job(job_name: Any, job_spec: Any) -> str:
    text = f"{job_name}\n{job_spec}".lower()
    has_operational = any(term in text for term in OPERATIONAL_JOB_TERMS)
    has_check = any(term in text for term in CHECK_JOB_TERMS)
    if has_operational:
        return "operational"
    if has_check:
        return "check"
    return "ambiguous"


def _drop_removed_needs(job_spec: Any, removed: set[str]) -> Any:
    if not isinstance(job_spec, dict) or "needs" not in job_spec:
        return job_spec
    updated = dict(job_spec)
    needs = updated["needs"]
    if isinstance(needs, str):
        if needs in removed:
            updated.pop("needs", None)
        return updated
    if isinstance(needs, list):
        kept = [item for item in needs if str(item) not in removed]
        if kept:
            updated["needs"] = kept
        else:
            updated.pop("needs", None)
    return updated


def _github_actions_yaml_loader():
    import yaml

    class GitHubActionsLoader(yaml.SafeLoader):
        pass

    for first_letter, resolvers in list(GitHubActionsLoader.yaml_implicit_resolvers.items()):
        GitHubActionsLoader.yaml_implicit_resolvers[first_letter] = [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != "tag:yaml.org,2002:bool"
        ]
    return GitHubActionsLoader
