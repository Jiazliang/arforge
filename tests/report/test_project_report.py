"""Tests for project report rendering.

This file verifies expected report sections and counts, and checks that
writing the report is deterministic for the same project input.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from arforge.reporting import render_project_report, write_project_report
from arforge.validate import load_and_validate_aggregator
from tests._shared import REPO_ROOT, TEMPLATE_DIR, VALID_PROJECT

def test_render_project_report_contains_expected_sections_and_counts() -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)

    report = render_project_report(project, template_dir=REPO_ROOT / "templates", project_path=VALID_PROJECT)

    assert "# Project Report" in report
    assert "## Overview" in report
    assert "## Counts" in report
    assert "## Unconnected Ports" in report
    assert "## Timing Overview" in report
    assert "| SWC types | 3 |" in report
    assert "| Reusable subcomposition types | 1 |" in report
    assert "| Total component prototypes | 4 |" in report
    assert "| Sender-Receiver interfaces | 1 |" in report
    assert "| Client-Server interfaces | 0 |" in report
    assert "| Mode-Switch interfaces | 1 |" in report
    assert "### Sender-Receiver" in report
    assert "### Mode-Switch" in report
    assert "DiagManager_0" in report
    assert "This report summarizes modeled architecture. Run `arforge validate` separately for findings." in report

def test_project_report_is_deterministic(tmp_path: Path) -> None:
    project = load_and_validate_aggregator(VALID_PROJECT)
    template_dir = REPO_ROOT / "templates"
    out1 = tmp_path / "report_1.md"
    out2 = tmp_path / "report_2.md"

    write_project_report(project, template_dir=template_dir, out=out1, project_path=VALID_PROJECT)
    write_project_report(project, template_dir=template_dir, out=out2, project_path=VALID_PROJECT)

    data1 = out1.read_bytes()
    data2 = out2.read_bytes()
    assert data1 == data2
    assert hashlib.sha256(data1).hexdigest() == hashlib.sha256(data2).hexdigest()
