from __future__ import annotations

import hashlib
from pathlib import Path

from arforge.codegen import write_code_outputs
from arforge.validate import load_and_validate_aggregator
from tests._shared import TEMPLATE_DIR, VALID_PROJECT

def test_generate_code_writes_expected_files_for_example_project(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = TEMPLATE_DIR
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
    template_dir = TEMPLATE_DIR
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
    template_dir = TEMPLATE_DIR
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
