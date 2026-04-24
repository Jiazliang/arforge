"""CLI tests for `arforge diff`.

This file verifies that the diff command completes successfully against the
small dedicated sample diff projects and writes the expected Markdown artifact.
"""

from __future__ import annotations

import subprocess
import sys

from tests._shared import REPO_ROOT

SAMPLE_PROJECTS_ROOT = REPO_ROOT / "tests" / "diff" / "sample_projects"
BASELINE_PROJECT = SAMPLE_PROJECTS_ROOT / "baseline" / "autosar.project.yaml"
UPDATED_PROJECT = SAMPLE_PROJECTS_ROOT / "updated" / "autosar.project.yaml"


def test_cli_diff_smoke() -> None:
    out_file = REPO_ROOT / "build" / "test_cli_diff.md"
    if out_file.exists():
        out_file.unlink()

    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "diff", str(BASELINE_PROJECT), str(UPDATED_PROJECT), "--out", str(out_file)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert out_file.exists()
