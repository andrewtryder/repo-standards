from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_standards.core.ai_files import discover_ai_files
from repo_standards.core.cicd import (
    KEEP_DEPLOY,
    REPLACE_DUPLICATE_AI_RULES_CHECK,
    REPLACE_DUPLICATE_SECRET_SCAN,
    UNKNOWN_REVIEW_REQUIRED,
    plan_mixed_workflow_cleanup,
    review_workflows,
)
from repo_standards.core.detection import detect_repository
from repo_standards.core.planning import apply_wizard_plan, build_wizard_plan
from repo_standards.core.state import GovernanceAnswers, WizardState, load_state, save_state


ROOT = Path(__file__).resolve().parents[1]


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class WizardCoreTests(unittest.TestCase):
    def test_firebase_detection_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "firebase-app"
            repo.mkdir()
            write(repo / "package.json", json.dumps({"private": True}))
            write(repo / "package-lock.json", "{}")
            write(repo / "tsconfig.json", "{}")
            write(repo / "firebase.json", "{}")

            result = detect_repository(repo, ROOT)

            self.assertEqual(result["language"], "typescript")
            self.assertEqual(result["deployment_provider"], "firebase")
            self.assertEqual(result["recommended_profile"], "typescript-app")
            self.assertIn("firebase", result["modules"])

    def test_home_assistant_custom_component_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "ha-integration"
            repo.mkdir()
            write(repo / "pyproject.toml", "[tool.pytest.ini_options]\n")
            write(repo / "requirements.txt", "homeassistant\n")
            write(
                repo / "custom_components/demo/manifest.json",
                '{"domain": "demo", "name": "Demo"}\n',
            )
            write(repo / "custom_components/demo/__init__.py", "")

            result = detect_repository(repo, ROOT)

            self.assertEqual(result["language"], "python")
            self.assertEqual(result["recommended_profile"], "python-home-assistant")
            self.assertIn("home-assistant", result["modules"])

    def test_ai_file_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            write(repo / "AGENTS.md", "old")
            write(repo / "CLAUDE.md", "old")
            (repo / ".cursor").mkdir()
            (repo / ".agents").mkdir()

            found = discover_ai_files(repo)

            self.assertEqual(
                [item.path for item in found],
                ["AGENTS.md", "CLAUDE.md", ".cursor", ".agents"],
            )

    def test_workflow_review_preserves_deploy_and_maps_standard_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            write(
                repo / ".github/workflows/deploy.yml",
                "name: Deploy\njobs:\n  deploy:\n    steps:\n      - run: firebase deploy\n",
            )
            write(repo / ".github/workflows/secret-scan.yml", "name: Secret scan\njobs: {}\n")
            write(repo / ".github/workflows/ai-rules-check.yml", "name: AI rules\njobs: {}\n")
            write(repo / ".github/workflows/custom.yml", "name: Custom\njobs: {}\n")

            reviews = {item.path: item.classification for item in review_workflows(repo)}

            self.assertEqual(reviews[".github/workflows/deploy.yml"], KEEP_DEPLOY)
            self.assertEqual(
                reviews[".github/workflows/secret-scan.yml"],
                REPLACE_DUPLICATE_SECRET_SCAN,
            )
            self.assertEqual(
                reviews[".github/workflows/ai-rules-check.yml"],
                REPLACE_DUPLICATE_AI_RULES_CHECK,
            )
            self.assertEqual(reviews[".github/workflows/custom.yml"], UNKNOWN_REVIEW_REQUIRED)

    def test_security_review_workflows_are_preserved_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            write(repo / ".github/workflows/codeql.yml", "name: CodeQL\njobs:\n  analyze:\n    steps:\n      - run: npm ci\n")
            write(repo / ".github/workflows/dependency-review.yml", "name: Dependency Review\njobs: {}\n")

            reviews = {item.path: item.classification for item in review_workflows(repo)}

            self.assertEqual(reviews[".github/workflows/codeql.yml"], UNKNOWN_REVIEW_REQUIRED)
            self.assertEqual(
                reviews[".github/workflows/dependency-review.yml"],
                UNKNOWN_REVIEW_REQUIRED,
            )

    def test_scheduled_secret_workflow_is_preserved_as_operational(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            write(
                repo / ".github/workflows/send-newsletter.yml",
                """name: Send newsletter

on:
  schedule:
    - cron: "0 8 * * 6"

jobs:
  send:
    runs-on: ubuntu-latest
    env:
      RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
    steps:
      - run: pip install -r backend/requirements.txt
      - run: python backend/newsletter.py send
      - run: bash checkly/scripts/heartbeat-ping.sh
""",
            )

            reviews = {item.path: item.classification for item in review_workflows(repo)}

            self.assertEqual(reviews[".github/workflows/send-newsletter.yml"], KEEP_DEPLOY)

    def test_release_please_with_publish_behavior_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            write(
                repo / ".github/workflows/release-please.yml",
                """name: Release Please

on:
  push:
    branches: [main]

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v5
  publish:
    runs-on: ubuntu-latest
    steps:
      - run: npm publish --provenance
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/deploy-pages@v5
""",
            )

            reviews = {item.path: item.classification for item in review_workflows(repo)}

            self.assertEqual(reviews[".github/workflows/release-please.yml"], "KEEP_RELEASE")

    def test_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            state = WizardState(
                repo=str(repo),
                standards=str(ROOT),
                phase="plan-reviewed",
                governance=GovernanceAnswers(visibility="public", license="MIT"),
                modules=["core", "ai-agents", "firebase"],
                ai_cleanup_confirmed=True,
            )

            save_state(state)
            loaded = load_state(repo)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.phase, "plan-reviewed")
            self.assertEqual(loaded.governance.visibility, "public")
            self.assertEqual(loaded.modules, ["core", "ai-agents", "firebase"])
            self.assertTrue(loaded.ai_cleanup_confirmed)

    def test_planning_blocks_ai_cleanup_until_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            init_repo(repo)
            write(repo / "AGENTS.md", "old")
            write(repo / "package.json", json.dumps({"private": True}))
            write(repo / "package-lock.json", "{}")
            write(repo / "tsconfig.json", "{}")
            write(
                repo / ".github/workflows/ci.yml",
                "name: CI\njobs:\n  test:\n    steps:\n      - run: npm test\n",
            )
            detection = detect_repository(repo, ROOT)

            state = WizardState(repo=str(repo), standards=str(ROOT), detection=detection)
            blocked = build_wizard_plan(state)

            self.assertTrue(
                any(
                    action.action == "BLOCK" and action.path == "AGENTS.md"
                    for action in blocked.actions
                )
            )

            state.ai_cleanup_confirmed = True
            state.cicd_standardization_confirmed = True
            confirmed = build_wizard_plan(state)

            self.assertTrue(
                any(
                    action.action == "DELETE" and action.path == "AGENTS.md"
                    for action in confirmed.actions
                )
            )
            self.assertTrue(
                any(
                    action.action == "REPLACE"
                    and action.path == ".github/workflows/ci.yml"
                    for action in confirmed.actions
                )
            )

    def test_mixed_special_warns_instead_of_replacing_without_reusable_ci(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            init_repo(repo)
            write(repo / "package.json", json.dumps({"private": True}))
            write(repo / "package-lock.json", "{}")
            write(repo / "backend/app.py", "")
            write(
                repo / ".github/workflows/ci.yml",
                "name: CI\njobs:\n  test:\n    steps:\n      - run: npm ci\n      - run: pytest\n",
            )
            detection = detect_repository(repo, ROOT)
            state = WizardState(
                repo=str(repo),
                standards=str(ROOT),
                detection=detection,
                cicd_standardization_confirmed=True,
            )

            plan = build_wizard_plan(state)

            self.assertEqual(detection["language"], "mixed")
            self.assertFalse(
                any(
                    action.action == "REPLACE"
                    and action.path == ".github/workflows/ci.yml"
                    for action in plan.actions
                )
            )
            self.assertTrue(
                any(
                    action.action == "WARN"
                    and action.path == ".github/workflows/ci.yml"
                    and "reusable CI support" in action.detail
                    for action in plan.actions
                )
            )

    def test_mixed_workflow_cleanup_removes_check_job_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            init_repo(repo)
            write(repo / "package.json", json.dumps({"private": True}))
            write(repo / "package-lock.json", "{}")
            write(repo / "tsconfig.json", "{}")
            write(
                repo / ".github/workflows/cicd.yml",
                """name: CI/CD

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
  deploy:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: firebase deploy
""",
            )
            detection = detect_repository(repo, ROOT)

            cleanup = plan_mixed_workflow_cleanup(repo, ".github/workflows/cicd.yml")
            self.assertTrue(cleanup.can_update)
            self.assertEqual(cleanup.removable_jobs, ["test"])
            self.assertEqual(cleanup.preserved_jobs, ["deploy"])

            state = WizardState(
                repo=str(repo),
                standards=str(ROOT),
                detection=detection,
                ai_cleanup_confirmed=True,
                cicd_standardization_confirmed=True,
                mixed_workflow_cleanup_confirmed=True,
                run_rulesync=False,
                run_assessment=False,
            )
            plan = build_wizard_plan(state, for_apply=True)
            self.assertTrue(
                any(
                    action.action == "UPDATE"
                    and action.path == ".github/workflows/cicd.yml"
                    for action in plan.actions
                )
            )
            self.assertTrue(
                any(
                    action.action == "CREATE"
                    and action.path == ".github/workflows/ci.yml"
                    for action in plan.actions
                )
            )

            _applied, code = apply_wizard_plan(plan)

            self.assertEqual(code, 0)
            self.assertTrue((repo / ".github/workflows/ci.yml").is_file())
            text = (repo / ".github/workflows/cicd.yml").read_text(encoding="utf-8")
            self.assertNotIn("test:", text)
            self.assertIn("deploy:", text)
            self.assertIn("firebase deploy", text)
            self.assertNotIn("needs:", text)

    def test_home_assistant_validation_workflow_trims_tests_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            init_repo(repo)
            write(repo / "pyproject.toml", "[tool.pytest.ini_options]\n")
            write(repo / "requirements.txt", "")
            write(repo / "requirements_test.txt", "")
            write(
                repo / "custom_components/demo/manifest.json",
                '{"domain": "demo", "name": "Demo"}\n',
            )
            write(repo / "custom_components/demo/__init__.py", "")
            write(
                repo / ".github/workflows/validate.yml",
                """name: Validate

on:
  pull_request:

jobs:
  validate-hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: hacs/action@main
  validate-hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: home-assistant/actions/hassfest@master
  validate-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest
""",
            )
            detection = detect_repository(repo, ROOT)
            state = WizardState(
                repo=str(repo),
                standards=str(ROOT),
                detection=detection,
                ai_cleanup_confirmed=True,
                cicd_standardization_confirmed=True,
                mixed_workflow_cleanup_confirmed=True,
                run_rulesync=False,
                run_assessment=False,
            )

            plan = build_wizard_plan(state, for_apply=True)
            self.assertTrue(
                any(
                    action.action == "UPDATE"
                    and action.path == ".github/workflows/validate.yml"
                    for action in plan.actions
                )
            )
            self.assertTrue(
                any(
                    action.action == "CREATE"
                    and action.path == ".github/workflows/ci.yml"
                    for action in plan.actions
                )
            )
            _applied, code = apply_wizard_plan(plan)

            self.assertEqual(code, 0)
            ci_text = (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")
            self.assertIn("requirements_test.txt", ci_text)
            self.assertNotIn("requirements-dev.txt", ci_text)
            text = (repo / ".github/workflows/validate.yml").read_text(encoding="utf-8")
            self.assertIn("validate-hacs:", text)
            self.assertIn("validate-hassfest:", text)
            self.assertNotIn("validate-tests:", text)


if __name__ == "__main__":
    unittest.main()
