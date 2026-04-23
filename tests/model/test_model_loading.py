"""Tests for parsed model content loaded into the internal representation.

These checks confirm that descriptions, normalized values, and selected
defaults from the main example project are present in the model IR.
"""

from __future__ import annotations

from arforge.validate import load_and_validate_aggregator
from tests._shared import VALID_PROJECT

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
    assert power_state_port.comSpec is None
    forwarded_speed_port = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedDisplay"
        for port in swc.ports
        if port.name == "Pp_VehicleSpeedOut"
    )
    assert forwarded_speed_port.description == "Provided sender-receiver port delegated to the subcomposition boundary."
    explicit_receiver = next(
        port
        for swc in project.swcs
        if swc.name == "SpeedDisplay"
        for port in swc.ports
        if port.name == "Rp_VehicleSpeed"
    )
    assert explicit_receiver.comSpec is not None
    assert explicit_receiver.comSpec.initValue == 0
    diag_receiver = next(
        port
        for swc in project.swcs
        if swc.name == "DiagManager"
        for port in swc.ports
        if port.name == "Rp_VehicleSpeed"
    )
    assert diag_receiver.comSpec is not None
    assert diag_receiver.comSpec.initValue == 0
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
    assert next(base_type for base_type in project.baseTypes if base_type.name == "uint8").category == "FIXED_LENGTH"

def test_main_example_mode_declaration_group_is_loaded_into_model_ir() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    assert [group.name for group in project.modeDeclarationGroups] == ["Mdg_PowerState"]
    assert project.modeDeclarationGroups[0].description == "Power state modes for the ECU."
    assert project.modeDeclarationGroups[0].category == "EXPLICIT_ORDER"
    assert project.modeDeclarationGroups[0].initialMode == "OFF"
    assert project.modeDeclarationGroups[0].onTransitionValue == 255
    assert [mode.name for mode in project.modeDeclarationGroups[0].modes] == ["OFF", "ON", "SLEEP"]
    assert [mode.value for mode in project.modeDeclarationGroups[0].modes] == [0, 1, 2]

def test_mode_group_yaml_category_alias_is_normalized_for_export() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    assert project.modeDeclarationGroups[0].category == "EXPLICIT_ORDER"

def test_main_example_omitted_swc_category_defaults_to_application() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    assert next(swc for swc in project.swcs if swc.name == "SpeedSensor").category == "application"
    assert next(swc for swc in project.swcs if swc.name == "SpeedDisplay").category == "application"
