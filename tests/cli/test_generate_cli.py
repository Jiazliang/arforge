"""CLI tests for `arforge generate`.

These tests cover the command-line entry points for code generation and
diagram generation, making sure both commands execute and emit artifacts.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from tests._shared import PLANTUML_DIAGRAM_OUTPUTS, REPO_ROOT, VALID_PROJECT

def test_cli_generate_code_smoke() -> None:
    out_dir = REPO_ROOT / "build" / "test_cli_generate_code_examples"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arforge.cli",
            "generate",
            "code",
            str(VALID_PROJECT),
            "--lang",
            "c",
            "--out",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

@pytest.mark.parametrize(
    ("diagram_format", "expected_names"),
    [
        ("plantuml", PLANTUML_DIAGRAM_OUTPUTS),
    ],
)
def test_cli_generate_diagram_smoke(diagram_format: str, expected_names: list[str]) -> None:
    out_dir = REPO_ROOT / "build" / f"test_diagrams_{diagram_format}"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arforge.cli",
            "generate",
            "diagram",
            str(VALID_PROJECT),
            "--out",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out_dir.iterdir()) == sorted(expected_names)
