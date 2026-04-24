"""Tests for Markdown model diff rendering.

This file verifies the expected report sections, representative added/removed
and changed items, and deterministic output for the same pair of project
inputs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from arforge.diffing import render_model_diff, write_model_diff
from arforge.validate import load_aggregator
from tests._shared import REPO_ROOT, TEMPLATE_DIR


SAMPLE_PROJECTS_ROOT = REPO_ROOT / "tests" / "diff" / "sample_projects"
BASELINE_PROJECT = SAMPLE_PROJECTS_ROOT / "baseline" / "autosar.project.yaml"
UPDATED_PROJECT = SAMPLE_PROJECTS_ROOT / "updated" / "autosar.project.yaml"


def test_render_model_diff_contains_expected_sections() -> None:
    baseline = load_aggregator(BASELINE_PROJECT)
    updated = load_aggregator(UPDATED_PROJECT)

    report = render_model_diff(
        baseline,
        updated,
        template_dir=TEMPLATE_DIR,
        old_project_path=BASELINE_PROJECT,
        new_project_path=UPDATED_PROJECT,
    )

    assert "# ARForge Model Diff" in report
    assert "## Summary" in report
    assert "## SWCs" in report
    assert "## Interfaces" in report
    assert "## Ports" in report
    assert "## Component Prototypes" in report
    assert "## Connectors" in report
    assert "## Compositions and Subcompositions" in report
    assert "## Notes" in report


def test_model_diff_reports_added_removed_and_changed_items() -> None:
    baseline = load_aggregator(BASELINE_PROJECT)
    updated = load_aggregator(UPDATED_PROJECT)

    report = render_model_diff(baseline, updated, template_dir=TEMPLATE_DIR)

    assert "`NewMonitor`" in report
    assert "`LegacyUnit`" in report
    assert "`If_Status` (`senderReceiver`)" in report
    assert "`Sensor.Pp_VehicleSpeed`" in report
    assert "`interfaceRef`: `If_VehicleSpeed` -> `If_VehicleSpeed_Backup`" in report
    assert "`Sensor.Rp_Command`" in report
    assert "`direction`: `requires` -> `provides`" in report
    assert "`kind`: `clientServer` -> `senderReceiver`" in report
    assert "`system: Display_1`" in report
    assert "`typeRef`: `Display` -> `NewMonitor`" in report
    assert "`system: Sensor_1.Pp_VehicleSpeed -> Added_1.Rp_VehicleSpeed`" in report
    assert "`system: Sensor_1.Pp_VehicleSpeed -> Display_1.Rp_VehicleSpeed`" in report
    assert "`SubCluster`" in report
    assert "`contained prototypes`:" in report


def test_model_diff_is_deterministic(tmp_path: Path) -> None:
    baseline = load_aggregator(BASELINE_PROJECT)
    updated = load_aggregator(UPDATED_PROJECT)
    out1 = tmp_path / "diff_1.md"
    out2 = tmp_path / "diff_2.md"

    write_model_diff(baseline, updated, template_dir=TEMPLATE_DIR, out=out1)
    write_model_diff(baseline, updated, template_dir=TEMPLATE_DIR, out=out2)

    data1 = out1.read_bytes()
    data2 = out2.read_bytes()
    assert data1 == data2
    assert hashlib.sha256(data1).hexdigest() == hashlib.sha256(data2).hexdigest()
