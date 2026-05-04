"""Tests for external ARXML package layout export behavior.

This file covers external package layout loading, explicit per-element package
assignment, default package fallback, validation failures, split/monolithic
parity, and deterministic export results.
"""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from arforge.arxml_paths import ArxmlPathResolver
from arforge.exporter import write_outputs
from arforge.validate import ValidationError, load_aggregator, load_and_validate_aggregator, validate_semantic
from tests._shared import PACKAGE_LAYOUT_FEATURE_PROJECT, REPO_ROOT, TEMPLATE_DIR


MINIMAL_PROJECT = REPO_ROOT / "examples" / "minimal" / "autosar.project.yaml"


def _copy_fixture_tree(tmp_path: Path) -> Path:
    fixture_dir = PACKAGE_LAYOUT_FEATURE_PROJECT.parent
    target = tmp_path / "package_layout"
    shutil.copytree(fixture_dir, target)
    return target


def test_default_layout_compatibility_preserves_existing_minimal_paths(tmp_path: Path) -> None:
    project = load_aggregator(MINIMAL_PROJECT)

    out_file = tmp_path / "minimal.arxml"
    write_outputs(project, template_dir=TEMPLATE_DIR, out=out_file, split_by_swc=False)
    xml = out_file.read_text(encoding="utf-8")

    assert "/MINIMAL/Components/SpeedSensor" in xml
    assert "/MINIMAL/Interfaces/If_VehicleSpeed" in xml
    assert "/MINIMAL/ApplicationDataTypes/App_VehicleSpeed" in xml


def test_external_package_layout_loads_and_resolves_paths() -> None:
    project = load_aggregator(PACKAGE_LAYOUT_FEATURE_PROJECT)
    resolver = ArxmlPathResolver(project)

    assert project.packageLayout.name == "CompanyLayout"
    assert resolver.swc("BrakeController") == "/BRAKE_ECU/Components/Brake/BrakeController"
    assert resolver.swc("BrakeDisplay") == "/BRAKE_ECU/Components/Common/BrakeDisplay"
    assert resolver.interface("If_BrakeTorque") == "/BRAKE_ECU/Interfaces/Brake/If_BrakeTorque"
    assert resolver.interface("If_BrakeMode") == "/BRAKE_ECU/Interfaces/Common/If_BrakeMode"
    assert resolver.application_type("App_BrakeTorque") == "/BRAKE_ECU/DataTypes/Application/App_BrakeTorque"
    assert resolver.mode_group("Mdg_BrakeMode") == "/BRAKE_ECU/Modes/Mdg_BrakeMode"


def test_package_layout_export_uses_explicit_and_default_packages(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(PACKAGE_LAYOUT_FEATURE_PROJECT)

    out_file = tmp_path / "package_layout.arxml"
    write_outputs(project, template_dir=TEMPLATE_DIR, out=out_file, split_by_swc=False)
    xml = out_file.read_text(encoding="utf-8")

    assert "/BRAKE_ECU/Components/Brake/BrakeController" in xml
    assert "/BRAKE_ECU/Components/Common/BrakeDisplay" in xml
    assert "/BRAKE_ECU/Components/Common/BrakeModeProvider" in xml
    assert "/BRAKE_ECU/Interfaces/Brake/If_BrakeTorque" in xml
    assert "/BRAKE_ECU/Interfaces/Common/If_BrakeMode" in xml
    assert "/BRAKE_ECU/DataTypes/Application/App_BrakeTorque" in xml
    assert "/BRAKE_ECU/Modes/Mdg_BrakeMode/OFF" in xml
    assert "<SHORT-NAME>Brake</SHORT-NAME>" in xml
    assert "<SHORT-NAME>Common</SHORT-NAME>" in xml


def test_invalid_explicit_package_assignment_reports_validation_error(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_tree(tmp_path)
    swc_path = fixture_root / "swcs" / "BrakeController.yaml"
    swc_data = yaml.safe_load(swc_path.read_text(encoding="utf-8"))
    swc_data["swc"]["package"] = "Components/Unknown"
    swc_path.write_text(yaml.safe_dump(swc_data, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValidationError) as excinfo:
        load_and_validate_aggregator(fixture_root / "autosar.project.yaml")

    assert "not listed in allowedPackages" in "\n".join(excinfo.value.errors)


def test_invalid_layout_default_not_allowed_reports_validation_error(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_tree(tmp_path)
    layout_path = fixture_root / "packages" / "company_layout.yaml"
    layout_data = yaml.safe_load(layout_path.read_text(encoding="utf-8"))
    layout_data["packageLayout"]["defaults"]["interface"] = "Interfaces/Missing"
    layout_path.write_text(yaml.safe_dump(layout_data, sort_keys=False), encoding="utf-8")

    project = load_aggregator(fixture_root / "autosar.project.yaml")
    errors = validate_semantic(project)

    assert any("default 'interface: Interfaces/Missing' is not listed in allowedPackages" in error for error in errors)


def test_invalid_layout_path_syntax_is_rejected_early(tmp_path: Path) -> None:
    fixture_root = _copy_fixture_tree(tmp_path)
    layout_path = fixture_root / "packages" / "company_layout.yaml"
    layout_data = yaml.safe_load(layout_path.read_text(encoding="utf-8"))
    layout_data["packageLayout"]["allowedPackages"].append("/Broken")
    layout_path.write_text(yaml.safe_dump(layout_data, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValidationError) as excinfo:
        load_aggregator(fixture_root / "autosar.project.yaml")

    assert "does not match" in "\n".join(excinfo.value.errors)


def test_package_layout_split_export_matches_monolithic_refs(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(PACKAGE_LAYOUT_FEATURE_PROJECT)

    mono_path = tmp_path / "mono.arxml"
    split_dir = tmp_path / "split"
    write_outputs(project, template_dir=TEMPLATE_DIR, out=mono_path, split_by_swc=False)
    write_outputs(project, template_dir=TEMPLATE_DIR, out=split_dir, split_by_swc=True)

    mono_xml = mono_path.read_text(encoding="utf-8")
    controller_xml = (split_dir / "BrakeController.arxml").read_text(encoding="utf-8")
    system_xml = (split_dir / "BrakeSystem.arxml").read_text(encoding="utf-8")

    expected_refs = [
        "/BRAKE_ECU/Interfaces/Brake/If_BrakeTorque/BrakeTorque",
        "/BRAKE_ECU/Interfaces/Common/If_BrakeMode/If_BrakeMode_ModeGroup",
        "/BRAKE_ECU/Modes/Mdg_BrakeMode/OFF",
        "/BRAKE_ECU/Components/Brake/BrakeController",
    ]

    for ref in expected_refs:
        assert ref in mono_xml
    assert "/BRAKE_ECU/Interfaces/Brake/If_BrakeTorque/BrakeTorque" in controller_xml
    assert "/BRAKE_ECU/Components/Brake/BrakeController" in system_xml


def test_package_layout_export_is_deterministic(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(PACKAGE_LAYOUT_FEATURE_PROJECT)

    first = tmp_path / "first"
    second = tmp_path / "second"
    write_outputs(project, template_dir=TEMPLATE_DIR, out=first, split_by_swc=True)
    write_outputs(project, template_dir=TEMPLATE_DIR, out=second, split_by_swc=True)

    first_files = sorted(path.name for path in first.iterdir())
    second_files = sorted(path.name for path in second.iterdir())
    assert first_files == second_files
    for name in first_files:
        assert (first / name).read_text(encoding="utf-8") == (second / name).read_text(encoding="utf-8")
