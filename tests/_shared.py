from __future__ import annotations

from pathlib import Path
import re
from xml.etree import ElementTree as ET

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "templates"
VALID_PROJECT = REPO_ROOT / "examples" / "features" / "subcomposition" / "autosar.project.yaml"
MODES_FEATURE_PROJECT = REPO_ROOT / "examples" / "features" / "modes" / "autosar.project.yaml"
PACKAGE_LAYOUT_FEATURE_PROJECT = REPO_ROOT / "examples" / "features" / "package_layout" / "autosar.project.yaml"
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
WARNING_PROJECT = INVALID_DIR / "project_sr_read_unconnected.yaml"
ERROR_PROJECT = INVALID_DIR / "project_bad_runnable_access.yaml"
MIXED_PROJECT = INVALID_DIR / "project_sr_read_unconnected.yaml"
CS_SERVER_WARNING_PROJECT = INVALID_DIR / "project_cs_server_oie_unconnected.yaml"
UNUSED_MODE_GROUP_PROJECT = INVALID_DIR / "project_unused_mode_group.yaml"
CONNECTED_UNUSED_MODE_SWITCH_PROJECT = INVALID_DIR / "project_connected_mode_switch_port_unused.yaml"
SR_ONE_TO_MANY_PROJECT = INVALID_DIR / "project_sr_one_to_many_valid.yaml"
SR_N_TO_1_PROJECT = INVALID_DIR / "project_sr_n_to_1_warning.yaml"
SAMPLE_NAMING_PROFILE = REPO_ROOT / "examples" / "features" / "validation_profiles" / "naming.yaml"
SAMPLE_STRICT_HYGIENE_PROFILE = REPO_ROOT / "examples" / "features" / "validation_profiles" / "strict_hygiene.yaml"
SAMPLE_PROFILE_FIXTURE = REPO_ROOT / "examples" / "features" / "validation_profiles" / "fixtures" / "profile_demo.project.yaml"


def is_project_fixture(path: Path) -> bool:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return isinstance(data, dict) and "autosar" in data and "inputs" in data


def invalid_project_fixtures() -> list[Path]:
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
    return [
        path
        for path in sorted(INVALID_DIR.glob("*.yaml"))
        if is_project_fixture(path) and path.name not in non_error_fixtures
    ]


def extract_r_port_fragment(xml: str, port_name: str) -> str:
    match = re.search(
        rf"<R-PORT-PROTOTYPE>\s*<SHORT-NAME>{re.escape(port_name)}</SHORT-NAME>(.*?)</R-PORT-PROTOTYPE>",
        xml,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing R-PORT-PROTOTYPE for {port_name}"
    return match.group(1)


def extract_element_fragment(xml: str, tag_pattern: str, short_name: str) -> str:
    match = re.search(
        rf"<(?:{tag_pattern})>\s*<SHORT-NAME>{re.escape(short_name)}</SHORT-NAME>(.*?)</(?:{tag_pattern})>",
        xml,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing element {short_name} for tag pattern {tag_pattern}"
    return match.group(0)


def extract_internal_behavior_fragment(xml: str, swc_name: str) -> str:
    match = re.search(
        rf"<SWC-INTERNAL-BEHAVIOR>\s*<SHORT-NAME>IB_{re.escape(swc_name)}</SHORT-NAME>(.*?)</SWC-INTERNAL-BEHAVIOR>",
        xml,
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing internal behavior for {swc_name}"
    return match.group(0)


def extract_mode_declaration_group_fragment(xml: str, group_name: str) -> str:
    return extract_element_fragment(xml, "MODE-DECLARATION-GROUP", group_name)


def normalize_xml_fragment(xml: str) -> str:
    return re.sub(r">\s+<", "><", xml).strip()


def parse_xml_fragment(xml: str) -> ET.Element:
    return ET.fromstring(xml)
