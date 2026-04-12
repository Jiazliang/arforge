from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from arforge.codegen import write_code_outputs
from arforge.exporter import write_outputs, write_outputs_with_report
from arforge.diagrams import build_diagram_views, write_diagram_outputs
from arforge.model import (
    ComponentPrototype,
    Composition,
    Interface,
    OperationInvokedEvent,
    Port,
    Project,
    Runnable,
    Swc,
    System,
)
from arforge.semantic_validation import Finding, FindingSeverity
from arforge.validate import ValidationError, build_semantic_report, load_aggregator, load_and_validate_aggregator


REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_PROJECT = REPO_ROOT / "examples" / "autosar.project.yaml"
INVALID_DIR = REPO_ROOT / "examples" / "invalid"
SHARED_EXAMPLE_OUTPUT = "DEMO_SharedTypes.arxml"
SUBCOMPOSITION_EXAMPLE_OUTPUT = "SubComposition_SpeedCluster.arxml"
SYSTEM_EXAMPLE_OUTPUT = "DemoSystem.arxml"
PLANTUML_DIAGRAM_OUTPUTS = [
    "composition_DemoSystem.puml",
    "subcomposition_SubComposition_SpeedCluster.puml",
    "interfaces_wiring.puml",
    "interfaces_contracts.puml",
    "behavior_DiagManager.puml",
    "behavior_SpeedDisplay.puml",
    "behavior_SpeedSensor.puml",
]
WARNING_ONLY_PROJECT = INVALID_DIR / "project_connected_sr_port_unused.yaml"
ERROR_PROJECT = INVALID_DIR / "project_bad_runnable_access.yaml"
MIXED_PROJECT = INVALID_DIR / "project_sr_read_unconnected.yaml"
CS_SERVER_WARNING_PROJECT = INVALID_DIR / "project_cs_server_oie_unconnected.yaml"
UNUSED_MODE_GROUP_PROJECT = INVALID_DIR / "project_unused_mode_group.yaml"
CONNECTED_UNUSED_MODE_SWITCH_PROJECT = INVALID_DIR / "project_connected_mode_switch_port_unused.yaml"
SR_ONE_TO_MANY_PROJECT = INVALID_DIR / "project_sr_one_to_many_valid.yaml"
SR_N_TO_1_PROJECT = INVALID_DIR / "project_sr_n_to_1_warning.yaml"


def _is_project_fixture(path: Path) -> bool:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return isinstance(data, dict) and "autosar" in data and "inputs" in data


def _invalid_project_fixtures() -> list[Path]:
    non_error_fixtures = {
        "project_connected_sr_port_unused.yaml",
        "project_cs_server_oie_unconnected.yaml",
        "project_declared_unused_cs_provides.yaml",
        "project_declared_unused_cs_requires.yaml",
        "project_declared_unused_mode_requires.yaml",
        "project_declared_unused_sr_provides.yaml",
        "project_connected_mode_switch_port_unused.yaml",
        "project_mode_switch_unconnected.yaml",
        "project_unused_mode_group.yaml",
        "project_sr_n_to_1_warning.yaml",
        "project_sr_read_unconnected.yaml",
        "project_sr_consumer_faster.yaml",
        "project_sr_producer_faster.yaml",
        "project_sr_timing_equal.yaml",
        "project_sr_write_unconnected.yaml",
        "project_sr_one_to_many_valid.yaml",
    }
    fixtures = [
        p
        for p in sorted(INVALID_DIR.glob("*.yaml"))
        if _is_project_fixture(p) and p.name not in non_error_fixtures
    ]
    return fixtures


def test_validate_main_example_passes() -> None:
    load_and_validate_aggregator(VALID_PROJECT)


def test_finding_defaults_to_error_severity() -> None:
    finding = Finding(code="CORE-999", message="Compatibility default.")

    assert finding.severity == FindingSeverity.ERROR


def test_main_example_descriptions_are_loaded_into_model_ir() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    assert next(interface for interface in project.interfaces if interface.name == "If_VehicleSpeed").description == (
        "Sender-receiver interface for the current vehicle speed."
    )
    power_state_interface = next(interface for interface in project.interfaces if interface.name == "If_PowerState")
    assert power_state_interface.description == "Mode switch interface for ECU power state."
    assert power_state_interface.modeGroupRef == "Mdg_PowerState"
    assert next(swc for swc in project.swcs if swc.name == "SpeedSensor").description == (
        "SWC type that reacts to the external power-state input and publishes the current vehicle speed."
    )
    assert next(swc for swc in project.swcs if swc.name == "SpeedDisplay").description == (
        "SWC type that reads vehicle speed through explicit, implicit, and queued receiver semantics."
    )
    provided_mode_port = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedSensor"
        for port in swc.ports
        if port.name == "Pp_PowerState"
    )
    assert provided_mode_port.description == "Provided mode switch port forwarded to the internal display."
    assert provided_mode_port.interfaceType == "modeSwitch"
    power_state_input = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedSensor"
        for port in swc.ports
        if port.name == "Rp_PowerStateIn"
    )
    assert power_state_input.description == "Required mode switch port delegated from the subcomposition boundary."
    speed_port = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedDisplay"
        for port in swc.ports
        if port.name == "Rp_VehicleSpeed"
    )
    assert speed_port.description == "Required sender-receiver port for receiving speed."
    power_state_port = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedDisplay"
        for port in swc.ports
        if port.name == "Rp_PowerState"
    )
    assert power_state_port.description == "Required mode switch port for ECU power state."
    assert power_state_port.interfaceType == "modeSwitch"
    assert power_state_port.modeGroupRef == "Mdg_PowerState"
    forwarded_speed_port = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedDisplay"
        for port in swc.ports
        if port.name == "Pp_VehicleSpeedOut"
    )
    assert forwarded_speed_port.description == "Provided sender-receiver port delegated to the subcomposition boundary."
    on_power_on = next(
        runnable
        for swc in project.swcs
        if swc.name == "SpeedDisplay"
        for runnable in swc.runnables
        if runnable.name == "Runnable_OnPowerOn"
    )
    assert [(event.port, event.mode) for event in on_power_on.modeSwitchEvents] == [("Rp_PowerState", "ON")]
    assert next(data_type for data_type in project.applicationDataTypes if data_type.name == "App_VehicleSpeed").description == (
        "Vehicle speed value shared between the demo SWC types."
    )
    assert next(data_type for data_type in project.implementationDataTypes if data_type.name == "Impl_VehicleSpeed_U16").description == (
        "Raw implementation type for a vehicle speed sample."
    )
    assert next(compu for compu in project.compuMethods if compu.name == "CM_VehicleSpeed_Kph").description == (
        "Identity scaling for the demo vehicle speed value."
    )
    assert next(subcomposition for subcomposition in project.subcompositions if subcomposition.name == "SubComposition_SpeedCluster").description == (
        "Reusable subcomposition that accepts a boundary power-state input, keeps the sensor-to-display wiring internal, and exposes a boundary speed output."
    )
    subcomposition = next(
        subcomposition for subcomposition in project.subcompositions if subcomposition.name == "SubComposition_SpeedCluster"
    )
    assert [port.name for port in subcomposition.ports] == ["Rp_PowerStateIn", "Pp_VehicleSpeedOut"]
    assert next(port for port in subcomposition.ports if port.name == "Rp_PowerStateIn").interfaceType == "modeSwitch"
    assert next(port for port in subcomposition.ports if port.name == "Pp_VehicleSpeedOut").interfaceType == "senderReceiver"
    assert [(connector.outer_port, connector.inner_ref) for connector in subcomposition.delegationConnectors] == [
        ("Rp_PowerStateIn", "SpeedSensor_1.Rp_PowerStateIn"),
        ("Pp_VehicleSpeedOut", "SpeedDisplay_1.Pp_VehicleSpeedOut"),
    ]
    assert project.system.description == (
        "Demo AUTOSAR system showing one standalone atomic SWC connected to one reusable subcomposition through composition boundary ports."
    )


def test_main_example_mode_declaration_group_is_loaded_into_model_ir() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    assert [group.name for group in project.modeDeclarationGroups] == ["Mdg_PowerState"]
    assert project.modeDeclarationGroups[0].description == "Power state modes for the ECU."
    assert project.modeDeclarationGroups[0].initialMode == "OFF"
    assert [mode.name for mode in project.modeDeclarationGroups[0].modes] == ["OFF", "ON", "SLEEP"]


def _extract_r_port_fragment(xml: str, port_name: str) -> str:
    match = re.search(
        rf"<R-PORT-PROTOTYPE>\s*<SHORT-NAME>{re.escape(port_name)}</SHORT-NAME>(.*?)</R-PORT-PROTOTYPE>",
        xml,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing R-PORT-PROTOTYPE for {port_name}"
    return match.group(1)


def _extract_element_fragment(xml: str, tag_pattern: str, short_name: str) -> str:
    match = re.search(
        rf"<(?:{tag_pattern})>\s*<SHORT-NAME>{re.escape(short_name)}</SHORT-NAME>(.*?)</(?:{tag_pattern})>",
        xml,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing element {short_name} for tag pattern {tag_pattern}"
    return match.group(0)


def _extract_internal_behavior_fragment(xml: str, swc_name: str) -> str:
    match = re.search(
        rf"<SWC-INTERNAL-BEHAVIOR>\s*<SHORT-NAME>IB_{re.escape(swc_name)}</SHORT-NAME>(.*?)</SWC-INTERNAL-BEHAVIOR>",
        xml,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing internal behavior for {swc_name}"
    return match.group(0)


def _normalize_xml_fragment(xml: str) -> str:
    return re.sub(r">\s+<", "><", xml).strip()


@pytest.mark.parametrize(
    "fixture_path",
    _invalid_project_fixtures(),
    ids=lambda p: p.name,
)
def test_invalid_project_fixtures_fail_validation(fixture_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_and_validate_aggregator(fixture_path)


def test_cli_validate_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "arforge.cli", "validate", str(VALID_PROJECT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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
def test_generate_diagrams_writes_expected_files(tmp_path: Path, diagram_format: str, expected_names: list[str]) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / diagram_format

    written = write_diagram_outputs(project, template_dir=template_dir, out=out_dir, fmt=diagram_format)

    assert [artifact.path.name for artifact in written] == expected_names


@pytest.mark.parametrize(
    ("diagram_format", "composition_name", "interface_name", "behavior_name"),
    [
        ("plantuml", "SpeedCluster_0", "If_VehicleSpeed", "Runnable_PublishVehicleSpeed"),
    ],
)
def test_generate_diagrams_contain_expected_smoke_fragments(
    tmp_path: Path,
    diagram_format: str,
    composition_name: str,
    interface_name: str,
    behavior_name: str,
) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / diagram_format

    _ = write_diagram_outputs(project, template_dir=template_dir, out=out_dir, fmt=diagram_format)
    extension = ".puml"

    composition_text = (out_dir / f"composition_DemoSystem{extension}").read_text(encoding="utf-8")
    subcomposition_text = (out_dir / f"subcomposition_SubComposition_SpeedCluster{extension}").read_text(encoding="utf-8")
    interfaces_wiring_text = (out_dir / f"interfaces_wiring{extension}").read_text(encoding="utf-8")
    interfaces_contracts_text = (out_dir / f"interfaces_contracts{extension}").read_text(encoding="utf-8")
    behavior_text = (out_dir / f"behavior_SpeedSensor{extension}").read_text(encoding="utf-8")

    assert composition_name in composition_text
    assert "DiagManager_0" in composition_text
    assert 'component "SpeedCluster_0"' in composition_text
    assert "Subcomposition" in composition_text
    assert "Rp_PowerStateIn" in composition_text
    assert "Pp_VehicleSpeedOut" in composition_text
    assert "Provided S/R" in composition_text
    assert "Subcomposition" in composition_text
    assert "Application SWC" in composition_text
    assert "DiagManager_0.Pp_PowerState" not in composition_text
    assert "Client/Server connector" in composition_text
    assert interface_name in interfaces_wiring_text
    assert "SpeedCluster_0" in interfaces_wiring_text
    assert "DiagManager_0" in interfaces_wiring_text
    assert "Rp_PowerStateIn" in interfaces_wiring_text
    assert "Pp_VehicleSpeedOut" in interfaces_wiring_text
    assert 'component "SubComposition_SpeedCluster"' in subcomposition_text
    assert "SpeedSensor_1" in subcomposition_text
    assert "SpeedDisplay_1" in subcomposition_text
    assert "Rp_PowerStateIn" in subcomposition_text
    assert "Pp_VehicleSpeedOut" in subcomposition_text
    assert "Pp_VehicleSpeed" in subcomposition_text
    assert "Rp_PowerStateIn" in subcomposition_text
    assert "..[#2e8b57,bold].>" in subcomposition_text
    assert "..[#8e44ad,bold,dashed].>" in subcomposition_text
    assert interface_name in interfaces_contracts_text
    assert "Mdg_PowerState" in interfaces_contracts_text
    assert "type__App_VehicleSpeed --> type__Impl_VehicleSpeed_U16 : impl" in interfaces_contracts_text
    assert behavior_name in behavior_text
    assert "Pp_VehicleSpeed" in behavior_text


@pytest.mark.parametrize(
    ("diagram_format", "expected_names"),
    [
        ("plantuml", PLANTUML_DIAGRAM_OUTPUTS),
    ],
)
def test_generate_diagrams_is_deterministic(tmp_path: Path, diagram_format: str, expected_names: list[str]) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out1 = tmp_path / f"{diagram_format}_1"
    out2 = tmp_path / f"{diagram_format}_2"

    _ = write_diagram_outputs(project, template_dir=template_dir, out=out1, fmt=diagram_format)
    _ = write_diagram_outputs(project, template_dir=template_dir, out=out2, fmt=diagram_format)

    assert sorted(path.name for path in out1.iterdir()) == sorted(expected_names)
    assert sorted(path.name for path in out2.iterdir()) == sorted(expected_names)

    for name in expected_names:
        data1 = (out1 / name).read_bytes()
        data2 = (out2 / name).read_bytes()
        assert data1 == data2
        assert hashlib.sha256(data1).hexdigest() == hashlib.sha256(data2).hexdigest()


def test_composition_diagram_uses_multi_column_layout_for_larger_systems() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    expanded_project = replace(
        project,
        system=replace(
            project.system,
            composition=replace(
                project.system.composition,
                components=sorted(
                    [
                        *project.system.composition.components,
                        replace(project.system.composition.components[0], name="SpeedDisplay_2", typeRef="SpeedDisplay"),
                        replace(project.system.composition.components[1], name="SpeedSensor_2", typeRef="SpeedSensor"),
                        replace(project.system.composition.components[0], name="SpeedDisplay_3", typeRef="SpeedDisplay"),
                    ],
                    key=lambda component: component.name,
                ),
            ),
        ),
    )

    view = build_diagram_views(expanded_project).composition

    assert view.grid_columns == 2
    assert [len(row.instances) for row in view.rows] == [2, 2, 1]


def test_subcomposition_diagram_view_contains_boundary_and_internal_instances() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    view = build_diagram_views(project).subcompositions[0]

    assert view.system_name == "SubComposition_SpeedCluster"
    assert view.boundary_name == "SubComposition_SpeedCluster"
    assert [port.name for port in view.boundary_incoming_ports] == ["Rp_PowerStateIn"]
    assert [port.name for port in view.boundary_outgoing_ports] == ["Pp_VehicleSpeedOut"]
    assert [instance.name for instance in view.instances] == ["SpeedDisplay_1", "SpeedSensor_1"]
    assert [(connector.source_id, connector.target_id) for connector in view.delegation_connectors] == [
        ("SubComposition_SpeedCluster__Rp_PowerStateIn", "SpeedSensor_1__Rp_PowerStateIn"),
        ("SpeedDisplay_1__Pp_VehicleSpeedOut", "SubComposition_SpeedCluster__Pp_VehicleSpeedOut"),
    ]


def test_behavior_diagram_places_server_trigger_ports_in_incoming_lane() -> None:
    project = Project(
        autosar_version="4.2",
        rootPackage="DEMO",
        baseTypes=[],
        implementationDataTypes=[],
        applicationDataTypes=[],
        units=[],
        compuMethods=[],
        modeDeclarationGroups=[],
        interfaces=[
            Interface(
                name="If_Diagnostics",
                type="clientServer",
                operations=[],
            )
        ],
        swcs=[
            Swc(
                name="DiagServer",
                ports=[
                    Port(
                        name="Pp_Diagnostics",
                        direction="provides",
                        interfaceRef="If_Diagnostics",
                        interfaceType="clientServer",
                    ),
                    Port(
                        name="Rp_DiagnosticsClient",
                        direction="requires",
                        interfaceRef="If_Diagnostics",
                        interfaceType="clientServer",
                    ),
                ],
                runnables=[
                    Runnable(
                        name="Runnable_HandleRequest",
                        operationInvokedEvents=[
                            OperationInvokedEvent(
                                port="Pp_Diagnostics",
                                operation="ReadDtc",
                            )
                        ],
                    )
                ],
            )
        ],
        subcompositions=[],
        system=System(
            name="DemoSystem",
            composition=Composition(
                name="Composition_DemoSystem",
                components=[ComponentPrototype(name="DiagServer_1", typeRef="DiagServer")],
                connectors=[],
            ),
        ),
    )

    view = build_diagram_views(project).behaviors[0]

    assert [port.name for port in view.incoming_ports] == ["Pp_Diagnostics", "Rp_DiagnosticsClient"]
    assert [port.name for port in view.outgoing_ports] == []


def test_behavior_diagram_uses_runnable_grid_for_larger_behaviors() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    speed_display = next(swc for swc in project.swcs if swc.name == "SpeedDisplay")
    expanded_runnables = sorted(
        [
            *speed_display.runnables,
            Runnable(name="Runnable_Extra1"),
            Runnable(name="Runnable_Extra2"),
            Runnable(name="Runnable_Extra3"),
        ],
        key=lambda runnable: runnable.name,
    )
    expanded_project = replace(
        project,
        swcs=[
            replace(swc, runnables=expanded_runnables) if swc.name == "SpeedDisplay" else swc
            for swc in project.swcs
        ],
    )

    view = next(behavior for behavior in build_diagram_views(expanded_project).behaviors if behavior.swc_name == "SpeedDisplay")

    assert view.runnable_columns == 2
    assert [len(row.runnables) for row in view.runnable_rows] == [2, 2, 2, 1]


def test_behavior_diagram_keeps_small_runnable_sets_in_one_row() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    view = next(
        behavior for behavior in build_diagram_views(project).behaviors if behavior.swc_name == "SpeedDisplay"
    )

    assert len(view.runnables) == 4
    assert view.runnable_columns == 4
    assert [len(row.runnables) for row in view.runnable_rows] == [4]


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


def test_cs_server_unconnected_binding_passes_validation_and_reports_warning() -> None:
    project = load_and_validate_aggregator(CS_SERVER_WARNING_PROJECT)
    report = build_semantic_report(project, ruleset="core")

    assert report.error_findings() == []
    oie_findings = [finding for finding in report.findings if finding.code == "CORE-043-CS-OIE-UNCONNECTED"]
    assert oie_findings
    assert all(finding.severity == FindingSeverity.WARNING for finding in oie_findings)


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
        "Connected modeSwitch requires port 'SpeedDisplay_1.Rp_PowerState' is not used by any runnable modeSwitchEvents."
    )


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


def test_split_export_reports_aligned_example_outputs(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    written = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    assert [path.name for path in written] == [
        SHARED_EXAMPLE_OUTPUT,
        "DiagManager.arxml",
        "SpeedDisplay.arxml",
        "SpeedSensor.arxml",
        SUBCOMPOSITION_EXAMPLE_OUTPUT,
        SYSTEM_EXAMPLE_OUTPUT,
    ]


def test_split_export_flat_project_regression_keeps_legacy_artifact_set(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    flat_project = replace(
        project,
        subcompositions=[],
        system=replace(
            project.system,
            composition=Composition(
                name=project.system.composition.name,
                description=project.system.composition.description,
                components=[component for component in project.system.composition.components if component.typeRef != "SubComposition_SpeedCluster"],
                connectors=[],
            ),
        ),
    )

    written = write_outputs(flat_project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    assert [path.name for path in written] == [
        SHARED_EXAMPLE_OUTPUT,
        "DiagManager.arxml",
        "SpeedDisplay.arxml",
        "SpeedSensor.arxml",
        SYSTEM_EXAMPLE_OUTPUT,
    ]


def test_generate_code_writes_expected_files_for_example_project(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "code"

    written = write_code_outputs(project, template_dir=template_dir, out=out_dir, lang="c")

    assert [path.name for path in written] == [
        "DiagManager.h",
        "DiagManager.c",
        "SpeedDisplay.h",
        "SpeedDisplay.c",
        "SpeedSensor.h",
        "SpeedSensor.c",
    ]


def test_generate_code_contains_expected_runnable_names_and_rte_placeholders(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "code"

    _ = write_code_outputs(project, template_dir=template_dir, out=out_dir, lang="c")

    speed_display_header = (out_dir / "SpeedDisplay.h").read_text(encoding="utf-8")
    speed_display_source = (out_dir / "SpeedDisplay.c").read_text(encoding="utf-8")
    speed_sensor_source = (out_dir / "SpeedSensor.c").read_text(encoding="utf-8")

    assert "#ifndef ARFORGE_SPEEDDISPLAY_H" in speed_display_header
    assert "void Runnable_OnPowerOn(void);" in speed_display_header
    assert "void Runnable_ReadVehicleSpeed(void);" in speed_display_header
    assert "void Runnable_ReadVehicleSpeedImplicit(void);" in speed_display_header
    assert "void Runnable_ReadVehicleSpeedQueued(void);" in speed_display_header
    assert "Trigger: ModeSwitchEvent(Rp_PowerState -> ON)" in speed_display_header
    assert "Trigger: TimingEvent(10 ms)" in speed_display_header

    assert "Rte_Read_Rp_VehicleSpeed_VehicleSpeed" in speed_display_source
    assert "Rte_Read_Rp_VehicleSpeedImplicit_VehicleSpeed" in speed_display_source
    assert "Rte_Read_Rp_VehicleSpeedQueued_VehicleSpeed" in speed_display_source
    assert "Rte_Write_Pp_VehicleSpeedOut_VehicleSpeed" in speed_display_source
    assert "uint16 rp_vehicle_speed_vehicle_speed = 0;" in speed_display_source
    assert "uint16 rp_vehicle_speed_implicit_vehicle_speed = 0;" in speed_display_source
    assert "uint16 rp_vehicle_speed_queued_vehicle_speed = 0;" in speed_display_source
    assert "Trigger: ModeSwitchEvent(Rp_PowerState -> ON)" in speed_display_source
    assert "TODO: handle modeled mode-switch trigger(s) for this runnable." in speed_display_source
    assert "React to the ECU entering the ON power mode." in speed_display_source

    assert "Rte_Write_Pp_VehicleSpeed_VehicleSpeed" in speed_sensor_source
    assert "Trigger: ModeSwitchEvent(Rp_PowerStateIn -> ON)" in speed_sensor_source
    assert "Trigger: TimingEvent(10 ms)" in speed_sensor_source


def test_generate_code_is_deterministic(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out1 = tmp_path / "code1"
    out2 = tmp_path / "code2"

    _ = write_code_outputs(project, template_dir=template_dir, out=out1, lang="c")
    _ = write_code_outputs(project, template_dir=template_dir, out=out2, lang="c")

    files1 = sorted(p.relative_to(out1) for p in out1.rglob("*.*"))
    files2 = sorted(p.relative_to(out2) for p in out2.rglob("*.*"))
    assert files1 == files2

    for rel in files1:
        data1 = (out1 / rel).read_bytes()
        data2 = (out2 / rel).read_bytes()
        assert data1 == data2
        assert hashlib.sha256(data1).hexdigest() == hashlib.sha256(data2).hexdigest()


def test_split_export_subcomposition_file_contains_reusable_composition_type(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    composition_xml = (out_dir / SUBCOMPOSITION_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    assert "<SHORT-NAME>SubComposition_SpeedCluster</SHORT-NAME>" in composition_xml
    assert "<PORTS>" in composition_xml
    assert "<SHORT-NAME>Rp_PowerStateIn</SHORT-NAME>" in composition_xml
    assert "<SHORT-NAME>Pp_VehicleSpeedOut</SHORT-NAME>" in composition_xml
    assert "<REQUIRED-INTERFACE-TREF DEST=\"MODE-SWITCH-INTERFACE\">/DEMO/Interfaces/If_PowerState</REQUIRED-INTERFACE-TREF>" in composition_xml
    assert "<PROVIDED-INTERFACE-TREF DEST=\"SENDER-RECEIVER-INTERFACE\">/DEMO/Interfaces/If_VehicleSpeed</PROVIDED-INTERFACE-TREF>" in composition_xml
    assert "<SHORT-NAME>SpeedSensor_1</SHORT-NAME>" in composition_xml
    assert "<SHORT-NAME>SpeedDisplay_1</SHORT-NAME>" in composition_xml
    assert composition_xml.count("<COMPOSITION-SW-COMPONENT-TYPE>") == 1
    assert composition_xml.count("<SW-COMPONENT-PROTOTYPE>") == 2
    assert composition_xml.count("<ASSEMBLY-SW-CONNECTOR>") == 4
    assert composition_xml.count("<DELEGATION-SW-CONNECTOR>") == 2
    assert "<TYPE-TREF DEST=\"APPLICATION-SW-COMPONENT-TYPE\">/DEMO/Components/SpeedSensor</TYPE-TREF>" in composition_xml
    assert "<TYPE-TREF DEST=\"APPLICATION-SW-COMPONENT-TYPE\">/DEMO/Components/SpeedDisplay</TYPE-TREF>" in composition_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/SpeedSensor_1</CONTEXT-COMPONENT-REF>" in composition_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/SpeedDisplay_1</CONTEXT-COMPONENT-REF>" in composition_xml
    assert "<P-PORT-IN-COMPOSITION-INSTANCE-REF>" in composition_xml
    assert "<R-PORT-IN-COMPOSITION-INSTANCE-REF>" in composition_xml
    assert "/DEMO/Components/SpeedSensor/Pp_VehicleSpeed</TARGET-P-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedDisplay/Rp_VehicleSpeed</TARGET-R-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedDisplay/Rp_VehicleSpeedImplicit</TARGET-R-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedDisplay/Rp_VehicleSpeedQueued</TARGET-R-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedSensor/Pp_PowerState</TARGET-P-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedDisplay/Rp_PowerState</TARGET-R-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/SpeedSensor_1/Pp_VehicleSpeed</TARGET-P-PORT-REF>" not in composition_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/SpeedDisplay_1/Rp_VehicleSpeed</TARGET-R-PORT-REF>" not in composition_xml
    assert "<SHORT-NAME>DelegationConn_1</SHORT-NAME>" in composition_xml
    assert "<SHORT-NAME>DelegationConn_2</SHORT-NAME>" in composition_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/Rp_PowerStateIn</OUTER-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/Pp_VehicleSpeedOut</OUTER-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedDisplay/Pp_VehicleSpeedOut</TARGET-P-PORT-REF>" in composition_xml
    assert "/DEMO/Components/SpeedSensor/Rp_PowerStateIn</TARGET-R-PORT-REF>" in composition_xml


def test_split_export_system_contains_root_composition_without_inlining_subcomposition_type(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    system_xml = (out_dir / SYSTEM_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    assert "<SHORT-NAME>Composition_DemoSystem</SHORT-NAME>" in system_xml
    assert "/DEMO/System/Composition_DemoSystem/DiagManager_0</CONTEXT-COMPONENT-REF>" in system_xml
    assert "/DEMO/System/Composition_DemoSystem/SpeedCluster_0</CONTEXT-COMPONENT-REF>" in system_xml
    assert "/DEMO/Components/DiagManager/Pp_PowerState</TARGET-P-PORT-REF>" in system_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/Rp_PowerStateIn</TARGET-R-PORT-REF>" in system_xml
    assert "/DEMO/Components/SubComposition_SpeedCluster/Pp_VehicleSpeedOut</TARGET-P-PORT-REF>" in system_xml
    assert "/DEMO/Components/DiagManager/Rp_VehicleSpeed</TARGET-R-PORT-REF>" in system_xml
    assert "/DEMO/System/Composition_DemoSystem/SpeedCluster_0/Rp_PowerStateIn</TARGET-R-PORT-REF>" not in system_xml
    assert "/DEMO/System/Composition_DemoSystem/SpeedCluster_0/Pp_VehicleSpeedOut</TARGET-P-PORT-REF>" not in system_xml
    assert "/DEMO/Components/SpeedSensor/Pp_VehicleSpeed</TARGET-P-PORT-REF>" not in system_xml
    assert "/DEMO/Components/SpeedDisplay/Pp_VehicleSpeedOut</TARGET-P-PORT-REF>" not in system_xml
    assert "<SHORT-NAME>SpeedCluster_0</SHORT-NAME>" in system_xml
    assert "<SHORT-NAME>DiagManager_0</SHORT-NAME>" in system_xml
    assert system_xml.count("<COMPOSITION-SW-COMPONENT-TYPE>") == 1
    assert system_xml.count("<SW-COMPONENT-PROTOTYPE>") == 2
    assert system_xml.count("<ASSEMBLY-SW-CONNECTOR>") == 2
    assert "<TYPE-TREF DEST=\"COMPOSITION-SW-COMPONENT-TYPE\">/DEMO/Components/SubComposition_SpeedCluster</TYPE-TREF>" in system_xml
    assert "<TYPE-TREF DEST=\"APPLICATION-SW-COMPONENT-TYPE\">/DEMO/Components/DiagManager</TYPE-TREF>" in system_xml
    assert "<SHORT-NAME>SubComposition_SpeedCluster</SHORT-NAME>" not in system_xml
    assert "<DELEGATION-SW-CONNECTOR>" not in system_xml


def test_split_export_shared_types_match_simple_example_model(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    shared_xml = (out_dir / SHARED_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    assert "<SHORT-NAME>If_VehicleSpeed</SHORT-NAME>" in shared_xml
    assert "<SHORT-NAME>If_PowerState</SHORT-NAME>" in shared_xml
    assert "<SHORT-NAME>VehicleSpeed</SHORT-NAME>" in shared_xml
    assert "<TYPE-TREF DEST=\"APPLICATION-PRIMITIVE-DATA-TYPE\">/DEMO/ApplicationDataTypes/App_VehicleSpeed</TYPE-TREF>" in shared_xml
    assert "<SHORT-NAME>App_VehicleSpeed</SHORT-NAME>" in shared_xml
    assert "<SHORT-NAME>Impl_VehicleSpeed_U16</SHORT-NAME>" in shared_xml
    assert "<SHORT-NAME>CM_VehicleSpeed_Kph</SHORT-NAME>" in shared_xml
    assert "<SHORT-NAME>km_per_h</SHORT-NAME>" in shared_xml
    assert "<SHORT-NAME>Mdg_PowerState</SHORT-NAME>" in shared_xml
    assert "<INITIAL-MODE-REF DEST=\"MODE-DECLARATION\">/DEMO/Modes/Mdg_PowerState/OFF</INITIAL-MODE-REF>" in shared_xml
    assert "<SHORT-NAME>SLEEP</SHORT-NAME>" in shared_xml
    assert "<MODE-SWITCH-INTERFACE>" in shared_xml
    assert "<TYPE-TREF DEST=\"MODE-DECLARATION-GROUP\">/DEMO/Modes/Mdg_PowerState</TYPE-TREF>" in shared_xml
    assert "<IS-SERVICE>false</IS-SERVICE>" in shared_xml
    assert "<SW-DATA-DEF-PROPS>" in shared_xml
    assert "<COMPU-INTERNAL-TO-PHYS>" in shared_xml
    assert "<FACTOR>" not in shared_xml


def test_split_export_swc_files_contain_aligned_runnables_and_ports(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_sensor_xml = (out_dir / "SpeedSensor.arxml").read_text(encoding="utf-8")
    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")

    assert "<SHORT-NAME>Runnable_PublishVehicleSpeed</SHORT-NAME>" in speed_sensor_xml
    assert "<SHORT-NAME>Runnable_OnPowerOn</SHORT-NAME>" in speed_sensor_xml
    assert "<SHORT-NAME>Pp_VehicleSpeed</SHORT-NAME>" in speed_sensor_xml
    assert "<SHORT-NAME>Rp_PowerStateIn</SHORT-NAME>" in speed_sensor_xml
    assert "<SHORT-NAME>Pp_PowerState</SHORT-NAME>" in speed_sensor_xml
    assert "<PROVIDED-INTERFACE-TREF DEST=\"MODE-SWITCH-INTERFACE\">/DEMO/Interfaces/If_PowerState</PROVIDED-INTERFACE-TREF>" in speed_sensor_xml
    assert "<SHORT-NAME>Runnable_ReadVehicleSpeed</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Runnable_ReadVehicleSpeedImplicit</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Runnable_ReadVehicleSpeedQueued</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Runnable_OnPowerOn</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Rp_VehicleSpeed</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Rp_VehicleSpeedImplicit</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Rp_VehicleSpeedQueued</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Rp_PowerState</SHORT-NAME>" in speed_display_xml
    assert "<SHORT-NAME>Pp_VehicleSpeedOut</SHORT-NAME>" in speed_display_xml
    assert "<REQUIRED-INTERFACE-TREF DEST=\"MODE-SWITCH-INTERFACE\">/DEMO/Interfaces/If_PowerState</REQUIRED-INTERFACE-TREF>" in speed_display_xml
    assert "<MODE-SWITCH-EVENT>" in speed_display_xml
    assert "<SHORT-NAME>MSE_Runnable_OnPowerOn_Rp_PowerState_ON</SHORT-NAME>" in speed_display_xml
    assert "<TARGET-MODE-DECLARATION-REF DEST=\"MODE-DECLARATION\">/DEMO/Modes/Mdg_PowerState/ON</TARGET-MODE-DECLARATION-REF>" in speed_display_xml


def test_split_export_preserves_explicit_sr_receiver_semantics(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    explicit_fragment = _extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeed")

    assert "<NONQUEUED-RECEIVER-COM-SPEC>" in explicit_fragment
    assert "<ENABLE-UPDATE>true</ENABLE-UPDATE>" in explicit_fragment


def test_split_export_preserves_implicit_sr_receiver_semantics(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    implicit_fragment = _extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeedImplicit")

    assert "<NONQUEUED-RECEIVER-COM-SPEC>" in implicit_fragment
    assert "<ENABLE-UPDATE>false</ENABLE-UPDATE>" in implicit_fragment


def test_split_export_preserves_queued_sr_receiver_semantics(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    queued_fragment = _extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeedQueued")

    assert "<QUEUED-RECEIVER-COM-SPEC>" in queued_fragment
    assert "<QUEUE-LENGTH>4</QUEUE-LENGTH>" in queued_fragment


def test_split_export_explicit_and_implicit_receiver_fragments_differ(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    explicit_fragment = _extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeed")
    implicit_fragment = _extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeedImplicit")

    assert explicit_fragment != implicit_fragment


def test_main_example_omitted_swc_category_defaults_to_application() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    assert next(swc for swc in project.swcs if swc.name == "SpeedSensor").category == "application"
    assert next(swc for swc in project.swcs if swc.name == "SpeedDisplay").category == "application"


def test_split_export_uses_swc_category_for_component_types_and_prototype_dests(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    categorized_project = replace(
        project,
        swcs=[
            replace(swc, category="service") if swc.name == "SpeedSensor" else replace(swc, category="complexDeviceDriver")
            for swc in project.swcs
        ],
    )

    _ = write_outputs(categorized_project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_sensor_xml = (out_dir / "SpeedSensor.arxml").read_text(encoding="utf-8")
    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    subcomposition_xml = (out_dir / SUBCOMPOSITION_EXAMPLE_OUTPUT).read_text(encoding="utf-8")
    system_xml = (out_dir / SYSTEM_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    assert "<SERVICE-SW-COMPONENT-TYPE>" in speed_sensor_xml
    assert "<APPLICATION-SW-COMPONENT-TYPE>" not in speed_sensor_xml
    assert "<COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE>" in speed_display_xml
    assert "<TYPE-TREF DEST=\"SERVICE-SW-COMPONENT-TYPE\">/DEMO/Components/SpeedSensor</TYPE-TREF>" in subcomposition_xml
    assert "<TYPE-TREF DEST=\"COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE\">/DEMO/Components/SpeedDisplay</TYPE-TREF>" in subcomposition_xml
    assert "<TYPE-TREF DEST=\"COMPOSITION-SW-COMPONENT-TYPE\">/DEMO/Components/SubComposition_SpeedCluster</TYPE-TREF>" in system_xml


def test_split_export_orders_outputs_deterministically(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    report = write_outputs_with_report(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    component_type_outputs = [
        artifact.path.name
        for artifact in report.outputs
        if artifact.path.name.endswith(".arxml") and artifact.path.name not in {SHARED_EXAMPLE_OUTPUT, SYSTEM_EXAMPLE_OUTPUT}
    ]
    assert component_type_outputs == [
        "DiagManager.arxml",
        "SpeedDisplay.arxml",
        "SpeedSensor.arxml",
        SUBCOMPOSITION_EXAMPLE_OUTPUT,
    ]


def test_monolithic_and_split_shared_type_fragments_are_equivalent(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    monolithic_out = tmp_path / "DemoProject.arxml"
    split_out = tmp_path / "split"

    _ = write_outputs(project, template_dir=template_dir, out=monolithic_out, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=split_out, split_by_swc=True)

    monolithic_xml = monolithic_out.read_text(encoding="utf-8")
    shared_xml = (split_out / SHARED_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    mono_app_type = _extract_element_fragment(monolithic_xml, "APPLICATION-PRIMITIVE-DATA-TYPE", "App_VehicleSpeed")
    split_app_type = _extract_element_fragment(shared_xml, "APPLICATION-PRIMITIVE-DATA-TYPE", "App_VehicleSpeed")
    assert "<SW-DATA-DEF-PROPS>" in mono_app_type
    assert "<SW-DATA-DEF-PROPS>" in split_app_type
    assert "<DATA-CONSTR-REF DEST=\"DATA-CONSTR\">/DEMO/DataConstrs/DC_App_VehicleSpeed</DATA-CONSTR-REF>" in mono_app_type
    assert "<DATA-CONSTR-REF DEST=\"DATA-CONSTR\">/DEMO/DataConstrs/DC_App_VehicleSpeed</DATA-CONSTR-REF>" in split_app_type
    assert _normalize_xml_fragment(mono_app_type) == _normalize_xml_fragment(split_app_type)

    mono_compu = _extract_element_fragment(monolithic_xml, "COMPU-METHOD", "CM_VehicleSpeed_Kph")
    split_compu = _extract_element_fragment(shared_xml, "COMPU-METHOD", "CM_VehicleSpeed_Kph")
    assert "<COMPU-INTERNAL-TO-PHYS>" in mono_compu
    assert "<COMPU-INTERNAL-TO-PHYS>" in split_compu
    assert "<FACTOR>" not in mono_compu
    assert "<FACTOR>" not in split_compu
    assert _normalize_xml_fragment(mono_compu) == _normalize_xml_fragment(split_compu)


def test_monolithic_and_split_swc_fragments_are_equivalent(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    monolithic_out = tmp_path / "DemoProject.arxml"
    split_out = tmp_path / "split"

    _ = write_outputs(project, template_dir=template_dir, out=monolithic_out, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=split_out, split_by_swc=True)

    monolithic_xml = monolithic_out.read_text(encoding="utf-8")
    split_xml = (split_out / "SpeedDisplay.arxml").read_text(encoding="utf-8")

    mono_behavior = _extract_internal_behavior_fragment(monolithic_xml, "SpeedDisplay")
    split_behavior = _extract_internal_behavior_fragment(split_xml, "SpeedDisplay")
    assert mono_behavior.index("<EVENTS>") < mono_behavior.index("<RUNNABLES>")
    assert split_behavior.index("<EVENTS>") < split_behavior.index("<RUNNABLES>")
    assert _normalize_xml_fragment(mono_behavior) == _normalize_xml_fragment(split_behavior)

    mono_component = _extract_element_fragment(
        monolithic_xml,
        "APPLICATION-SW-COMPONENT-TYPE|SERVICE-SW-COMPONENT-TYPE|COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "SpeedDisplay",
    )
    split_component = _extract_element_fragment(
        split_xml,
        "APPLICATION-SW-COMPONENT-TYPE|SERVICE-SW-COMPONENT-TYPE|COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "SpeedDisplay",
    )
    mono_r_port = _extract_r_port_fragment(mono_component, "Rp_VehicleSpeed")
    split_r_port = _extract_r_port_fragment(split_component, "Rp_VehicleSpeed")
    assert mono_r_port.index("<REQUIRED-COM-SPECS>") < mono_r_port.index("<REQUIRED-INTERFACE-TREF")
    assert split_r_port.index("<REQUIRED-COM-SPECS>") < split_r_port.index("<REQUIRED-INTERFACE-TREF")
    assert _normalize_xml_fragment(mono_r_port) == _normalize_xml_fragment(split_r_port)


def test_monolithic_and_split_subcomposition_fragments_are_equivalent(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    monolithic_out = tmp_path / "DemoProject.arxml"
    split_out = tmp_path / "split"

    _ = write_outputs(project, template_dir=template_dir, out=monolithic_out, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=split_out, split_by_swc=True)

    monolithic_xml = monolithic_out.read_text(encoding="utf-8")
    split_xml = (split_out / SUBCOMPOSITION_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    mono_subcomposition = _extract_element_fragment(monolithic_xml, "COMPOSITION-SW-COMPONENT-TYPE", "SubComposition_SpeedCluster")
    split_subcomposition = _extract_element_fragment(split_xml, "COMPOSITION-SW-COMPONENT-TYPE", "SubComposition_SpeedCluster")
    assert "<P-PORT-IN-COMPOSITION-INSTANCE-REF>" in mono_subcomposition
    assert "<P-PORT-IN-COMPOSITION-INSTANCE-REF>" in split_subcomposition
    assert "<R-PORT-IN-COMPOSITION-INSTANCE-REF>" in mono_subcomposition
    assert "<R-PORT-IN-COMPOSITION-INSTANCE-REF>" in split_subcomposition
    assert re.search(r"<INNER-PORT-IREF>\s*<CONTEXT-COMPONENT-REF", mono_subcomposition) is None
    assert re.search(r"<INNER-PORT-IREF>\s*<CONTEXT-COMPONENT-REF", split_subcomposition) is None
    assert _normalize_xml_fragment(mono_subcomposition) == _normalize_xml_fragment(split_subcomposition)


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
        ("project_impl_array_zero_length.yaml", "CORE-010-ARRAY-LENGTH"),
        ("project_struct_cycle.yaml", "CORE-010-STRUCT-CYCLE"),
        ("project_struct_duplicate_field_names.yaml", "CORE-010-STRUCT-DUPLICATE-FIELD"),
        ("project_struct_unknown_nested_type.yaml", "CORE-010-STRUCT-UNKNOWN-TYPE"),
        ("project_sr_duplicate_port_pair.yaml", "CORE-040-SR-DUPLICATE-PORT-PAIR"),
        ("project_mode_group_duplicate_modes.yaml", "CORE-012-MDG-DUPLICATE-MODE"),
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


def test_split_export_is_deterministic(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    _ = write_outputs(project, template_dir=template_dir, out=out1, split_by_swc=True)
    _ = write_outputs(project, template_dir=template_dir, out=out2, split_by_swc=True)

    files1 = sorted(p.relative_to(out1) for p in out1.rglob("*.arxml"))
    files2 = sorted(p.relative_to(out2) for p in out2.rglob("*.arxml"))
    assert files1 == files2

    for rel in files1:
        data1 = (out1 / rel).read_bytes()
        data2 = (out2 / rel).read_bytes()
        assert data1 == data2
        assert hashlib.sha256(data1).hexdigest() == hashlib.sha256(data2).hexdigest()
