"""Tests for `arforge init` scaffold generation.

These checks make sure the scaffold creates the expected starter layout,
produces a valid project, and handles empty/non-empty target directories.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from arforge.exporter import write_outputs
from arforge.validate import load_and_validate_aggregator
from tests._shared import REPO_ROOT, TEMPLATE_DIR


def _run_init(project_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "arforge.cli", "init", str(project_dir), *extra_args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "arforge.cli", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_init_default_creates_valid_project(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    result = _run_init(project_dir, "--name", "DemoSystem")
    assert result.returncode == 0, result.stdout + result.stderr

    expected_files = [
        "README.md",
        "autosar.project.yaml",
        "types/base_types.yaml",
        "types/implementation_types.yaml",
        "types/application_types.yaml",
        "units/units.yaml",
        "compu_methods/compu_methods.yaml",
        "modes/operation_mode.yaml",
        "interfaces/If_VehicleSpeed.yaml",
        "interfaces/If_OperationMode.yaml",
        "swcs/SpeedSensor.yaml",
        "swcs/SpeedReporter.yaml",
        "swcs/SystemSupervisor.yaml",
        "subcompositions/subcomposition_speed_path.yaml",
        "system.yaml",
    ]
    for rel in expected_files:
        assert (project_dir / rel).is_file(), f"Missing scaffold file: {rel}"

    project = load_and_validate_aggregator(project_dir / "autosar.project.yaml")
    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    project_yaml = (project_dir / "autosar.project.yaml").read_text(encoding="utf-8")
    system_yaml = (project_dir / "system.yaml").read_text(encoding="utf-8")
    modes_yaml = (project_dir / "modes" / "operation_mode.yaml").read_text(encoding="utf-8")
    vehicle_speed_interface_yaml = (project_dir / "interfaces" / "If_VehicleSpeed.yaml").read_text(encoding="utf-8")
    operation_mode_interface_yaml = (project_dir / "interfaces" / "If_OperationMode.yaml").read_text(encoding="utf-8")
    speed_sensor_yaml = (project_dir / "swcs" / "SpeedSensor.yaml").read_text(encoding="utf-8")
    speed_reporter_yaml = (project_dir / "swcs" / "SpeedReporter.yaml").read_text(encoding="utf-8")
    system_supervisor_yaml = (project_dir / "swcs" / "SystemSupervisor.yaml").read_text(encoding="utf-8")
    subcomposition_yaml = (project_dir / "subcompositions" / "subcomposition_speed_path.yaml").read_text(encoding="utf-8")
    base_types_yaml = (project_dir / "types" / "base_types.yaml").read_text(encoding="utf-8")
    application_types_yaml = (project_dir / "types" / "application_types.yaml").read_text(encoding="utf-8")
    implementation_types_yaml = (project_dir / "types" / "implementation_types.yaml").read_text(encoding="utf-8")

    assert project_yaml.startswith("# ARForge: Project input manifest")
    assert system_yaml.startswith("# ARForge: System composition")
    assert vehicle_speed_interface_yaml.startswith("# ARForge: Interface definition")
    assert speed_sensor_yaml.startswith("# ARForge: Software Component Type")
    assert speed_reporter_yaml.startswith("# ARForge: Software Component Type")
    assert system_supervisor_yaml.startswith("# ARForge: Software Component Type")
    assert subcomposition_yaml.startswith("# ARForge: Subcomposition type")
    assert modes_yaml.startswith("# ARForge: Mode declaration groups")

    assert "recommended small reference project" in readme
    assert "modes/operation_mode.yaml" in readme
    assert "interfaces/If_OperationMode.yaml" in readme
    assert "modeConditions" in readme
    assert "subcompositions/subcomposition_speed_path.yaml" in readme
    assert "internal assembly connectors" in readme
    assert "python -m arforge.cli validate autosar.project.yaml" in readme
    assert "python -m arforge.cli export autosar.project.yaml --out build/out --split-by-swc" in readme
    assert "python -m arforge.cli generate code autosar.project.yaml --lang c --out build/code" in readme

    assert 'modeDeclarationGroups:' in project_yaml
    assert '- "modes/*.yaml"' in project_yaml
    assert 'subcompositions:' in project_yaml
    assert 'description: "Operation modes used by the scaffolded starter project."' in modes_yaml
    assert 'name: "Mdg_OperationMode"' in modes_yaml
    assert 'name: "ACTIVE"' in modes_yaml
    assert 'name: "SERVICE"' in modes_yaml

    assert 'typeRef may point to either an atomic SWC type or a reusable subcomposition type.' in system_yaml
    assert 'name: "SpeedPath_0"' in system_yaml
    assert 'typeRef: "SubComposition_SpeedPath"' in system_yaml
    assert 'name: "SystemSupervisor_0"' in system_yaml
    assert 'from: "SystemSupervisor_0.Pp_OperationMode"' in system_yaml
    assert 'to: "SpeedPath_0.Rp_OperationModeIn"' in system_yaml
    assert 'from: "SpeedPath_0.Pp_VehicleSpeedOut"' in system_yaml
    assert 'to: "SystemSupervisor_0.Rp_VehicleSpeed"' in system_yaml

    assert 'description: "Sender-receiver interface for the current vehicle speed."' in vehicle_speed_interface_yaml
    assert 'description: "Mode switch interface for the starter project operation mode."' in operation_mode_interface_yaml
    assert 'modeGroupRef: "Mdg_OperationMode"' in operation_mode_interface_yaml

    assert 'description: "Publishes the current vehicle speed and reacts to the delegated operation mode."' in speed_sensor_yaml
    assert 'modeConditions:' in speed_sensor_yaml
    assert 'name: "Runnable_OnOperationActive"' in speed_sensor_yaml
    assert 'port: "Rp_OperationModeIn"' in speed_sensor_yaml
    assert 'name: "Pp_OperationMode"' in speed_sensor_yaml

    assert 'description: "Consumes the internal speed sample and republishes it on the subcomposition boundary."' in speed_reporter_yaml
    assert 'name: "Runnable_ReportVehicleSpeed"' in speed_reporter_yaml
    assert 'mode: "explicit"' in speed_reporter_yaml
    assert 'name: "Rp_OperationMode"' in speed_reporter_yaml
    assert 'modeSwitchEvents:' in speed_reporter_yaml
    assert 'modeConditions:' in speed_reporter_yaml
    assert 'mode: "ACTIVE"' in speed_reporter_yaml

    assert 'description: "Top-level SWC that drives the example operation mode and reads the speed value returned by the reusable subcomposition."' in system_supervisor_yaml
    assert 'name: "Runnable_InitOperationModeSource"' in system_supervisor_yaml
    assert 'name: "Runnable_ReadVehicleSpeed"' in system_supervisor_yaml
    assert 'timingEventMs: 20' in system_supervisor_yaml

    assert 'name: "SubComposition_SpeedPath"' in subcomposition_yaml
    assert 'name: "Rp_OperationModeIn"' in subcomposition_yaml
    assert 'name: "SpeedReporter_1"' in subcomposition_yaml
    assert 'typeRef: "SpeedSensor"' in subcomposition_yaml
    assert 'typeRef: "SpeedReporter"' in subcomposition_yaml
    assert 'delegationConnectors:' in subcomposition_yaml
    assert 'from: "SpeedSensor_1.Pp_VehicleSpeed"' in subcomposition_yaml
    assert 'to: "SpeedReporter_1.Rp_VehicleSpeed"' in subcomposition_yaml
    assert 'from: "SpeedSensor_1.Pp_OperationMode"' in subcomposition_yaml
    assert 'to: "SpeedReporter_1.Rp_OperationMode"' in subcomposition_yaml
    assert 'inner: "SpeedSensor_1.Rp_OperationModeIn"' in subcomposition_yaml
    assert 'inner: "SpeedReporter_1.Pp_VehicleSpeedOut"' in subcomposition_yaml

    assert 'category: "fixedLength"' in base_types_yaml
    assert 'description: "Vehicle speed value shared between the scaffolded SWC types."' in application_types_yaml
    assert 'description: "Raw implementation type for a vehicle speed sample."' in implementation_types_yaml

    validate_result = _run_cli("validate", str(project_dir / "autosar.project.yaml"))
    assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr

    cli_out_dir = tmp_path / "out_cli"
    export_result = _run_cli(
        "export",
        str(project_dir / "autosar.project.yaml"),
        "--out",
        str(cli_out_dir),
        "--split-by-swc",
    )
    assert export_result.returncode == 0, export_result.stdout + export_result.stderr
    for rel in [
        "DEMOSYSTEM_SharedTypes.arxml",
        "SpeedReporter.arxml",
        "SpeedSensor.arxml",
        "SystemSupervisor.arxml",
        "SubComposition_SpeedPath.arxml",
        "DemoSystem.arxml",
    ]:
        assert (cli_out_dir / rel).is_file(), f"Missing CLI export artifact: {rel}"

    out_dir = tmp_path / "out"
    written = write_outputs(project, template_dir=TEMPLATE_DIR, out=out_dir, split_by_swc=True)
    assert [path.name for path in written] == [
        "DEMOSYSTEM_SharedTypes.arxml",
        "SpeedReporter.arxml",
        "SpeedSensor.arxml",
        "SystemSupervisor.arxml",
        "SubComposition_SpeedPath.arxml",
        "DemoSystem.arxml",
    ]
    speed_reporter_xml = (out_dir / "SpeedReporter.arxml").read_text(encoding="utf-8")
    assert "<SWC-MODE-SWITCH-EVENT>" in speed_reporter_xml
    assert "<SHORT-NAME>MSE_Runnable_OnOperationActive_Rp_OperationMode_ACTIVE</SHORT-NAME>" in speed_reporter_xml


def test_init_no_example_creates_structure_only_project(tmp_path: Path) -> None:
    project_dir = tmp_path / "empty"
    result = _run_init(project_dir, "--no-example")
    assert result.returncode == 0, result.stdout + result.stderr

    expected_files = [
        "README.md",
        "autosar.project.yaml",
        "types/base_types.yaml",
        "types/implementation_types.yaml",
        "types/application_types.yaml",
        "units/units.yaml",
        "compu_methods/compu_methods.yaml",
        "modes/operation_mode.yaml",
        "system.yaml",
    ]
    for rel in expected_files:
        assert (project_dir / rel).is_file(), f"Missing scaffold file: {rel}"

    assert (project_dir / "interfaces").is_dir()
    assert (project_dir / "swcs").is_dir()
    assert (project_dir / "subcompositions").is_dir()
    assert list((project_dir / "interfaces").glob("*.yaml")) == []
    assert list((project_dir / "swcs").glob("*.yaml")) == []
    assert list((project_dir / "subcompositions").glob("*.yaml")) == []

    readme = (project_dir / "README.md").read_text(encoding="utf-8")
    system_yaml = (project_dir / "system.yaml").read_text(encoding="utf-8")
    project_yaml = (project_dir / "autosar.project.yaml").read_text(encoding="utf-8")
    modes_yaml = (project_dir / "modes" / "operation_mode.yaml").read_text(encoding="utf-8")

    assert "without example interfaces or SWCs" in readme
    assert "mode declaration groups under `modes/`" in readme
    assert "subcomposition types under `subcompositions/`" in readme
    assert system_yaml.startswith("# ARForge: System composition")
    assert "Example shape:" in system_yaml
    assert 'modeDeclarationGroups:' in project_yaml
    assert modes_yaml.startswith("# ARForge: Mode declaration groups")


def test_init_fails_for_non_empty_dir_without_force(tmp_path: Path) -> None:
    project_dir = tmp_path / "existing"
    project_dir.mkdir()
    (project_dir / "keep.txt").write_text("keep", encoding="utf-8")

    result = _run_init(project_dir)
    assert result.returncode != 0
    assert "not empty" in (result.stdout + result.stderr)
