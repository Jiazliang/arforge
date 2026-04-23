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
SAMPLE_NAMING_PROFILE = REPO_ROOT / "examples" / "validation_profiles" / "naming.yaml"
SAMPLE_STRICT_HYGIENE_PROFILE = REPO_ROOT / "examples" / "validation_profiles" / "strict_hygiene.yaml"
SAMPLE_PROFILE_FIXTURE = REPO_ROOT / "examples" / "validation_profiles" / "fixtures" / "profile_demo.project.yaml"


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


def test_profile_loader_rejects_unsupported_extra_fields_via_schema(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "TestProfile"
          mode: "core+extensions"
          severity: "warning"
        """,
    )

    with pytest.raises(ValidationProfileError) as excinfo:
        load_validation_profile(profile_path)

    assert "Additional properties are not allowed" in excinfo.value.errors[0]
    assert "severity" in excinfo.value.errors[0]


def test_profile_loader_rejects_empty_extension_rule_list_via_schema(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "TestProfile"
        extensions:
          - module: "tests.support_validation_rules"
            rules: []
        """,
    )

    with pytest.raises(ValidationProfileError) as excinfo:
        load_validation_profile(profile_path)

    assert "should be non-empty" in excinfo.value.errors[0] or "[] should be non-empty" in excinfo.value.errors[0]


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


def test_profiles_with_same_module_name_are_isolated(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()

    first_profile = _write_profile(
        first_root,
        """
        profile:
          name: "FirstProfile"
          mode: "extensions-only"
        extensions:
          - module: "shared_rules"
            rules: ["rule_project_name"]
        """,
    )
    second_profile = _write_profile(
        second_root,
        """
        profile:
          name: "SecondProfile"
          mode: "extensions-only"
        extensions:
          - module: "shared_rules"
            rules: ["rule_project_name"]
        """,
    )

    (first_root / "shared_rules.py").write_text(
        textwrap.dedent(
            """
            from arforge.semantic_validation import Finding, validation_rule

            @validation_rule(
                code="MY-001",
                name="SharedRule",
                description="First profile rule.",
                default_severity="info",
            )
            def rule_project_name(context):
                return [Finding(code="MY-001-PROJECT", severity="info", message="first-profile")]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (second_root / "shared_rules.py").write_text(
        textwrap.dedent(
            """
            from arforge.semantic_validation import Finding, validation_rule

            @validation_rule(
                code="MY-001",
                name="SharedRule",
                description="Second profile rule.",
                default_severity="info",
            )
            def rule_project_name(context):
                return [Finding(code="MY-001-PROJECT", severity="info", message="second-profile")]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    project = load_aggregator(VALID_PROJECT)
    first_report = build_semantic_report(project, profile=load_validation_profile(first_profile))
    second_report = build_semantic_report(project, profile=load_validation_profile(second_profile))

    assert [finding.message for finding in first_report.findings] == ["first-profile"]
    assert [finding.message for finding in second_report.findings] == ["second-profile"]


def test_profile_loads_rule_module_from_profile_directory(tmp_path: Path) -> None:
    profile_path = _write_profile(
        tmp_path,
        """
        profile:
          name: "LocalCustomRules"
          mode: "extensions-only"
        extensions:
          - module: "custom_rules"
            rules: ["rule_require_runnables"]
        """,
    )

    (tmp_path / "custom_rules.py").write_text(
        textwrap.dedent(
            """
            from arforge.semantic_validation import Finding, validation_rule

            @validation_rule(
                code="PRJ-210",
                name="SwcMustDeclareProvidesPort",
                description="Flags SWCs with no provides ports.",
                default_severity="warning",
            )
            def rule_require_runnables(context):
                findings = []
                for swc in sorted(context.project.swcs, key=lambda item: item.name):
                    if any(port.direction == "provides" for port in swc.ports):
                        continue
                    findings.append(
                        Finding(
                            code="PRJ-210-NO-PROVIDES-PORT",
                            severity="warning",
                            message=f"SWC '{swc.name}' declares no provides ports.",
                            location=f"swc:{swc.name}",
                        )
                    )
                return findings
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    project = load_aggregator(SAMPLE_PROFILE_FIXTURE)
    report = build_semantic_report(project, profile=load_validation_profile(profile_path))

    assert report.ruleset == "profile:LocalCustomRules"
    assert [finding.code for finding in report.findings] == ["PRJ-210-NO-PROVIDES-PORT"]
    assert [finding.location for finding in report.findings] == ["swc:SpeedMonitor"]


def test_sample_profiles_load_successfully() -> None:
    naming_profile = load_validation_profile(SAMPLE_NAMING_PROFILE)
    strict_profile = load_validation_profile(SAMPLE_STRICT_HYGIENE_PROFILE)

    assert naming_profile.mode == "extensions-only"
    assert strict_profile.mode == "core+extensions"
    assert naming_profile.extensions
    assert strict_profile.extensions


def test_sample_profile_modules_load_successfully() -> None:
    naming_profile = load_validation_profile(SAMPLE_NAMING_PROFILE)
    strict_profile = load_validation_profile(SAMPLE_STRICT_HYGIENE_PROFILE)

    naming_report = build_semantic_report(load_aggregator(VALID_PROJECT), profile=naming_profile)
    strict_report = build_semantic_report(load_aggregator(VALID_PROJECT), profile=strict_profile)

    assert naming_report.ruleset == "profile:SampleNamingConventions"
    assert strict_report.ruleset == "profile:SampleStrictHygiene"
    assert all(case.case_id.startswith("PRJ-") for case in naming_report.case_results)
    assert any(case.case_id == "PRJ-201" for case in strict_report.case_results)


def test_sample_naming_profile_flags_non_conforming_fixture() -> None:
    project = load_aggregator(SAMPLE_PROFILE_FIXTURE)
    report = build_semantic_report(project, profile=load_validation_profile(SAMPLE_NAMING_PROFILE))

    finding_codes = {finding.code for finding in report.findings}

    assert "PRJ-101-SWC-NAME" in finding_codes
    assert "PRJ-102-PORT-PREFIX" in finding_codes
    assert "PRJ-103-RUNNABLE-NAME" in finding_codes
    assert all(code.startswith("PRJ-") for code in finding_codes)
    assert "PRJ-105-INSTANCE-NAME" not in finding_codes


def test_sample_strict_hygiene_profile_changes_behavior_from_core() -> None:
    project = load_aggregator(SAMPLE_PROFILE_FIXTURE)

    baseline_report = build_semantic_report(project)
    strict_report = build_semantic_report(project, profile=load_validation_profile(SAMPLE_STRICT_HYGIENE_PROFILE))

    baseline_codes = {finding.code for finding in baseline_report.findings}
    strict_codes = {finding.code for finding in strict_report.findings}

    assert "CORE-041-SR-PROVIDES-NO-OUTGOING" in baseline_codes
    assert "CORE-042-SR-CONNECTED-REQUIRES-UNUSED" in baseline_codes
    assert "CORE-047-SR-PROVIDES-DECLARED-UNUSED" in baseline_codes

    assert "CORE-041-SR-PROVIDES-NO-OUTGOING" not in strict_codes
    assert "CORE-042-SR-CONNECTED-REQUIRES-UNUSED" not in strict_codes
    assert "CORE-047-SR-PROVIDES-DECLARED-UNUSED" not in strict_codes
    assert "PRJ-201-PORT-UNCONNECTED" in strict_codes
    assert "PRJ-202-CONNECTED-PORT-UNUSED" in strict_codes
    assert "PRJ-203-COMPOSITION-NAME" in strict_codes


def test_sample_profiles_are_deterministic() -> None:
    project = load_aggregator(SAMPLE_PROFILE_FIXTURE)
    profile = load_validation_profile(SAMPLE_STRICT_HYGIENE_PROFILE)

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
            str(SAMPLE_NAMING_PROFILE),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "summary:" in result.stdout
