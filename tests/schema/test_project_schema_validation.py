"""Tests for schema-level validation behavior.

This file focuses on failures that should be rejected by JSON Schema or
early loading rules before semantic validation is reached.
"""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator
import pytest
import yaml

from arforge.validate import ValidationError, load_aggregator
from tests._shared import INVALID_DIR, REPO_ROOT

def _schema_errors(schema_name: str, data: object) -> list[str]:
    schema = json.loads((REPO_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors: list[str] = []

    def collect(error: object) -> None:
        err = error
        path = ".".join(str(part) for part in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
        for child in sorted(err.context, key=lambda item: (list(item.absolute_path), item.message)):
            collect(child)

    for root_error in sorted(validator.iter_errors(data), key=lambda err: (list(err.absolute_path), err.message)):
        collect(root_error)

    return errors

def test_schema_accepts_supported_text_table_unit_ref() -> None:
    errors = _schema_errors(
        "compu_methods.schema.json",
        {
            "compuMethods": [
                {
                    "name": "CM_PowerState",
                    "category": "textTable",
                    "unitRef": "NoUnit",
                    "entries": [
                        {"value": 0, "label": "OFF"},
                        {"value": 1, "label": "ON"},
                    ],
                }
            ]
        },
    )

    assert errors == []

def test_implementation_type_schema_rejects_zero_length_array_earlier() -> None:
    data = yaml.safe_load((INVALID_DIR / "types" / "implementation_types_array_zero_length.yaml").read_text(encoding="utf-8"))

    errors = _schema_errors("implementation_types.schema.json", data)

    assert any("length: 0 is less than the minimum of 1" in error for error in errors)

def test_interface_schema_rejects_negative_possible_error_code_earlier() -> None:
    data = yaml.safe_load((INVALID_DIR / "interfaces" / "If_Diagnostics_negative_error_code.yaml").read_text(encoding="utf-8"))

    errors = _schema_errors("interface.schema.json", data)

    assert any("code: -1 is less than the minimum of 0" in error for error in errors)

def test_tightened_project_fixture_with_multiple_runnable_triggers_fails_earlier() -> None:
    with pytest.raises(ValidationError) as excinfo:
        load_aggregator(INVALID_DIR / "project_runnable_both_trigger_styles.yaml")

    assert "is valid under each of" in "\n".join(excinfo.value.errors)

def test_swc_schema_rejects_false_init_event_flag() -> None:
    errors = _schema_errors(
        "swc.schema.json",
        {
            "swc": {
                "name": "SpeedSensor",
                "runnables": [
                    {
                        "name": "Runnable_Init",
                        "initEvent": False,
                    }
                ],
                "ports": [
                    {
                        "name": "Pp_VehicleSpeed",
                        "direction": "provides",
                        "interfaceRef": "If_VehicleSpeed",
                    }
                ],
            }
        },
    )

    assert any("True was expected" in error for error in errors)

def test_swc_schema_accepts_runnable_mode_conditions() -> None:
    errors = _schema_errors(
        "swc.schema.json",
        {
            "swc": {
                "name": "BrakeController",
                "runnables": [
                    {
                        "name": "Runnable_ControlBrakeTorque",
                        "timingEventMs": 10,
                        "modeConditions": [
                            {
                                "port": "Rp_BrakeEcuMode",
                                "mode": "NORMAL",
                            }
                        ],
                    }
                ],
                "ports": [
                    {
                        "name": "Rp_BrakeEcuMode",
                        "direction": "requires",
                        "interfaceRef": "If_BrakeEcuMode",
                    }
                ],
            }
        },
    )

    assert errors == []

def test_swc_schema_rejects_invalid_mode_condition_shape() -> None:
    errors = _schema_errors(
        "swc.schema.json",
        {
            "swc": {
                "name": "BrakeController",
                "runnables": [
                    {
                        "name": "Runnable_ControlBrakeTorque",
                        "timingEventMs": 10,
                        "modeConditions": [
                            {
                                "port": "Rp_BrakeEcuMode",
                                "extra": "nope",
                            }
                        ],
                    }
                ],
                "ports": [
                    {
                        "name": "Rp_BrakeEcuMode",
                        "direction": "requires",
                        "interfaceRef": "If_BrakeEcuMode",
                    }
                ],
            }
        },
    )

    assert any("runnables.0.modeConditions.0" in error and "additional properties" in error.lower() for error in errors)
    assert any("runnables.0.modeConditions.0" in error and "'mode' is a required property" in error for error in errors)

def test_swc_schema_rejects_mode_conditions_on_init_event_runnable() -> None:
    errors = _schema_errors(
        "swc.schema.json",
        {
            "swc": {
                "name": "BrakeController",
                "runnables": [
                    {
                        "name": "Runnable_InitBrake",
                        "initEvent": True,
                        "modeConditions": [
                            {
                                "port": "Rp_BrakeEcuMode",
                                "mode": "NORMAL",
                            }
                        ],
                    }
                ],
                "ports": [
                    {
                        "name": "Rp_BrakeEcuMode",
                        "direction": "requires",
                        "interfaceRef": "If_BrakeEcuMode",
                    }
                ],
            }
        },
    )

    assert any("runnables.0" in error and "should not be valid" in error.lower() for error in errors)

def test_schema_validation_errors_are_deterministic_for_same_fixture() -> None:
    fixture = INVALID_DIR / "project_impl_array_zero_length.yaml"

    first_errors: list[str] = []
    second_errors: list[str] = []
    for target in (first_errors, second_errors):
        with pytest.raises(ValidationError) as excinfo:
            load_aggregator(fixture)
        target.extend(excinfo.value.errors)

    assert first_errors == second_errors

def test_mode_group_schema_rejects_explicit_order_without_on_transition_value() -> None:
    with pytest.raises(ValidationError) as excinfo:
        load_aggregator(INVALID_DIR / "project_mode_group_missing_on_transition.yaml")

    assert "onTransitionValue" in "\n".join(excinfo.value.errors)

def test_mode_group_schema_rejects_explicit_order_without_mode_value() -> None:
    with pytest.raises(ValidationError) as excinfo:
        load_aggregator(INVALID_DIR / "project_mode_group_missing_mode_value.yaml")

    assert "value" in "\n".join(excinfo.value.errors)

def test_system_schema_rejects_connector_selectors() -> None:
    with pytest.raises(ValidationError) as excinfo:
        load_aggregator(INVALID_DIR / "project_bad_operation.yaml")

    errors = "\n".join(excinfo.value.errors)
    assert "operation" in errors
    assert "additional properties" in errors.lower()


def test_project_schema_accepts_package_layout_ref() -> None:
    errors = _schema_errors(
        "aggregator.schema.json",
        {
            "autosar": {
                "version": "4.2",
                "rootPackage": "BRAKE_ECU",
                "packageLayoutRef": "packages/company_layout.yaml",
            },
            "inputs": {
                "baseTypes": "types/base_types.yaml",
                "implementationDataTypes": "types/implementation_types.yaml",
                "applicationDataTypes": "types/application_types.yaml",
                "interfaces": ["interfaces/*.yaml"],
                "swcs": ["swcs/*.yaml"],
                "system": "system.yaml",
            },
        },
    )

    assert errors == []


def test_schema_accepts_nested_package_assignment_on_packageable_element() -> None:
    errors = _schema_errors(
        "swc.schema.json",
        {
            "swc": {
                "name": "BrakeController",
                "package": "Components/Brake",
                "runnables": [
                    {
                        "name": "Runnable_ControlBrakeTorque",
                        "timingEventMs": 10,
                    }
                ],
                "ports": [
                    {
                        "name": "Pp_BrakeTorque",
                        "direction": "provides",
                        "interfaceRef": "If_BrakeTorque",
                    }
                ],
            }
        },
    )

    assert errors == []


def test_schema_rejects_invalid_package_path_on_packageable_element() -> None:
    errors = _schema_errors(
        "interface.schema.json",
        {
            "interface": {
                "name": "If_BrakeTorque",
                "type": "senderReceiver",
                "package": "/Interfaces/Brake",
                "dataElements": [
                    {
                        "name": "BrakeTorque",
                        "typeRef": "App_BrakeTorque",
                    }
                ],
            }
        },
    )

    assert any("package" in error and "does not match" in error for error in errors)
