"""Tests for built-in semantic validation rules.

These tests cover core rule findings, warning/error behavior, invalid fixture
expectations, and deterministic reporting across the built-in ruleset.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from arforge.model import ModeCondition, ModeDeclaration
from arforge.semantic_validation import Finding, FindingSeverity
from arforge.validate import ValidationError, build_semantic_report, load_aggregator, load_and_validate_aggregator
from tests._shared import (
    CONNECTED_UNUSED_MODE_SWITCH_PROJECT,
    CS_SERVER_WARNING_PROJECT,
    ERROR_PROJECT,
    INVALID_DIR,
    MIXED_PROJECT,
    MODES_FEATURE_PROJECT,
    SR_N_TO_1_PROJECT,
    SR_ONE_TO_MANY_PROJECT,
    UNUSED_MODE_GROUP_PROJECT,
    VALID_PROJECT,
    WARNING_ONLY_PROJECT,
)


def _replace_runnable(project, swc_name: str, runnable_name: str, **changes):
    return replace(
        project,
        swcs=[
            replace(
                swc,
                runnables=[
                    replace(runnable, **changes) if swc.name == swc_name and runnable.name == runnable_name else runnable
                    for runnable in swc.runnables
                ],
            )
            for swc in project.swcs
        ],
    )

def test_finding_defaults_to_error_severity() -> None:
    finding = Finding(code="CORE-999", message="Compatibility default.")

    assert finding.severity == FindingSeverity.ERROR

def test_semantic_validation_flags_missing_on_transition_value_for_explicit_order_group() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    group = project.modeDeclarationGroups[0]
    report = build_semantic_report(
        replace(project, modeDeclarationGroups=[replace(group, onTransitionValue=None)]),
        ruleset="core",
    )

    error_codes = {finding.code for finding in report.error_findings()}
    assert "CORE-012-MDG-EXPLICIT-ORDER-ON-TRANSITION" in error_codes

def test_semantic_validation_flags_missing_mode_value_for_explicit_order_group() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    group = project.modeDeclarationGroups[0]
    report = build_semantic_report(
        replace(
            project,
            modeDeclarationGroups=[
                replace(
                    group,
                    modes=[
                        ModeDeclaration(name="OFF", value=0),
                        ModeDeclaration(name="ON"),
                        ModeDeclaration(name="SLEEP", value=2),
                    ],
                )
            ],
        ),
        ruleset="core",
    )

    error_codes = {finding.code for finding in report.error_findings()}
    assert "CORE-012-MDG-EXPLICIT-ORDER-MODE-VALUE" in error_codes

def test_semantic_validation_flags_duplicate_mode_values() -> None:
    project = load_aggregator(INVALID_DIR / "project_mode_group_duplicate_values.yaml")
    report = build_semantic_report(project, ruleset="core")

    error_codes = {finding.code for finding in report.error_findings()}
    assert "CORE-012-MDG-DUPLICATE-VALUE" in error_codes

def test_system_connector_validation_covers_subcomposition_boundary_ports() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    bad_project = replace(
        project,
        system=replace(
            project.system,
            composition=replace(
                project.system.composition,
                connectors=[
                    replace(
                        project.system.composition.connectors[0],
                        from_instance="DiagManager_0",
                        from_port="Rp_VehicleSpeed",
                        to_instance="SpeedCluster_0",
                        to_port="Pp_VehicleSpeedOut",
                    )
                ],
            ),
        ),
    )

    report = build_semantic_report(bad_project, ruleset="core")
    error_codes = {finding.code for finding in report.error_findings()}

    assert "CORE-040-FROM-DIRECTION" in error_codes
    assert "CORE-040-TO-DIRECTION" in error_codes

def test_warning_only_project_passes_validation_and_preserves_warning_report() -> None:
    project = load_and_validate_aggregator(WARNING_ONLY_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    assert any(finding.severity == FindingSeverity.WARNING for finding in report.findings)

def test_error_project_fails_validation() -> None:
    with pytest.raises(ValidationError):
        load_and_validate_aggregator(ERROR_PROJECT)

def test_mixed_warning_project_passes_and_reports_warnings() -> None:
    project = load_aggregator(MIXED_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    assert any(finding.severity == FindingSeverity.WARNING for finding in report.findings)
    load_and_validate_aggregator(MIXED_PROJECT)

def test_sr_one_to_many_project_passes_without_multiplicity_warning() -> None:
    project = load_and_validate_aggregator(SR_ONE_TO_MANY_PROJECT)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == FindingSeverity.WARNING}

    assert report.error_findings() == []
    assert "CORE-045-SR-N-TO-1" not in warning_codes

def test_sr_n_to_1_project_passes_validation_and_reports_warning() -> None:
    project = load_and_validate_aggregator(SR_N_TO_1_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    multiplicity_findings = [finding for finding in report.findings if finding.code == "CORE-045-SR-N-TO-1"]
    assert len(multiplicity_findings) == 1
    assert multiplicity_findings[0].severity == FindingSeverity.WARNING
    assert multiplicity_findings[0].message == (
        "SenderReceiver requires port 'SrRequester_1.Rp_VehicleSpeed' is connected to multiple providers: "
        "['SrProvider_1.Pp_VehicleSpeed', 'SrProvider_2.Pp_VehicleSpeed']. "
        "AUTOSAR allows this, but arbitration semantics may be unclear."
    )

def test_cs_server_unconnected_binding_passes_validation_and_reports_warning() -> None:
    project = load_and_validate_aggregator(CS_SERVER_WARNING_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    oie_findings = [finding for finding in report.findings if finding.code == "CORE-043-CS-OIE-UNCONNECTED"]
    assert oie_findings
    assert all(finding.severity == FindingSeverity.WARNING for finding in oie_findings)

def test_validation_report_summary_counts_are_grouped_by_severity() -> None:
    project = load_aggregator(MIXED_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.severity_counts() == {"error": 0, "warning": 5, "info": 0}

def test_main_example_has_no_declared_unused_port_findings() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}

    assert "CORE-047-SR-PROVIDES-DECLARED-UNUSED" not in warning_codes
    assert "CORE-047-SR-REQUIRES-DECLARED-UNUSED" not in warning_codes
    assert "CORE-047-CS-PROVIDES-DECLARED-UNUSED" not in warning_codes
    assert "CORE-047-CS-REQUIRES-DECLARED-UNUSED" not in warning_codes
    assert "CORE-047-MS-REQUIRES-DECLARED-UNUSED" not in warning_codes

def test_main_example_has_no_connected_unused_mode_switch_requires_warning() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}

    assert "CORE-048-MS-CONNECTED-REQUIRES-UNUSED" not in warning_codes

def test_main_example_has_no_unused_mode_declaration_group_warning() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}

    assert "CORE-014-MDG-DECLARED-UNUSED" not in warning_codes

def test_unused_mode_group_project_passes_validation_and_reports_warning() -> None:
    project = load_and_validate_aggregator(UNUSED_MODE_GROUP_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    unused_group_findings = [finding for finding in report.findings if finding.code == "CORE-014-MDG-DECLARED-UNUSED"]
    assert len(unused_group_findings) == 1
    assert unused_group_findings[0].severity == FindingSeverity.WARNING
    assert unused_group_findings[0].message == (
        "ModeDeclarationGroup 'Mdg_UnusedPowerState' is declared but not referenced by any ModeSwitchInterface."
    )

def test_connected_unused_mode_switch_project_passes_validation_and_reports_warning() -> None:
    project = load_and_validate_aggregator(CONNECTED_UNUSED_MODE_SWITCH_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    connected_findings = [
        finding for finding in report.findings if finding.code == "CORE-048-MS-CONNECTED-REQUIRES-UNUSED"
    ]
    assert len(connected_findings) == 1
    assert connected_findings[0].severity == FindingSeverity.WARNING
    assert connected_findings[0].message == (
        "Connected modeSwitch requires port 'SpeedDisplay_1.Rp_PowerState' is not used by any runnable modeSwitchEvents or modeConditions."
    )

def test_mode_conditions_unknown_port_emits_error() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = _replace_runnable(
        project,
        "PowerStateUser",
        "Runnable_ProcessWhenActive",
        modeConditions=[ModeCondition(port="Rp_UnknownMode", mode="ON")],
    )

    report = build_semantic_report(project, ruleset="core")

    assert "CORE-029-MODE-CONDITION-PORT-UNKNOWN" in {finding.code for finding in report.error_findings()}

def test_mode_conditions_non_mode_switch_port_emits_error() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    project = _replace_runnable(
        project,
        "SpeedDisplay",
        "Runnable_ReadVehicleSpeed",
        modeConditions=[ModeCondition(port="Rp_VehicleSpeed", mode="ON")],
    )

    report = build_semantic_report(project, ruleset="core")

    assert "CORE-029-MODE-CONDITION-INTERFACE-TYPE" in {finding.code for finding in report.error_findings()}

def test_mode_conditions_provides_port_emits_error() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    project = _replace_runnable(
        project,
        "SpeedSensor",
        "Runnable_PublishVehicleSpeed",
        modeConditions=[ModeCondition(port="Pp_PowerState", mode="ON")],
    )

    report = build_semantic_report(project, ruleset="core")

    assert "CORE-029-MODE-CONDITION-DIRECTION" in {finding.code for finding in report.error_findings()}

def test_mode_conditions_unknown_mode_emits_error() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = _replace_runnable(
        project,
        "PowerStateUser",
        "Runnable_ProcessWhenActive",
        modeConditions=[ModeCondition(port="Rp_PowerState", mode="DIAG")],
    )

    report = build_semantic_report(project, ruleset="core")

    assert "CORE-029-MODE-CONDITION-UNKNOWN-MODE" in {finding.code for finding in report.error_findings()}

def test_mode_conditions_duplicate_emits_single_warning_deterministically() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = _replace_runnable(
        project,
        "PowerStateUser",
        "Runnable_ProcessWhenActive",
        modeConditions=[
            ModeCondition(port="Rp_PowerState", mode="ON"),
            ModeCondition(port="Rp_PowerState", mode="ON"),
        ],
    )

    report = build_semantic_report(project, ruleset="core")

    duplicate_findings = [
        finding for finding in report.findings if finding.code == "CORE-029-MODE-CONDITION-DUPLICATE"
    ]
    assert len(duplicate_findings) == 1
    assert duplicate_findings[0].severity == FindingSeverity.WARNING

def test_declared_unused_mode_switch_port_counts_mode_conditions_as_usage() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = _replace_runnable(project, "PowerStateUser", "Runnable_OnPowerOn", modeSwitchEvents=[], modeConditions=[])
    project = _replace_runnable(project, "PowerStateUser", "Runnable_OnSleep", modeSwitchEvents=[])

    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == FindingSeverity.WARNING}

    assert "CORE-047-MS-REQUIRES-DECLARED-UNUSED" not in warning_codes

def test_connected_mode_switch_port_counts_mode_conditions_as_usage() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = _replace_runnable(project, "PowerStateUser", "Runnable_OnPowerOn", modeSwitchEvents=[], modeConditions=[])
    project = _replace_runnable(project, "PowerStateUser", "Runnable_OnSleep", modeSwitchEvents=[])

    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == FindingSeverity.WARNING}

    assert "CORE-048-MS-CONNECTED-REQUIRES-UNUSED" not in warning_codes

def test_mode_conditions_on_unconnected_mode_switch_port_emit_warning() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = replace(
        project,
        system=replace(
            project.system,
            composition=replace(project.system.composition, connectors=[]),
        ),
    )

    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == FindingSeverity.WARNING}

    assert "CORE-048-MS-MODE-CONDITION-UNCONNECTED" in warning_codes

def test_mode_conditions_on_init_event_emit_error() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    project = _replace_runnable(
        project,
        "PowerStateUser",
        "Runnable_OnSleep",
        initEvent=True,
        modeSwitchEvents=[],
        modeConditions=[ModeCondition(port="Rp_PowerState", mode="SLEEP")],
    )

    report = build_semantic_report(project, ruleset="core")

    assert "CORE-029-MODE-CONDITION-INIT-EVENT-UNSUPPORTED" in {
        finding.code for finding in report.error_findings()
    }

@pytest.mark.parametrize(
    ("fixture_name", "expected_code"),
    [
        ("project_data_receive_event_unknown_port.yaml", "CORE-027-DRE-UNKNOWN-PORT"),
        ("project_data_receive_event_unknown_dataelement.yaml", "CORE-027-DRE-UNKNOWN-DATAELEMENT"),
        ("project_data_receive_event_on_provides_port.yaml", "CORE-027-DRE-DIRECTION"),
        ("project_data_receive_event_on_client_server_port.yaml", "CORE-027-DRE-INTERFACE-TYPE"),
        ("project_cs_call_unconnected.yaml", "CORE-043-CS-CALL-UNCONNECTED"),
        ("project_cs_duplicate_port_pair.yaml", "CORE-040-CS-DUPLICATE-PORT-PAIR"),
        ("project_cs_interface_mismatch.yaml", "CORE-040-INTERFACE-MISMATCH"),
        ("project_cs_wrong_directions.yaml", "CORE-040-FROM-DIRECTION"),
        ("project_impl_array_application_ref.yaml", "CORE-010-ARRAY-APPLICATION-TYPE"),
        ("project_impl_array_unknown_element_type.yaml", "CORE-010-ARRAY-UNKNOWN-ELEMENT-TYPE"),
        ("project_struct_cycle.yaml", "CORE-010-STRUCT-CYCLE"),
        ("project_struct_duplicate_field_names.yaml", "CORE-010-STRUCT-DUPLICATE-FIELD"),
        ("project_struct_unknown_nested_type.yaml", "CORE-010-STRUCT-UNKNOWN-TYPE"),
        ("project_sr_duplicate_port_pair.yaml", "CORE-040-SR-DUPLICATE-PORT-PAIR"),
        ("project_mode_group_duplicate_modes.yaml", "CORE-012-MDG-DUPLICATE-MODE"),
        ("project_mode_group_duplicate_values.yaml", "CORE-012-MDG-DUPLICATE-VALUE"),
        ("project_mode_group_bad_initial_mode.yaml", "CORE-013-MDG-INITIAL-MODE"),
        ("project_mode_switch_interface_unknown_mode_group.yaml", "CORE-010-MS-UNKNOWN-MODE-GROUP-REF"),
        ("project_mode_switch_event_unknown_port.yaml", "CORE-028-MSE-UNKNOWN-PORT"),
        ("project_mode_switch_event_on_provides_port.yaml", "CORE-028-MSE-DIRECTION"),
        ("project_mode_switch_event_on_non_mode_switch_port.yaml", "CORE-028-MSE-INTERFACE-TYPE"),
        ("project_mode_switch_event_unknown_mode.yaml", "CORE-028-MSE-UNKNOWN-MODE"),
        ("project_unknown_subcomposition_type.yaml", "CORE-030-UNKNOWN-COMPONENT-TYPE"),
        ("project_subcomposition_unknown_swc_type.yaml", "CORE-031-UNKNOWN-SWC-TYPE"),
        ("project_subcomposition_duplicate_component_names.yaml", "CORE-001-SUBCOMPOSITION-INSTANCE-DUPLICATE"),
        ("project_subcomposition_nested_not_allowed.yaml", "CORE-031-NESTED-SUBCOMPOSITION"),
        ("project_subcomposition_duplicate_port_names.yaml", "CORE-033-PORT-DUPLICATE"),
        ("project_subcomposition_unknown_port_interface.yaml", "CORE-033-UNKNOWN-INTERFACE-REF"),
        ("project_subcomposition_delegation_unknown_outer_port.yaml", "CORE-034-UNKNOWN-OUTER-PORT"),
        ("project_subcomposition_delegation_unknown_inner_instance.yaml", "CORE-034-UNKNOWN-INNER-INSTANCE"),
        ("project_subcomposition_delegation_unknown_inner_port.yaml", "CORE-034-UNKNOWN-INNER-PORT"),
        ("project_subcomposition_delegation_direction_mismatch.yaml", "CORE-034-DIRECTION-MISMATCH"),
        ("project_subcomposition_delegation_interface_mismatch.yaml", "CORE-034-INTERFACE-MISMATCH"),
        ("project_subcomposition_delegation_duplicate.yaml", "CORE-034-DUPLICATE"),
        ("project_comspec_init_value_unsupported.yaml", "CORE-025-SR-COMSPEC-INITVALUE-DIRECTION"),
    ],
)
def test_data_receive_event_invalid_fixtures_emit_expected_codes(fixture_name: str, expected_code: str) -> None:
    project = load_aggregator(INVALID_DIR / fixture_name)
    report = build_semantic_report(project, ruleset="core")
    error_codes = {finding.code for finding in report.error_findings()}
    assert expected_code in error_codes

@pytest.mark.parametrize(
    ("fixture_name", "expected_warning"),
    [
        ("project_sr_read_unconnected.yaml", "CORE-041-SR-READ-UNCONNECTED"),
        ("project_sr_write_unconnected.yaml", "CORE-041-SR-WRITE-UNCONNECTED"),
    ],
)
def test_sr_connectivity_warning_only_fixtures_emit_expected_usage_warnings(
    fixture_name: str,
    expected_warning: str,
) -> None:
    project = load_aggregator(INVALID_DIR / fixture_name)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}
    assert expected_warning in warning_codes

@pytest.mark.parametrize(
    ("fixture_name", "expected_warning"),
    [
        ("project_declared_unused_sr_provides.yaml", "CORE-047-SR-PROVIDES-DECLARED-UNUSED"),
        ("project_connected_sr_port_unused.yaml", "CORE-047-SR-REQUIRES-DECLARED-UNUSED"),
        ("project_declared_unused_cs_requires.yaml", "CORE-047-CS-REQUIRES-DECLARED-UNUSED"),
        ("project_declared_unused_cs_provides.yaml", "CORE-047-CS-PROVIDES-DECLARED-UNUSED"),
        ("project_declared_unused_mode_requires.yaml", "CORE-047-MS-REQUIRES-DECLARED-UNUSED"),
        ("project_connected_mode_switch_port_unused.yaml", "CORE-048-MS-CONNECTED-REQUIRES-UNUSED"),
        ("project_unused_mode_group.yaml", "CORE-014-MDG-DECLARED-UNUSED"),
        ("project_sr_n_to_1_warning.yaml", "CORE-045-SR-N-TO-1"),
        ("project_sr_read_unconnected.yaml", "CORE-041-SR-REQUIRES-NO-INCOMING"),
        ("project_sr_write_unconnected.yaml", "CORE-041-SR-PROVIDES-NO-OUTGOING"),
        ("project_cs_call_unconnected.yaml", "CORE-044-CS-REQUIRES-NO-CONNECTOR"),
        ("project_connected_sr_port_unused.yaml", "CORE-042-SR-CONNECTED-REQUIRES-UNUSED"),
        ("project_cs_server_oie_unconnected.yaml", "CORE-043-CS-OIE-UNCONNECTED"),
    ],
)
def test_invalid_project_fixtures_emit_expected_warnings(fixture_name: str, expected_warning: str) -> None:
    project = load_aggregator(INVALID_DIR / fixture_name)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}
    assert expected_warning in warning_codes

def test_open_mode_switch_ports_emit_connectivity_warnings() -> None:
    project = load_aggregator(INVALID_DIR / "project_mode_switch_unconnected.yaml")
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}

    assert "CORE-046-MS-PROVIDES-NO-OUTGOING" in warning_codes
    assert "CORE-046-MS-REQUIRES-NO-INCOMING" in warning_codes

def test_sr_timing_equal_fixture_has_no_timing_mismatch_findings() -> None:
    project = load_aggregator(INVALID_DIR / "project_sr_timing_equal.yaml")
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}
    assert "CORE-050" not in warning_codes
    assert "CORE-051" not in warning_codes

@pytest.mark.parametrize(
    ("fixture_name", "expected_warning"),
    [
        ("project_sr_consumer_faster.yaml", "CORE-050"),
        ("project_sr_producer_faster.yaml", "CORE-051"),
    ],
)
def test_sr_timing_warning_fixtures_emit_expected_codes(fixture_name: str, expected_warning: str) -> None:
    project = load_aggregator(INVALID_DIR / fixture_name)
    report = build_semantic_report(project, ruleset="core")
    warning_codes = {finding.code for finding in report.findings if finding.severity == "warning"}
    assert expected_warning in warning_codes
