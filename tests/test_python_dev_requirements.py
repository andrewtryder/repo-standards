"""Tests for Python dev requirements helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from python_dev_requirements import (
    merge_python_dev_requirements_text,
    missing_python_dev_packages,
    requirement_names_in_text,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class PythonDevRequirementsTests(unittest.TestCase):
    def test_requirement_names_ignore_comments_and_includes(self) -> None:
        text = """-r requirements.txt

# Testing
pytest==8.3.4
ruff>=0.8
"""
        self.assertEqual(requirement_names_in_text(text), {"pytest", "ruff"})

    def test_missing_packages_detects_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "requirements.txt", "fastapi\n")
            write(
                repo / "requirements-dev.txt",
                "-r requirements.txt\n\npytest\nruff\n",
            )

            missing = missing_python_dev_packages(repo)

            self.assertEqual(missing, ["coverage", "httpx"])

    def test_merge_appends_missing_packages(self) -> None:
        existing = "-r requirements.txt\n\npytest\nruff\n"
        merged = merge_python_dev_requirements_text(existing, ["coverage"])

        self.assertIn("coverage", merged)
        self.assertIn("repo-standards", merged)


if __name__ == "__main__":
    unittest.main()
