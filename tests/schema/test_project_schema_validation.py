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
