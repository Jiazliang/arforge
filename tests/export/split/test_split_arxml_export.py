"""Tests for split ARXML export behavior.

This file verifies split artifact naming, shared and per-component content,
mode declaration emission, receiver semantics, and deterministic ordering.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

from arforge.exporter import write_outputs, write_outputs_with_report
from arforge.model import Composition
from arforge.validate import load_and_validate_aggregator
from tests._shared import (
    MODES_FEATURE_PROJECT,
    REPO_ROOT,
    SHARED_EXAMPLE_OUTPUT,
    SUBCOMPOSITION_EXAMPLE_OUTPUT,
    SYSTEM_EXAMPLE_OUTPUT,
    TEMPLATE_DIR,
    VALID_PROJECT,
    extract_mode_declaration_group_fragment,
    extract_r_port_fragment,
    parse_xml_fragment,
)

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
    assert "<CATEGORY>FIXED_LENGTH</CATEGORY>" in shared_xml
    assert "<SHORT-NAME>Mdg_PowerState</SHORT-NAME>" in shared_xml
    assert "<CATEGORY>EXPLICIT_ORDER</CATEGORY>" in shared_xml
    assert "<ON-TRANSITION-VALUE>255</ON-TRANSITION-VALUE>" in shared_xml
    assert "<INITIAL-MODE-REF DEST=\"MODE-DECLARATION\">/DEMO/Modes/Mdg_PowerState/OFF</INITIAL-MODE-REF>" in shared_xml
    assert "<VALUE>0</VALUE>" in shared_xml
    assert "<VALUE>1</VALUE>" in shared_xml
    assert "<VALUE>2</VALUE>" in shared_xml
    assert "<SHORT-NAME>SLEEP</SHORT-NAME>" in shared_xml
    assert "<MODE-SWITCH-INTERFACE>" in shared_xml
    assert "<TYPE-TREF DEST=\"MODE-DECLARATION-GROUP\">/DEMO/Modes/Mdg_PowerState</TYPE-TREF>" in shared_xml
    assert "<IS-SERVICE>false</IS-SERVICE>" in shared_xml
    assert "<SW-DATA-DEF-PROPS>" in shared_xml
    assert "<COMPU-INTERNAL-TO-PHYS>" in shared_xml
    assert "<FACTOR>" not in shared_xml
    assert "<CATEGORY>VALUE</CATEGORY>" in shared_xml
    assert "<COMPU-METHOD-REF DEST=\"COMPU-METHOD\">/DEMO/CompuMethods/CM_VehicleSpeed_Kph</COMPU-METHOD-REF>" in shared_xml

def test_split_export_mode_declaration_group_fragment_is_schema_aligned(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"

    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    shared_xml = (out_dir / SHARED_EXAMPLE_OUTPUT).read_text(encoding="utf-8")
    fragment = extract_mode_declaration_group_fragment(shared_xml, "Mdg_PowerState")
    element = parse_xml_fragment(fragment)

    assert [child.tag for child in element] == [
        "SHORT-NAME",
        "CATEGORY",
        "INITIAL-MODE-REF",
        "MODE-DECLARATIONS",
        "ON-TRANSITION-VALUE",
    ]
    assert element.findtext("CATEGORY") == "EXPLICIT_ORDER"
    assert element.findtext("ON-TRANSITION-VALUE") == "255"
    assert element.findtext("INITIAL-MODE-REF") == "/DEMO/Modes/Mdg_PowerState/OFF"

    mode_declarations = element.find("MODE-DECLARATIONS")
    assert mode_declarations is not None
    declared_modes = [mode.findtext("SHORT-NAME") for mode in mode_declarations.findall("MODE-DECLARATION")]
    declared_values = [mode.findtext("VALUE") for mode in mode_declarations.findall("MODE-DECLARATION")]
    assert declared_modes == ["OFF", "ON", "SLEEP"]
    assert declared_values == ["0", "1", "2"]

def test_mode_group_initial_mode_reference_points_to_emitted_mode_declaration(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"

    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    shared_xml = (out_dir / SHARED_EXAMPLE_OUTPUT).read_text(encoding="utf-8")
    fragment = extract_mode_declaration_group_fragment(shared_xml, "Mdg_PowerState")
    element = parse_xml_fragment(fragment)

    initial_mode_ref = element.findtext("INITIAL-MODE-REF")
    assert initial_mode_ref is not None

    mode_declarations = element.find("MODE-DECLARATIONS")
    assert mode_declarations is not None
    emitted_mode_paths = {
        f"/DEMO/Modes/Mdg_PowerState/{mode.findtext('SHORT-NAME')}"
        for mode in mode_declarations.findall("MODE-DECLARATION")
    }
    assert initial_mode_ref in emitted_mode_paths
    assert "/DEMO/Modes/Mdg_PowerState/ON" in emitted_mode_paths

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
    assert "<SWC-MODE-SWITCH-EVENT>" in speed_display_xml
    assert "<SHORT-NAME>MSE_Runnable_OnPowerOn_Rp_PowerState_ON</SHORT-NAME>" in speed_display_xml
    assert "<TARGET-MODE-DECLARATION-REF DEST=\"MODE-DECLARATION\">/DEMO/Modes/Mdg_PowerState/ON</TARGET-MODE-DECLARATION-REF>" in speed_display_xml
    assert "<DATA-ELEMENT-REF DEST=\"VARIABLE-DATA-PROTOTYPE\">/DEMO/Interfaces/If_VehicleSpeed/VehicleSpeed</DATA-ELEMENT-REF>" in speed_display_xml
    assert "<INIT-VALUE>" in speed_display_xml

def test_split_modes_example_keeps_mode_conditions_out_of_arxml(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    out_dir = tmp_path / "out"
    written = write_outputs(project, template_dir=REPO_ROOT / "templates", out=out_dir, split_by_swc=True)

    power_state_user_path = next(path for path in written if path.name == "PowerStateUser.arxml")
    power_state_user_xml = power_state_user_path.read_text(encoding="utf-8")

    assert "<SWC-MODE-SWITCH-EVENT>" in power_state_user_xml
    assert "Runnable_ProcessWhenActive" in power_state_user_xml
    assert "<DISABLED-MODE-IREFS>" in power_state_user_xml
    assert "<SHORT-NAME>TE_Runnable_ProcessWhenActive</SHORT-NAME>" in power_state_user_xml
    assert "/FEATURE_MODES/Modes/Mdg_PowerState/OFF</TARGET-MODE-DECLARATION-REF>" in power_state_user_xml
    assert "/FEATURE_MODES/Modes/Mdg_PowerState/ON</TARGET-MODE-DECLARATION-REF>" not in (
        power_state_user_xml.split("<SHORT-NAME>TE_Runnable_ProcessWhenActive</SHORT-NAME>", 1)[1]
        .split("</TIMING-EVENT>", 1)[0]
    )

def test_split_export_preserves_explicit_sr_receiver_semantics(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    explicit_fragment = extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeed")

    assert "<NONQUEUED-RECEIVER-COM-SPEC>" in explicit_fragment
    assert "<ENABLE-UPDATE>true</ENABLE-UPDATE>" in explicit_fragment
    assert "<DATA-ELEMENT-REF DEST=\"VARIABLE-DATA-PROTOTYPE\">/DEMO/Interfaces/If_VehicleSpeed/VehicleSpeed</DATA-ELEMENT-REF>" in explicit_fragment
    assert "<INIT-VALUE>" in explicit_fragment
    assert "<V>0</V>" in explicit_fragment

def test_split_export_preserves_implicit_sr_receiver_semantics(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    implicit_fragment = extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeedImplicit")

    assert "<NONQUEUED-RECEIVER-COM-SPEC>" in implicit_fragment
    assert "<ENABLE-UPDATE>false</ENABLE-UPDATE>" in implicit_fragment
    assert "<DATA-ELEMENT-REF DEST=\"VARIABLE-DATA-PROTOTYPE\">/DEMO/Interfaces/If_VehicleSpeed/VehicleSpeed</DATA-ELEMENT-REF>" in implicit_fragment
    assert "<INIT-VALUE>" in implicit_fragment

def test_split_export_preserves_queued_sr_receiver_semantics(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    queued_fragment = extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeedQueued")

    assert "<QUEUED-RECEIVER-COM-SPEC>" in queued_fragment
    assert "<QUEUE-LENGTH>4</QUEUE-LENGTH>" in queued_fragment
    assert "<DATA-ELEMENT-REF DEST=\"VARIABLE-DATA-PROTOTYPE\">/DEMO/Interfaces/If_VehicleSpeed/VehicleSpeed</DATA-ELEMENT-REF>" in queued_fragment
    assert "<INIT-VALUE>" not in queued_fragment

def test_split_export_explicit_and_implicit_receiver_fragments_differ(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out_dir = tmp_path / "out"
    _ = write_outputs(project, template_dir=template_dir, out=out_dir, split_by_swc=True)

    speed_display_xml = (out_dir / "SpeedDisplay.arxml").read_text(encoding="utf-8")
    explicit_fragment = extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeed")
    implicit_fragment = extract_r_port_fragment(speed_display_xml, "Rp_VehicleSpeedImplicit")

    assert explicit_fragment != implicit_fragment

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
