"""CLI tests for `arforge validate`.

These tests focus on user-visible validation behavior: exit codes, summary
output, verbose modes, warning/error presentation, and profile support.
"""

from __future__ import annotations

import subprocess
import sys

from tests._shared import (
    CONNECTED_UNUSED_MODE_SWITCH_PROJECT,
    CS_SERVER_WARNING_PROJECT,
    ERROR_PROJECT,
    MIXED_PROJECT,
    REPO_ROOT,
    SAMPLE_NAMING_PROFILE,
    SR_N_TO_1_PROJECT,
    VALID_PROJECT,
    WARNING_ONLY_PROJECT,
    UNUSED_MODE_GROUP_PROJECT,
)

def test_cli_validate_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(VALID_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

def test_cli_validate_verbose_includes_case_name() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(VALID_PROJECT), "-v"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CORE-021 PortInterfaceReferences RUN OK" in result.stdout

def test_cli_validate_extra_verbose_includes_case_description() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(VALID_PROJECT), "-vv"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CORE-021 PortInterfaceReferences" in result.stdout
    assert "Checks that each SWC port references an existing interface and uses the" in result.stdout
    assert "expected kind." in result.stdout

def test_cli_validate_main_example_has_clean_summary() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(VALID_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "errors: 0" in result.stdout
    assert "warnings: 0" in result.stdout

def test_cli_validate_warning_only_project_shows_warning_and_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(WARNING_ONLY_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING CORE-042-SR-CONNECTED-REQUIRES-UNUSED" in result.stdout
    assert "errors: 0" in result.stdout
    assert "warnings: 2" in result.stdout

def test_cli_validate_sr_n_to_1_project_warns_and_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(SR_N_TO_1_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING CORE-045-SR-N-TO-1" in result.stdout
    assert "SrRequester_1.Rp_VehicleSpeed" in result.stdout
    assert "errors: 0" in result.stdout
    assert "warnings: 1" in result.stdout

def test_cli_validate_sr_n_to_1_verbose_includes_case_and_finding_count() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(SR_N_TO_1_PROJECT), "-v"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CORE-045 SenderReceiverMultiplicity WARNING" in result.stdout
    assert "findings=1" in result.stdout

def test_cli_validate_cs_server_unconnected_binding_warns_and_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(CS_SERVER_WARNING_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING CORE-043-CS-OIE-UNCONNECTED" in result.stdout
    assert "errors: 0" in result.stdout

def test_cli_validate_error_project_shows_error_and_fails() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(ERROR_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "ERROR" in result.stdout

def test_cli_validate_error_project_verbose_marks_failing_case_as_error() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(ERROR_PROJECT), "-v"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "CORE-022 RunnableAccessSemantics ERROR" in result.stdout
    assert "errors: " in result.stdout

def test_cli_validate_mixed_project_shows_warnings_and_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(MIXED_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING CORE-041-SR-READ-UNCONNECTED" in result.stdout
    assert "WARNING CORE-041-SR-REQUIRES-NO-INCOMING" in result.stdout

def test_cli_validate_unused_mode_group_warns_and_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(UNUSED_MODE_GROUP_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING CORE-014-MDG-DECLARED-UNUSED" in result.stdout
    assert "Mdg_UnusedPowerState" in result.stdout
    assert "errors: 0" in result.stdout
    assert "warnings: 1" in result.stdout

def test_cli_validate_connected_unused_mode_switch_warns_and_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(CONNECTED_UNUSED_MODE_SWITCH_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNING CORE-048-MS-CONNECTED-REQUIRES-UNUSED" in result.stdout
    assert "SpeedDisplay_1.Rp_PowerState" in result.stdout
    assert "errors: 0" in result.stdout

def test_cli_validate_supports_profile_option() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arforge.cli",
            "validate",
            str(VALID_PROJECT),
            "--profile",
            str(SAMPLE_NAMING_PROFILE),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "summary:" in result.stdout
