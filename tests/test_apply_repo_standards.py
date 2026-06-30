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
    rulesync_install_command_text,
    tooling_package_json_content,
)
from assess_repo_standards import (  # noqa: E402
    make_recommendations,
    package_state,
    python_dependency_state,
    score_report,
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


def minimal_assessment_state(repo: Path) -> dict[str, object]:
    return {
        "package": package_state(repo),
        "python_dependencies": python_dependency_state(repo),
        "workflows": {
            "has_ai_rules_workflow": True,
            "has_semantic_pr_workflow": True,
            "mentions_coverage": False,
            "has_release_please": True,
        },
        "ai": {
            "has_repo_policy": True,
            "has_rulesync_config": True,
            "has_rulesync_rules_dir": True,
            "has_agents_md": True,
            "has_cursor_rules_dir": True,
            "has_agents_rules_dir": True,
            "has_antigravity_target_in_config": False,
        },
        "docs": {
            "has_readme": True,
            "readme_mentions_checks": True,
            "readme_mentions_deploy_or_release": True,
            "readme_mentions_ai": True,
        },
        "gitignore": {
            "has_coverage": True,
            "has_gitignore": True,
            "has_editorconfig": True,
            "has_env_example": True,
            "has_security_md": True,
            "has_issue_templates": True,
            "has_adr_template_or_decisions_dir": True,
            "excludes_env_not_example": True,
        },
        "governance": {
            "has_contributing": True,
            "has_pr_template": True,
            "has_license": True,
            "policy_visibility": "private",
            "policy_license": "proprietary",
        },
        "code_quality": {"findings": []},
        "changed": {
            "generated_artifacts": [],
            "agent_memories": [],
            "suspicious_agents_paths": [],
            "risky_deploy_files": [],
            "secretish_files": [],
        },
    }


def empty_command_analysis() -> dict[str, object]:
    return {
        "eslint_errors": 0,
        "eslint_warnings": 0,
        "npm_vulnerabilities": None,
        "npm_vulnerability_detail": None,
        "coverage": None,
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

    def test_python_missing_dev_requirements_warns_and_recommends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "main.py", "print('hello')\n")

            state = minimal_assessment_state(repo)
            _score, _blockers, warnings = score_report(
                state,
                empty_command_analysis(),
                [],
                [],
                [],
            )
            recs, _feedback = make_recommendations(
                state,
                empty_command_analysis(),
                [],
                [],
            )

            self.assertTrue(
                any("requirements-dev.txt" in warning for warning in warnings)
            )
            self.assertTrue(any("requirements-dev.txt" in rec for rec in recs))

    def test_node_tooling_in_runtime_dependencies_warns_and_recommends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(
                repo / "package.json",
                json.dumps(
                    {
                        "scripts": {"lint": "eslint .", "test": "vitest run", "build": "tsc"},
                        "dependencies": {"eslint": "^9.0.0", "@types/node": "^22.0.0"},
                        "devDependencies": {"typescript": "^5.0.0"},
                    }
                ),
            )

            state = minimal_assessment_state(repo)
            _score, _blockers, warnings = score_report(
                state,
                empty_command_analysis(),
                [],
                [],
                [],
            )
            recs, _feedback = make_recommendations(
                state,
                empty_command_analysis(),
                [],
                [],
            )

            self.assertIn("eslint", state["package"]["misplaced_dev_dependencies"])
            self.assertIn("@types/node", state["package"]["misplaced_dev_dependencies"])
            self.assertTrue(
                any("devDependencies" in warning for warning in warnings)
            )
            self.assertTrue(any("devDependencies" in rec for rec in recs))

    def test_node_tooling_in_dev_dependencies_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(
                repo / "package.json",
                json.dumps(
                    {
                        "scripts": {"lint": "eslint .", "test": "vitest run", "build": "tsc"},
                        "dependencies": {"fastify": "^5.0.0"},
                        "devDependencies": {
                            "eslint": "^9.0.0",
                            "@types/node": "^22.0.0",
                            "typescript": "^5.0.0",
                            "vitest": "^2.0.0",
                        },
                    }
                ),
            )

            state = minimal_assessment_state(repo)

            self.assertEqual(state["package"]["misplaced_dev_dependencies"], [])

    def test_full_python_adoption_creates_dev_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "main.py", "print('hello')\n")

            summary = build_plan(
                repo,
                ROOT,
                mode="existing",
                profile="python-service",
                workflow_strategy="none",
                rules_strategy="profile",
                adoption_level="full",
                update_existing=False,
                force=False,
                allow_generated_output_rewrite=False,
                cleanup_generated_artifacts=False,
                replace_check_workflows=False,
                migrate_existing_agent_rules=False,
                for_apply=True,
                will_run_rulesync=False,
                policy_fields=PolicyFields("private", "proprietary", "test", "test"),
                format_touched=False,
                format_existing_docs=False,
                add_license=False,
            )

            self.assertTrue(
                any(
                    action.action == "CREATE" and action.path == "requirements-dev.txt"
                    for action in summary.actions
                )
            )

    def test_existing_dev_requirements_missing_coverage_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "requirements-dev.txt", "-r requirements.txt\n\npytest\nruff\n")
            write(repo / "main.py", "print('hello')\n")

            summary = build_plan(
                repo,
                ROOT,
                mode="existing",
                profile="python-service",
                workflow_strategy="none",
                rules_strategy="profile",
                adoption_level="reusable-ci",
                update_existing=False,
                force=False,
                allow_generated_output_rewrite=False,
                cleanup_generated_artifacts=False,
                replace_check_workflows=False,
                migrate_existing_agent_rules=False,
                for_apply=True,
                will_run_rulesync=False,
                policy_fields=PolicyFields("private", "proprietary", "test", "test"),
                format_touched=False,
                format_existing_docs=False,
                add_license=False,
            )

            self.assertTrue(
                any(
                    action.action == "MERGE"
                    and action.path == "requirements-dev.txt"
                    and "coverage" in action.detail
                    for action in summary.actions
                )
            )

    def test_python_service_adoption_creates_release_please(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "main.py", "print('hello')\n")

            summary = build_plan(
                repo,
                ROOT,
                mode="existing",
                profile="python-service",
                workflow_strategy="reusable",
                rules_strategy="profile",
                adoption_level="reusable-ci",
                update_existing=False,
                force=False,
                allow_generated_output_rewrite=False,
                cleanup_generated_artifacts=False,
                replace_check_workflows=False,
                migrate_existing_agent_rules=False,
                for_apply=True,
                will_run_rulesync=False,
                policy_fields=PolicyFields("public", "MIT", "test", "test"),
                format_touched=False,
                format_existing_docs=False,
                add_license=False,
            )

            self.assertTrue(
                any(
                    action.action == "CREATE"
                    and action.path == ".github/workflows/release-please.yml"
                    for action in summary.actions
                )
            )
            self.assertTrue(
                any(action.action == "CREATE" and action.path == "CHANGELOG.md" for action in summary.actions)
            )

    def test_full_python_adoption_creates_tooling_package_for_rulesync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "main.py", "print('hello')\n")

            summary = build_plan(
                repo,
                ROOT,
                mode="existing",
                profile="python-service",
                workflow_strategy="none",
                rules_strategy="profile",
                adoption_level="full",
                update_existing=False,
                force=False,
                allow_generated_output_rewrite=False,
                cleanup_generated_artifacts=False,
                replace_check_workflows=False,
                migrate_existing_agent_rules=False,
                for_apply=True,
                will_run_rulesync=False,
                policy_fields=PolicyFields("private", "proprietary", "test", "test"),
                format_touched=False,
                format_existing_docs=False,
                add_license=False,
            )

            self.assertTrue(
                any(
                    action.action == "CREATE" and action.path == "package.json"
                    for action in summary.actions
                )
            )
            package = json.loads(tooling_package_json_content(repo))
            self.assertTrue(package["private"])
            self.assertEqual(package["scripts"]["rulesync"], "rulesync generate")

    def test_rulesync_install_command_available_without_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            command = rulesync_install_command_text(
                repo,
                {
                    "language": "python",
                    "package_manager": "pip-requirements",
                    "recommended_profile": "python-service",
                },
            )

            self.assertEqual(command, "npm install -D rulesync")

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
