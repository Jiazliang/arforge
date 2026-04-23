from __future__ import annotations

import shutil
import subprocess
import sys

from tests._shared import REPO_ROOT, VALID_PROJECT

def test_cli_export_smoke() -> None:
    out_dir = REPO_ROOT / "build" / "test_cli_export_examples"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "export", str(VALID_PROJECT), "--out", str(out_dir), "--split-by-swc"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
