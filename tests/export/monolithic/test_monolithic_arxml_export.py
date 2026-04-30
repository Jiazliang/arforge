"""Tests for monolithic ARXML export behavior.

These checks compare monolithic output with split output for equivalent
fragments and verify deterministic single-file export results.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re

from arforge.exporter import write_outputs
from arforge.validate import load_and_validate_aggregator
from tests._shared import (
    MODES_FEATURE_PROJECT,
    SHARED_EXAMPLE_OUTPUT,
    SUBCOMPOSITION_EXAMPLE_OUTPUT,
    TEMPLATE_DIR,
    VALID_PROJECT,
    extract_element_fragment,
    extract_internal_behavior_fragment,
    extract_mode_declaration_group_fragment,
    extract_r_port_fragment,
    normalize_xml_fragment,
    parse_xml_fragment,
)

def test_monolithic_and_split_shared_type_fragments_are_equivalent(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = TEMPLATE_DIR
    monolithic_out = tmp_path / "DemoProject.arxml"
    split_out = tmp_path / "split"

    _ = write_outputs(project, template_dir=template_dir, out=monolithic_out, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=split_out, split_by_swc=True)

    monolithic_xml = monolithic_out.read_text(encoding="utf-8")
    shared_xml = (split_out / SHARED_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    mono_app_type = extract_element_fragment(monolithic_xml, "APPLICATION-PRIMITIVE-DATA-TYPE", "App_VehicleSpeed")
    split_app_type = extract_element_fragment(shared_xml, "APPLICATION-PRIMITIVE-DATA-TYPE", "App_VehicleSpeed")
    assert "<SW-DATA-DEF-PROPS>" in mono_app_type
    assert "<SW-DATA-DEF-PROPS>" in split_app_type
    assert "<CATEGORY>VALUE</CATEGORY>" in mono_app_type
    assert "<CATEGORY>VALUE</CATEGORY>" in split_app_type
    assert "<COMPU-METHOD-REF DEST=\"COMPU-METHOD\">/DEMO/CompuMethods/CM_VehicleSpeed_Kph</COMPU-METHOD-REF>" in mono_app_type
    assert "<COMPU-METHOD-REF DEST=\"COMPU-METHOD\">/DEMO/CompuMethods/CM_VehicleSpeed_Kph</COMPU-METHOD-REF>" in split_app_type
    assert "<DATA-CONSTR-REF DEST=\"DATA-CONSTR\">/DEMO/DataConstrs/DC_App_VehicleSpeed</DATA-CONSTR-REF>" in mono_app_type
    assert "<DATA-CONSTR-REF DEST=\"DATA-CONSTR\">/DEMO/DataConstrs/DC_App_VehicleSpeed</DATA-CONSTR-REF>" in split_app_type
    assert normalize_xml_fragment(mono_app_type) == normalize_xml_fragment(split_app_type)

    mono_compu = extract_element_fragment(monolithic_xml, "COMPU-METHOD", "CM_VehicleSpeed_Kph")
    split_compu = extract_element_fragment(shared_xml, "COMPU-METHOD", "CM_VehicleSpeed_Kph")
    assert "<COMPU-INTERNAL-TO-PHYS>" in mono_compu
    assert "<COMPU-INTERNAL-TO-PHYS>" in split_compu
    assert "<FACTOR>" not in mono_compu
    assert "<FACTOR>" not in split_compu
    assert normalize_xml_fragment(mono_compu) == normalize_xml_fragment(split_compu)

    mono_mode_group = extract_mode_declaration_group_fragment(monolithic_xml, "Mdg_PowerState")
    split_mode_group = extract_mode_declaration_group_fragment(shared_xml, "Mdg_PowerState")
    assert "<CATEGORY>EXPLICIT_ORDER</CATEGORY>" in mono_mode_group
    assert "<CATEGORY>EXPLICIT_ORDER</CATEGORY>" in split_mode_group
    assert "<ON-TRANSITION-VALUE>255</ON-TRANSITION-VALUE>" in mono_mode_group
    assert "<ON-TRANSITION-VALUE>255</ON-TRANSITION-VALUE>" in split_mode_group
    assert "<VALUE>0</VALUE>" in mono_mode_group
    assert "<VALUE>1</VALUE>" in mono_mode_group
    assert "<VALUE>2</VALUE>" in mono_mode_group
    mono_mode_group_element = parse_xml_fragment(mono_mode_group)
    split_mode_group_element = parse_xml_fragment(split_mode_group)
    assert [child.tag for child in mono_mode_group_element] == [child.tag for child in split_mode_group_element]
    assert normalize_xml_fragment(mono_mode_group) == normalize_xml_fragment(split_mode_group)

def test_monolithic_and_split_swc_fragments_are_equivalent(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = TEMPLATE_DIR
    monolithic_out = tmp_path / "DemoProject.arxml"
    split_out = tmp_path / "split"

    _ = write_outputs(project, template_dir=template_dir, out=monolithic_out, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=split_out, split_by_swc=True)

    monolithic_xml = monolithic_out.read_text(encoding="utf-8")
    split_xml = (split_out / "SpeedDisplay.arxml").read_text(encoding="utf-8")

    mono_behavior = extract_internal_behavior_fragment(monolithic_xml, "SpeedDisplay")
    split_behavior = extract_internal_behavior_fragment(split_xml, "SpeedDisplay")
    assert mono_behavior.index("<EVENTS>") < mono_behavior.index("<RUNNABLES>")
    assert split_behavior.index("<EVENTS>") < split_behavior.index("<RUNNABLES>")
    assert "<SWC-MODE-SWITCH-EVENT>" in mono_behavior
    assert "<SWC-MODE-SWITCH-EVENT>" in split_behavior
    assert "<MODE-SWITCH-EVENT>" not in mono_behavior
    assert "<MODE-SWITCH-EVENT>" not in split_behavior
    assert normalize_xml_fragment(mono_behavior) == normalize_xml_fragment(split_behavior)

    mono_component = extract_element_fragment(
        monolithic_xml,
        "APPLICATION-SW-COMPONENT-TYPE|SERVICE-SW-COMPONENT-TYPE|COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "SpeedDisplay",
    )
    split_component = extract_element_fragment(
        split_xml,
        "APPLICATION-SW-COMPONENT-TYPE|SERVICE-SW-COMPONENT-TYPE|COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
        "SpeedDisplay",
    )
    mono_r_port = extract_r_port_fragment(mono_component, "Rp_VehicleSpeed")
    split_r_port = extract_r_port_fragment(split_component, "Rp_VehicleSpeed")
    assert mono_r_port.index("<REQUIRED-COM-SPECS>") < mono_r_port.index("<REQUIRED-INTERFACE-TREF")
    assert split_r_port.index("<REQUIRED-COM-SPECS>") < split_r_port.index("<REQUIRED-INTERFACE-TREF")
    assert "<DATA-ELEMENT-REF DEST=\"VARIABLE-DATA-PROTOTYPE\">/DEMO/Interfaces/If_VehicleSpeed/VehicleSpeed</DATA-ELEMENT-REF>" in mono_r_port
    assert "<DATA-ELEMENT-REF DEST=\"VARIABLE-DATA-PROTOTYPE\">/DEMO/Interfaces/If_VehicleSpeed/VehicleSpeed</DATA-ELEMENT-REF>" in split_r_port
    assert "<INIT-VALUE>" in mono_r_port
    assert "<INIT-VALUE>" in split_r_port
    assert normalize_xml_fragment(mono_r_port) == normalize_xml_fragment(split_r_port)

    mono_base_type = extract_element_fragment(monolithic_xml, "SW-BASE-TYPE", "uint16")
    split_base_type = extract_element_fragment((split_out / SHARED_EXAMPLE_OUTPUT).read_text(encoding="utf-8"), "SW-BASE-TYPE", "uint16")
    assert "<CATEGORY>FIXED_LENGTH</CATEGORY>" in mono_base_type
    assert "<CATEGORY>FIXED_LENGTH</CATEGORY>" in split_base_type
    assert normalize_xml_fragment(mono_base_type) == normalize_xml_fragment(split_base_type)

def test_monolithic_and_split_subcomposition_fragments_are_equivalent(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = TEMPLATE_DIR
    monolithic_out = tmp_path / "DemoProject.arxml"
    split_out = tmp_path / "split"

    _ = write_outputs(project, template_dir=template_dir, out=monolithic_out, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=split_out, split_by_swc=True)

    monolithic_xml = monolithic_out.read_text(encoding="utf-8")
    split_xml = (split_out / SUBCOMPOSITION_EXAMPLE_OUTPUT).read_text(encoding="utf-8")

    mono_subcomposition = extract_element_fragment(monolithic_xml, "COMPOSITION-SW-COMPONENT-TYPE", "SubComposition_SpeedCluster")
    split_subcomposition = extract_element_fragment(split_xml, "COMPOSITION-SW-COMPONENT-TYPE", "SubComposition_SpeedCluster")
    assert "<P-PORT-IN-COMPOSITION-INSTANCE-REF>" in mono_subcomposition
    assert "<P-PORT-IN-COMPOSITION-INSTANCE-REF>" in split_subcomposition
    assert "<R-PORT-IN-COMPOSITION-INSTANCE-REF>" in mono_subcomposition
    assert "<R-PORT-IN-COMPOSITION-INSTANCE-REF>" in split_subcomposition
    assert re.search(r"<INNER-PORT-IREF>\s*<CONTEXT-COMPONENT-REF", mono_subcomposition) is None
    assert re.search(r"<INNER-PORT-IREF>\s*<CONTEXT-COMPONENT-REF", split_subcomposition) is None
    assert normalize_xml_fragment(mono_subcomposition) == normalize_xml_fragment(split_subcomposition)

def test_monolithic_export_is_deterministic(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = TEMPLATE_DIR
    out1 = tmp_path / "DemoProject1.arxml"
    out2 = tmp_path / "DemoProject2.arxml"

    _ = write_outputs(project, template_dir=template_dir, out=out1, split_by_swc=False)
    _ = write_outputs(project, template_dir=template_dir, out=out2, split_by_swc=False)

    data1 = out1.read_bytes()
    data2 = out2.read_bytes()
    assert data1 == data2
    assert hashlib.sha256(data1).hexdigest() == hashlib.sha256(data2).hexdigest()

def test_monolithic_modes_example_keeps_mode_conditions_out_of_arxml(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(MODES_FEATURE_PROJECT)
    out = tmp_path / "FeatureModes.arxml"

    _ = write_outputs(project, template_dir=TEMPLATE_DIR, out=out, split_by_swc=False)

    xml = out.read_text(encoding="utf-8")
    assert "<SWC-MODE-SWITCH-EVENT>" in xml
    assert "Runnable_ProcessWhenActive" in xml
    assert "MODE-DEPENDENC" not in xml
    assert "DISABLED-MODE-IREF" not in xml
