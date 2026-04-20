from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from arforge.validate import build_semantic_report, load_aggregator
from arforge.validation_profile import ValidationProfileError, load_validation_profile


REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_PROJECT = REPO_ROOT / "examples" / "autosar.project.yaml"
WARNING_PROJECT = REPO_ROOT / "examples" / "invalid" / "project_sr_read_unconnected.yaml"


def _write_profile(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return path


def test_profile_loader_accepts_valid_profile(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "TestProfile"
          mode: "core+extensions"
        rules:
          enable: ["MY-001"]
          disable: ["CORE-041"]
        extensions:
          - module: "tests.support_validation_rules"
            rules: ["rule_project_name"]
        """,
    )

    profile = load_validation_profile(profile_path)

    assert profile.name == "TestProfile"
    assert profile.mode == "core+extensions"
    assert profile.enable == ("MY-001",)
    assert profile.disable == ("CORE-041",)
    assert profile.extensions[0].module == "tests.support_validation_rules"
    assert profile.extensions[0].rules == ("rule_project_name",)


def test_profile_loader_rejects_invalid_structure(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: ""
          mode: "broken"
        rules:
          enable: "MY-001"
        """,
    )

    with pytest.raises(ValidationProfileError) as excinfo:
        load_validation_profile(profile_path)

    assert "profile.name" in excinfo.value.errors[0] or "profile.mode" in excinfo.value.errors[0]


def test_profile_fails_clearly_for_missing_extension_module(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "BrokenModule"
          mode: "core+extensions"
        extensions:
          - module: "missing_validation_module"
            rules: ["rule_project_name"]
        """,
    )

    profile = load_validation_profile(profile_path)
    project = load_aggregator(VALID_PROJECT)

    with pytest.raises(ValidationProfileError) as excinfo:
        build_semantic_report(project, profile=profile)

    assert "Failed to import extension module 'missing_validation_module'" in excinfo.value.errors[0]


def test_profile_fails_clearly_for_missing_rule_function(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "BrokenRuleFunction"
          mode: "core+extensions"
        extensions:
          - module: "tests.support_validation_rules"
            rules: ["rule_does_not_exist"]
        """,
    )

    profile = load_validation_profile(profile_path)
    project = load_aggregator(VALID_PROJECT)

    with pytest.raises(ValidationProfileError) as excinfo:
        build_semantic_report(project, profile=profile)

    assert "does not define rule function 'rule_does_not_exist'" in excinfo.value.errors[0]


def test_profile_executes_extension_rules(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "ExtensionRules"
          mode: "core+extensions"
        extensions:
          - module: "tests.support_validation_rules"
            rules:
              - "rule_project_name"
              - "rule_component_count"
        """,
    )

    profile = load_validation_profile(profile_path)
    project = load_aggregator(VALID_PROJECT)
    report = build_semantic_report(project, profile=profile)

    assert report.ruleset == "profile:ExtensionRules"
    assert "MY-001-PROJECT" in {finding.code for finding in report.findings}
    assert "MY-002-COMPONENT-COUNT" in {finding.code for finding in report.findings}


def test_profile_can_disable_core_rules(tmp_path: Path) -> None:
    project = load_aggregator(WARNING_PROJECT)
    baseline_report = build_semantic_report(project)
    assert "CORE-041-SR-READ-UNCONNECTED" in {finding.code for finding in baseline_report.findings}

    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "DisableCoreRule"
          mode: "core+extensions"
        rules:
          disable: ["CORE-041"]
        extensions: []
        """,
    )

    profile = load_validation_profile(profile_path)
    report = build_semantic_report(project, profile=profile)

    assert "CORE-041-SR-READ-UNCONNECTED" not in {finding.code for finding in report.findings}


def test_profile_extensions_only_mode_excludes_core_rules(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "ExtensionsOnly"
          mode: "extensions-only"
        extensions:
          - module: "tests.support_validation_rules"
            rules: ["rule_project_name"]
        """,
    )

    profile = load_validation_profile(profile_path)
    project = load_aggregator(WARNING_PROJECT)
    report = build_semantic_report(project, profile=profile)

    assert {finding.code for finding in report.findings} == {"MY-001-PROJECT"}
    assert all(case.case_id.startswith("MY-") for case in report.case_results)


def test_profile_results_are_deterministic(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "DeterministicProfile"
          mode: "core+extensions"
        extensions:
          - module: "tests.support_validation_rules"
            rules:
              - "rule_component_count"
              - "rule_project_name"
        """,
    )

    profile = load_validation_profile(profile_path)
    project = load_aggregator(VALID_PROJECT)

    report_one = build_semantic_report(project, profile=profile)
    report_two = build_semantic_report(project, profile=profile)

    findings_one = [(finding.code, finding.message, finding.location) for finding in report_one.findings]
    findings_two = [(finding.code, finding.message, finding.location) for finding in report_two.findings]
    cases_one = [case.case_id for case in report_one.case_results]
    cases_two = [case.case_id for case in report_two.case_results]

    assert findings_one == findings_two
    assert cases_one == cases_two


def test_cli_validate_supports_profile_option() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arforge.cli",
            "validate",
            str(VALID_PROJECT),
            "--profile",
            str(REPO_ROOT / "examples" / "validation_profiles" / "profile.yaml"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "summary:" in result.stdout
