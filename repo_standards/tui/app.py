"""Textual application for guided repo-standards migrations."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

from repo_standards.core.ai_files import CANONICAL_SOURCES, GENERATED_OUTPUTS, discover_ai_files
from repo_standards.core.ai_inference import classify_workflow_summary
from repo_standards.core.cicd import (
    UNKNOWN_REVIEW_REQUIRED,
    preserved_deploy_workflows,
    review_workflows,
    workflow_safe_summary,
)
from repo_standards.core.detection import detect_repository, quality_gates
from repo_standards.core.planning import action_groups, apply_wizard_plan, build_wizard_plan
from repo_standards.core.state import GovernanceAnswers, WizardState, load_state, save_state


class WizardScreen(Screen):
    """Base class with a typed app helper."""

    @property
    def wizard(self) -> "RepoStandardsWizardApp":
        return self.app  # type: ignore[return-value]

    def next(self, name: str) -> None:
        self.wizard.state.phase = name
        self.wizard.persist()
        self.app.push_screen(name)


class WelcomeScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Repo Standards Migration Wizard", classes="title")
            yield Static("Migrate one repository at a time with explicit review gates.")
            yield Static("Target repository")
            yield Input(value=self.wizard.state.repo, id="repo")
            yield Static("Repo standards checkout")
            yield Input(value=self.wizard.state.standards, id="standards")
            yield Static("Mode: existing or new")
            yield Input(value=self.wizard.state.mode, id="mode")
            yield Static("Base ref")
            yield Input(value=self.wizard.state.base_ref, id="base_ref")
            yield Static("", id="error")
            yield Button("Validate And Continue", id="continue", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "continue":
            return
        repo = Path(self.query_one("#repo", Input).value).expanduser().resolve()
        standards = Path(self.query_one("#standards", Input).value).expanduser().resolve()
        mode = self.query_one("#mode", Input).value.strip()
        base_ref = self.query_one("#base_ref", Input).value.strip() or "main"
        error = self.query_one("#error", Static)
        if not repo.is_dir():
            error.update(f"Repository path does not exist: {repo}")
            return
        if not standards.is_dir():
            error.update(f"Standards path does not exist: {standards}")
            return
        if not (repo / ".git").exists():
            error.update("Target repository must be a git repository.")
            return
        if mode not in {"existing", "new"}:
            error.update('Mode must be "existing" or "new".')
            return
        existing = load_state(repo)
        if existing:
            self.wizard.state = existing
        self.wizard.state.repo = str(repo)
        self.wizard.state.standards = str(standards)
        self.wizard.state.mode = mode  # type: ignore[assignment]
        self.wizard.state.base_ref = base_ref
        self.next("governance")


class GovernanceScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        gov = self.wizard.state.governance
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Project Governance", classes="title")
            yield Static("Visibility")
            yield Input(value=gov.visibility, id="visibility")
            yield Static("License: MIT, Apache-2.0, BSD-3-Clause, ISC, proprietary, none, or other")
            yield Input(value=gov.license, id="license")
            yield Checkbox("More than one developer", value=gov.multi_developer, id="multi")
            yield Checkbox("Public contributors expected", value=gov.public_contributors, id="contributors")
            yield Checkbox("GitHub Pages/docs site needed", value=gov.github_pages_docs, id="pages")
            yield Checkbox("User-facing docs needed", value=gov.user_facing_docs, id="docs")
            yield Checkbox("Public issue templates needed", value=gov.issue_templates, id="issues")
            yield Checkbox("Public PR template needed", value=gov.pr_template, id="pr")
            yield Checkbox("SECURITY.md needed", value=gov.security_policy, id="security")
            yield Checkbox("CODEOWNERS recommended", value=gov.codeowners_recommended, id="codeowners")
            yield Static("", id="error")
            yield Button("Run Detection", id="continue", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "continue":
            return
        visibility = self.query_one("#visibility", Input).value.strip()
        license_value = self.query_one("#license", Input).value.strip()
        error = self.query_one("#error", Static)
        if visibility not in {"public", "private"}:
            error.update('Visibility must be "public" or "private".')
            return
        if license_value not in {
            "MIT",
            "Apache-2.0",
            "BSD-3-Clause",
            "ISC",
            "proprietary",
            "none",
            "other",
        }:
            error.update(
                'License must be "MIT", "Apache-2.0", "BSD-3-Clause", '
                '"ISC", "proprietary", "none", or "other".'
            )
            return
        self.wizard.state.governance = GovernanceAnswers(
            visibility=visibility,  # type: ignore[arg-type]
            license=license_value,  # type: ignore[arg-type]
            multi_developer=self.query_one("#multi", Checkbox).value,
            public_contributors=self.query_one("#contributors", Checkbox).value,
            github_pages_docs=self.query_one("#pages", Checkbox).value,
            user_facing_docs=self.query_one("#docs", Checkbox).value,
            issue_templates=self.query_one("#issues", Checkbox).value,
            pr_template=self.query_one("#pr", Checkbox).value,
            security_policy=self.query_one("#security", Checkbox).value,
            codeowners_recommended=self.query_one("#codeowners", Checkbox).value,
        )
        self.wizard.state.detection = detect_repository(
            self.wizard.state.repo_path,
            self.wizard.state.standards_path,
        )
        self.wizard.state.modules = list(self.wizard.state.detection.get("modules", []))
        self.next("detection")


class DetectionScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        detection = self.wizard.state.detection
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Language And Platform Detection", classes="title")
            yield Static(_format_detection(detection))
            yield Button("Review AI-Agent Files", id="continue", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.next("ai_cleanup")


class AiCleanupScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        files = discover_ai_files(self.wizard.state.repo_path)
        self.wizard.state.ai_files = [item.path for item in files]
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("AI-Agent Standardization", classes="title")
            yield Static(_list_block("Existing files/directories", [item.path for item in files] or ["none"]))
            yield Static(_list_block("Canonical source after migration", CANONICAL_SOURCES))
            yield Static(_list_block("Generated outputs after Rulesync", GENERATED_OUTPUTS))
            yield Static('Type "replace-ai-files" to plan removal/replacement.')
            yield Input(value="replace-ai-files" if self.wizard.state.ai_cleanup_confirmed else "", id="confirm")
            yield Button("Review CI/CD", id="continue", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.wizard.state.ai_cleanup_confirmed = (
                self.query_one("#confirm", Input).value.strip() == "replace-ai-files"
            )
            self.next("cicd")


class CicdScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        reviews = review_workflows(self.wizard.state.repo_path)
        self.wizard.state.workflow_review = [asdict(item) for item in reviews]
        self.wizard.state.deploy_workflows_preserved = preserved_deploy_workflows(reviews)
        advisories = {}
        for item in reviews:
            if item.classification == UNKNOWN_REVIEW_REQUIRED:
                advisory = classify_workflow_summary(
                    workflow_safe_summary(self.wizard.state.repo_path, item.path)
                )
                if advisory:
                    advisories[item.path] = advisory
        self.wizard.state.ai_advisory = advisories
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("CI/CD Review", classes="title")
            yield Static(_format_workflows(self.wizard.state.workflow_review, advisories))
            yield Static('Type "standardize-ci" to replace duplicate standards checks.')
            yield Input(value="standardize-ci" if self.wizard.state.cicd_standardization_confirmed else "", id="confirm")
            yield Static('Type "split-mixed-workflows" to remove check-only jobs from mixed CI/deploy workflows.')
            yield Input(
                value=(
                    "split-mixed-workflows"
                    if self.wizard.state.mixed_workflow_cleanup_confirmed
                    else ""
                ),
                id="mixed_confirm",
            )
            yield Button("Review Modules", id="continue", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.wizard.state.cicd_standardization_confirmed = (
                self.query_one("#confirm", Input).value.strip() == "standardize-ci"
            )
            self.wizard.state.mixed_workflow_cleanup_confirmed = (
                self.query_one("#mixed_confirm", Input).value.strip()
                == "split-mixed-workflows"
            )
            self.next("modules")


class ModuleScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Modules And Quality Gates", classes="title")
            yield Static(_list_block("Selected modules", self.wizard.state.modules))
            yield Static(_list_block("Recommended quality gates", quality_gates(self.wizard.state.detection)))
            yield Checkbox("Add .pre-commit-config.yaml", value=self.wizard.state.add_precommit_config, id="precommit")
            yield Checkbox("Install local pre-commit hooks now", value=self.wizard.state.install_precommit_confirmed, id="install")
            yield Checkbox("Run Rulesync after apply", value=self.wizard.state.run_rulesync, id="rulesync")
            yield Checkbox("Run assessment after apply", value=self.wizard.state.run_assessment, id="assessment")
            yield Button("Preview Plan", id="continue", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.wizard.state.add_precommit_config = self.query_one("#precommit", Checkbox).value
            self.wizard.state.install_precommit_confirmed = self.query_one("#install", Checkbox).value
            self.wizard.state.run_rulesync = self.query_one("#rulesync", Checkbox).value
            self.wizard.state.run_assessment = self.query_one("#assessment", Checkbox).value
            self.next("plan")


class PlanScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        plan = build_wizard_plan(self.wizard.state)
        self.wizard.plan = plan
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Migration Plan Preview", classes="title")
            yield Static(_format_plan(plan))
            if plan.blocked:
                yield Static("Apply disabled while blockers are present.")
            else:
                yield Button("Apply Confirmed Plan", id="apply", variant="error")
            yield Button("Back To CI/CD Review", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            self.next("apply")
        elif event.button.id == "back":
            self.app.push_screen("cicd")


class ApplyScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Apply Progress", classes="title")
            yield Static("Press Apply to write confirmed changes, run Rulesync, and assess.")
            yield Button("Apply Now", id="apply", variant="error")
            yield Static("", id="result")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "apply":
            return
        plan = build_wizard_plan(self.wizard.state, for_apply=True)
        applied, code = apply_wizard_plan(plan)
        self.wizard.plan = applied
        result = self.query_one("#result", Static)
        assessment = applied.engine_summary.assessment_result
        rulesync = applied.engine_summary.rulesync_result
        result.update(f"Apply exit code: {code}\nRulesync: {rulesync}\nAssessment: {assessment}")
        self.app.push_screen("assessment")


class AssessmentScreen(WizardScreen):
    def compose(self) -> ComposeResult:
        summary = self.wizard.plan.engine_summary if self.wizard.plan else None
        yield Header()
        with VerticalScroll(classes="screen"):
            yield Static("Assessment Result And PR Checklist", classes="title")
            if summary:
                yield Static(
                    f"Rulesync: {summary.rulesync_result}\n"
                    f"Assessment: {summary.assessment_result}\n\n"
                    f"{_assessment_excerpt(summary.assessment_detail)}"
                )
            yield Static(
                "Review:\n"
                "  - .repo-policy.yml\n"
                "  - .repo-standards-migration-summary.md\n"
                "  - generated AI/editor files\n"
                "  - preserved deploy workflows\n"
                "  - replaced standard checks\n"
                "  - assessment report\n\n"
                "Suggested commands:\n"
                "  git status\n"
                "  git diff\n"
                "  git add .\n"
                '  git commit -m "chore(standards): adopt repo standards"\n'
                "  git push -u origin chore/standards-migration\n\n"
                'Optional:\n'
                '  gh pr create --draft --title "chore(standards): adopt repo standards"'
            )
            yield Button("Quit", id="quit", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()


class RepoStandardsWizardApp(App):
    CSS = """
    .screen {
        padding: 1 2;
    }
    .title {
        text-style: bold;
        margin-bottom: 1;
    }
    Input {
        margin-bottom: 1;
    }
    Button {
        margin-top: 1;
        margin-right: 1;
    }
    """

    SCREENS = {
        "welcome": WelcomeScreen,
        "governance": GovernanceScreen,
        "detection": DetectionScreen,
        "ai_cleanup": AiCleanupScreen,
        "cicd": CicdScreen,
        "modules": ModuleScreen,
        "plan": PlanScreen,
        "apply": ApplyScreen,
        "assessment": AssessmentScreen,
    }

    def __init__(self, *, repo: Path | None, standards: Path, base_ref: str = "main") -> None:
        super().__init__()
        self.state = WizardState(
            repo=str(repo or Path.cwd()),
            standards=str(standards),
            base_ref=base_ref,
        )
        self.plan = None

    def on_mount(self) -> None:
        self.push_screen("welcome")

    def persist(self) -> None:
        if self.state.repo:
            save_state(self.state)


def _list_block(title: str, items: list[str] | tuple[str, ...]) -> str:
    lines = [f"{title}:"]
    lines.extend(f"  - {item}" for item in items)
    return "\n".join(lines)


def _format_detection(detection: dict) -> str:
    return "\n".join(
        [
            f"Language: {detection.get('language')}",
            f"Package manager: {detection.get('package_manager')}",
            f"Deployment provider: {detection.get('deployment_provider')}",
            f"Recommended profile: {detection.get('recommended_profile')}",
            f"Confidence: {detection.get('confidence')}",
            "",
            _list_block("Evidence", detection.get("evidence") or ["none"]),
            "",
            _list_block("Manual review notes", detection.get("manual_review") or ["none"]),
        ]
    )


def _format_workflows(reviews: list[dict], advisories: dict) -> str:
    if not reviews:
        return "No GitHub Actions workflows found."
    lines: list[str] = []
    for item in reviews:
        lines.append(f"{item['classification']}: {item['path']}")
        lines.append(f"  Reason: {item['reason']}")
        advisory = advisories.get(item["path"])
        if advisory:
            lines.append(f"  AI advisory: {advisory.get('classification')} ({advisory.get('confidence')})")
            lines.append(f"  AI reason: {advisory.get('reason')}")
    return "\n".join(lines)


def _format_plan(plan) -> str:
    lines: list[str] = []
    for group, actions in action_groups(plan).items():
        lines.append(f"{group}:")
        if not actions:
            lines.append("  none")
            continue
        for action in actions:
            detail = f" — {action.detail}" if action.detail else ""
            lines.append(f"  {action.path}{detail}")
        lines.append("")
    return "\n".join(lines)


def _assessment_excerpt(text: str) -> str:
    if not text:
        return "No assessment output captured."
    lines = text.splitlines()
    return "\n".join(lines[:40])
