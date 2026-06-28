from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from apply_repo_standards import (  # noqa: E402
    PolicyFields,
    build_plan,
    reusable_ci_workflow_for,
)
from detect_repo_standard import detect_repo  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def node_detection(package_manager: str) -> dict[str, str]:
    return {
        "language": "typescript",
        "package_manager": package_manager,
        "deployment_provider": "none",
        "recommended_profile": "typescript-app",
    }


class ApplyRepoStandardsTests(unittest.TestCase):
    def test_detect_repo_identifies_fly_deployment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "main.py", "print('hello')\n")
            write(repo / "fly.toml", "app = 'demo'\n")
            write(
                repo / ".github/workflows/fly.yml",
                "name: Fly Deploy\nsteps:\n  - run: flyctl deploy\n",
            )

            result = detect_repo(repo, ROOT)

            self.assertEqual(result["deployment_provider"], "fly")
            self.assertIn("fly.toml exists", result["evidence"])

    def test_node_reusable_ci_uses_inferred_package_manager_commands(self) -> None:
        cases = [
            ("npm", "package-lock.json", "npm ci", "npm run lint", "npm test"),
            (
                "pnpm",
                "pnpm-lock.yaml",
                "pnpm install --frozen-lockfile",
                "pnpm run lint",
                "pnpm run test",
            ),
            (
                "yarn",
                "yarn.lock",
                "yarn install --frozen-lockfile",
                "yarn run lint",
                "yarn run test",
            ),
            (
                "bun",
                "bun.lock",
                "bun install --frozen-lockfile",
                "bun run lint",
                "bun run test",
            ),
        ]
        for package_manager, lockfile, install, lint, test in cases:
            with self.subTest(package_manager=package_manager):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = Path(tmp)
                    write(
                        repo / "package.json",
                        json.dumps(
                            {
                                "scripts": {
                                    "lint": "eslint .",
                                    "test": "vitest run",
                                }
                            }
                        ),
                    )
                    write(repo / lockfile, "")

                    workflow = reusable_ci_workflow_for(
                        repo,
                        node_detection(package_manager),
                    )

                    assert workflow is not None
                    self.assertIn(f'install_command: "{install}"', workflow)
                    self.assertIn(f'lint_command: "{lint}"', workflow)
                    self.assertIn(f'test_command: "{test}"', workflow)

    def test_node_reusable_ci_preserves_safe_defaults_for_unknown_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "package.json", json.dumps({"scripts": {}}))
            write(repo / "package-lock.json", "")

            workflow = reusable_ci_workflow_for(repo, node_detection("npm"))

            assert workflow is not None
            self.assertIn('lint_command: "npm run lint --if-present"', workflow)
            self.assertIn('test_command: "npm test --if-present"', workflow)

    def test_python_reusable_ci_uses_empty_coverage_args_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            workflow = reusable_ci_workflow_for(
                repo,
                {
                    "language": "python",
                    "package_manager": "pip-requirements",
                    "recommended_profile": "python-service",
                },
            )

            assert workflow is not None
            self.assertIn('coverage_args: ""', workflow)
            self.assertNotIn("--report-only", workflow)

    def test_python_reusable_ci_uses_existing_requirements_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")

            workflow = reusable_ci_workflow_for(
                repo,
                {
                    "language": "python",
                    "package_manager": "pip-requirements",
                    "recommended_profile": "python-service",
                },
            )

            assert workflow is not None
            self.assertIn(
                'install_command: "python -m pip install -r requirements.txt pytest coverage ruff httpx"',
                workflow,
            )
            self.assertNotIn("requirements-dev.txt", workflow)

    def test_python_reusable_ci_includes_dev_requirements_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "requirements-dev.txt", "pytest\ncoverage\nruff\n")

            workflow = reusable_ci_workflow_for(
                repo,
                {
                    "language": "python",
                    "package_manager": "pip-requirements",
                    "recommended_profile": "python-service",
                },
            )

            assert workflow is not None
            self.assertIn(
                'install_command: "python -m pip install -r requirements.txt -r requirements-dev.txt"',
                workflow,
            )

    def test_migrated_agent_rule_does_not_false_block_rulesync_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "")
            write(repo / ".agents/rules/custom.md", "Existing generated rule\n")

            summary = build_plan(
                repo,
                ROOT,
                mode="existing",
                profile="python-service",
                workflow_strategy="none",
                rules_strategy="profile",
                adoption_level="baseline",
                update_existing=False,
                force=False,
                allow_generated_output_rewrite=False,
                cleanup_generated_artifacts=False,
                replace_check_workflows=False,
                migrate_existing_agent_rules=True,
                for_apply=True,
                will_run_rulesync=True,
                policy_fields=PolicyFields("private", "proprietary", "test", "test"),
                format_touched=False,
                format_existing_docs=False,
                add_license=False,
            )

            self.assertIn("05-custom.md", summary.migrated_agent_rule_targets)
            self.assertFalse(
                any(
                    action.action == "BLOCK"
                    and action.path == ".agents/rules/custom.md"
                    for action in summary.actions
                )
            )

    def test_orphaned_agent_rule_still_blocks_rulesync_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "")
            write(repo / ".agents/rules/custom.md", "Existing generated rule\n")

            summary = build_plan(
                repo,
                ROOT,
                mode="existing",
                profile="python-service",
                workflow_strategy="none",
                rules_strategy="profile",
                adoption_level="baseline",
                update_existing=False,
                force=False,
                allow_generated_output_rewrite=False,
                cleanup_generated_artifacts=False,
                replace_check_workflows=False,
                migrate_existing_agent_rules=False,
                for_apply=True,
                will_run_rulesync=True,
                policy_fields=PolicyFields("private", "proprietary", "test", "test"),
                format_touched=False,
                format_existing_docs=False,
                add_license=False,
            )

            self.assertTrue(
                any(
                    action.action == "BLOCK"
                    and action.path == ".agents/rules/custom.md"
                    for action in summary.actions
                )
            )


if __name__ == "__main__":
    unittest.main()
