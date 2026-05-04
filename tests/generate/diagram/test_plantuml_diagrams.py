"""Tests for diagram view models and PlantUML generation.

This file covers both the internal diagram views and the rendered PlantUML
artifacts so layout and emitted content stay stable over time.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from arforge.arxml_paths import default_package_layout
from arforge.diagrams import build_diagram_views, write_diagram_outputs
from arforge.model import (
    ComponentPrototype,
    Composition,
    Interface,
    OperationInvokedEvent,
    PackageLayout,
    Port,
    Project,
    Runnable,
    Swc,
    System,
)
from arforge.validate import load_and_validate_aggregator
from tests._shared import MODES_FEATURE_PROJECT, PLANTUML_DIAGRAM_OUTPUTS, REPO_ROOT, TEMPLATE_DIR, VALID_PROJECT

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
    assert '#f1e3d3 {' in subcomposition_text
    assert "#f8f9fa" not in subcomposition_text
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
        packageLayout=PackageLayout(**default_package_layout()),
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

def test_behavior_diagram_includes_mode_condition_metadata() -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)

    view = next(behavior for behavior in build_diagram_views(project).behaviors if behavior.swc_name == "PowerStateUser")
    process_when_active = next(runnable for runnable in view.runnables if runnable.name == "Runnable_ProcessWhenActive")
    on_power_on = next(runnable for runnable in view.runnables if runnable.name == "Runnable_OnPowerOn")

    assert "(cyclic, 10 ms)" in process_when_active.metadata_lines
    assert "(allowed, Rp_PowerState: ON | SLEEP)" in process_when_active.metadata_lines
    assert "(mode, Rp_PowerState: ON)" in on_power_on.metadata_lines
    assert "(allowed, Rp_PowerState: ON)" in on_power_on.metadata_lines
