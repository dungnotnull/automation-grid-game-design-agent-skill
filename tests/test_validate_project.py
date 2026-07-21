"""test_validate_project.py - pytest wrapper that runs validate_project.py and asserts exit 0."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_validate_project_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_project.py")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, (
        f"validate_project failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "PASSED" in result.stdout


def test_run_test_scenarios_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "run_test_scenarios.py")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, (
        f"run_test_scenarios failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "all checks passed" in result.stdout


def test_knowledge_updater_dry_run():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "knowledge_updater.py"),
         "--dry-run", "--news-only", "--offline", "--keywords", "zzz"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
