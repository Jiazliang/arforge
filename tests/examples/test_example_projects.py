"""Tests for shipped example projects and invalid example fixtures.

This file ensures the main reference example stays valid and that the
`examples/invalid/` project fixtures continue to fail as intended.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arforge.validate import ValidationError, load_and_validate_aggregator
from tests._shared import VALID_PROJECT, invalid_project_fixtures

def test_validate_main_example_passes() -> None:
    load_and_validate_aggregator(VALID_PROJECT)

@pytest.mark.parametrize(
    "fixture_path",
    invalid_project_fixtures(),
    ids=lambda p: p.name,
)
def test_invalid_project_fixtures_fail_validation(fixture_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_and_validate_aggregator(fixture_path)
