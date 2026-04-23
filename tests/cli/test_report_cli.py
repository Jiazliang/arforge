from __future__ import annotations

import subprocess
import sys

from tests._shared import REPO_ROOT, VALID_PROJECT, WARNING_ONLY_PROJECT

def test_cli_report_smoke() -> None:
    out_file = REPO_ROOT / "build" / "test_cli_report_examples.md"
    if out_file.exists():
        out_file.unlink()

    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "report", str(VALID_PROJECT), "--out", str(out_file)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert out_file.exists()

def test_cli_report_warning_project_still_succeeds() -> None:
    out_file = REPO_ROOT / "build" / "test_cli_report_warning.md"
    if out_file.exists():
        out_file.unlink()

    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "report", str(WARNING_ONLY_PROJECT), "--out", str(out_file)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert out_file.exists()
