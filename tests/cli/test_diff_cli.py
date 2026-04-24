"""CLI tests for `arforge diff`.

This file verifies both the existing two-project diff mode and the
Git-integrated diff mode, including argument validation and error handling.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import os
from pathlib import Path

from typer.testing import CliRunner

from arforge.cli import app
from tests._shared import REPO_ROOT

SAMPLE_PROJECTS_ROOT = REPO_ROOT / "tests" / "diff" / "sample_projects"
BASELINE_PROJECT = SAMPLE_PROJECTS_ROOT / "baseline" / "autosar.project.yaml"
UPDATED_PROJECT = SAMPLE_PROJECTS_ROOT / "updated" / "autosar.project.yaml"
RUNNER = CliRunner()


def _run_cli(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) if not pythonpath else os.pathsep.join([str(REPO_ROOT), pythonpath])
    return subprocess.run(
        [sys.executable, "-m", "arforge.cli", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )


def _copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _create_git_diff_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "git_diff_repo"
    repo.mkdir()
    _copy_tree(SAMPLE_PROJECTS_ROOT / "baseline", repo / "baseline")
    _copy_tree(SAMPLE_PROJECTS_ROOT / "updated", repo / "updated")

    project_dir = repo / "project"
    project_dir.mkdir()
    project_path = project_dir / "autosar.project.yaml"
    project_path.write_text(
        "\n".join(
            [
                'autosar:',
                '  version: "4.2"',
                '  rootPackage: "DIFF"',
                '',
                'inputs:',
                '  baseTypes: "../baseline/types/base_types.yaml"',
                '  implementationDataTypes: "../baseline/types/implementation_types.yaml"',
                '  applicationDataTypes: "../baseline/types/application_types.yaml"',
                '  interfaces:',
                '    - "../baseline/interfaces/*.yaml"',
                '  swcs:',
                '    - "../baseline/swcs/*.yaml"',
                '  subcompositions:',
                '    - "../baseline/subcompositions/*.yaml"',
                '  system: "../baseline/system.yaml"',
                '',
            ]
        ),
        encoding="utf-8",
    )

    assert _git(repo, "init").returncode == 0
    assert _git(repo, "config", "user.name", "ARForge Tests").returncode == 0
    assert _git(repo, "config", "user.email", "tests@example.com").returncode == 0
    assert _git(repo, "add", ".").returncode == 0
    commit = _git(repo, "commit", "-m", "baseline")
    assert commit.returncode == 0, commit.stdout + commit.stderr

    project_path.write_text(
        "\n".join(
            [
                'autosar:',
                '  version: "4.2"',
                '  rootPackage: "DIFF"',
                '',
                'inputs:',
                '  baseTypes: "../updated/types/base_types.yaml"',
                '  implementationDataTypes: "../updated/types/implementation_types.yaml"',
                '  applicationDataTypes: "../updated/types/application_types.yaml"',
                '  interfaces:',
                '    - "../updated/interfaces/*.yaml"',
                '  swcs:',
                '    - "../updated/swcs/*.yaml"',
                '  subcompositions:',
                '    - "../updated/subcompositions/*.yaml"',
                '  system: "../updated/system.yaml"',
                '',
            ]
        ),
        encoding="utf-8",
    )
    return repo, project_path.relative_to(repo)


def test_cli_diff_file_mode_smoke() -> None:
    out_file = REPO_ROOT / "build" / "test_cli_diff.md"
    if out_file.exists():
        out_file.unlink()

    result = _run_cli(
        ["diff", str(BASELINE_PROJECT), str(UPDATED_PROJECT), "--out", str(out_file)],
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert out_file.exists()


def test_cli_diff_git_mode_works(tmp_path: Path) -> None:
    repo, project_relpath = _create_git_diff_fixture(tmp_path)
    out_file = repo / "build" / "git_diff.md"
    project_arg = project_relpath.as_posix()

    result = _run_cli(
        ["diff", project_arg, "--base-git-ref", "HEAD", "--out", str(out_file)],
        cwd=repo,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    rendered = out_file.read_text(encoding="utf-8")
    assert "Detected " in rendered
    assert "`NewMonitor`" in rendered
    assert f"`HEAD:{project_arg}`" in rendered
    assert ".arforge-git-base-" not in rendered


def test_cli_diff_git_mode_is_deterministic(tmp_path: Path) -> None:
    repo, project_relpath = _create_git_diff_fixture(tmp_path)
    out_one = repo / "build" / "git_diff_1.md"
    out_two = repo / "build" / "git_diff_2.md"
    project_arg = project_relpath.as_posix()

    result_one = _run_cli(
        ["diff", project_arg, "--base-git-ref", "HEAD", "--out", str(out_one)],
        cwd=repo,
    )
    result_two = _run_cli(
        ["diff", project_arg, "--base-git-ref", "HEAD", "--out", str(out_two)],
        cwd=repo,
    )

    assert result_one.returncode == 0, result_one.stdout + result_one.stderr
    assert result_two.returncode == 0, result_two.stdout + result_two.stderr
    assert out_one.read_text(encoding="utf-8") == out_two.read_text(encoding="utf-8")


def test_cli_diff_rejects_one_path_without_git_ref() -> None:
    result = _run_cli(["diff", str(BASELINE_PROJECT)], cwd=REPO_ROOT)

    assert result.returncode == 2
    assert "Invalid diff arguments" in result.stdout


def test_cli_diff_rejects_two_paths_with_git_ref() -> None:
    result = _run_cli(
        ["diff", str(BASELINE_PROJECT), str(UPDATED_PROJECT), "--base-git-ref", "HEAD"],
        cwd=REPO_ROOT,
    )

    assert result.returncode == 2
    assert "Invalid diff arguments" in result.stdout


def test_cli_diff_reports_invalid_git_ref(tmp_path: Path) -> None:
    repo, project_relpath = _create_git_diff_fixture(tmp_path)
    project_arg = project_relpath.as_posix()

    result = _run_cli(
        ["diff", project_arg, "--base-git-ref", "missing-ref"],
        cwd=repo,
    )

    assert result.returncode == 2
    assert "could not be resolved" in result.stdout


def test_cli_diff_reports_missing_file_in_git_ref(tmp_path: Path) -> None:
    repo, project_relpath = _create_git_diff_fixture(tmp_path)
    assert _git(repo, "mv", str(project_relpath), "project/renamed.project.yaml").returncode == 0

    result = _run_cli(
        ["diff", "project/renamed.project.yaml", "--base-git-ref", "HEAD"],
        cwd=repo,
    )

    assert result.returncode == 2
    assert "is not present at git ref" in result.stdout


def test_cli_diff_reports_missing_git_executable(monkeypatch) -> None:
    def _raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr("arforge.cli.subprocess.run", _raise_file_not_found)
    result = RUNNER.invoke(app, ["diff", "project.yaml", "--base-git-ref", "HEAD"])

    assert result.exit_code == 2
    assert "was not found on PATH" in result.stdout
