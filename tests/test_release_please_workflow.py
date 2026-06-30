"""Tests for Release Please workflow helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from release_please_workflow import (  # noqa: E402
    RELEASE_PLEASE_WORKFLOW_REL,
    has_release_please_workflow,
    parse_release_please_enabled,
    release_please_enabled_for_repo,
    release_please_template_path,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ReleasePleaseWorkflowTests(unittest.TestCase):
    def test_parse_release_please_enabled(self) -> None:
        text = "release:\n  release_please: true\n  strategy: simple\n"
        self.assertTrue(parse_release_please_enabled(text))
        self.assertFalse(parse_release_please_enabled("release_please: false"))

    def test_python_service_uses_simple_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            standards = ROOT
            write(repo / "requirements.txt", "fastapi\n")
            template = release_please_template_path(
                standards,
                repo,
                selected_profile="python-service",
                language="python",
                policy_text="release:\n  release_please: true\n  strategy: simple\n",
            )
            self.assertEqual(template.name, "release-please.simple.yml")

    def test_typescript_app_policy_disables_release_please(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            enabled = release_please_enabled_for_repo(
                repo,
                ROOT,
                selected_profile="typescript-app",
                rendered_policy=None,
            )
            self.assertFalse(enabled)


if __name__ == "__main__":
    unittest.main()
