# Test Suite Layout

The test suite is grouped by ARForge capability so contributors can add coverage where the behavior lives.

## Folders

- `cli/`: command-line behavior for `validate`, `export`, `generate`, and `report`.
- `schema/`: JSON Schema validation and schema-first rejection cases.
- `model/`: parsing and model IR loading checks.
- `validation/core/`: built-in semantic validation rules and validation regressions.
- `validation/profiles/`: validation profile loading, extension rules, and profile-specific CLI checks.
- `export/monolithic/`: single-file ARXML export tests.
- `export/split/`: split-by-SWC ARXML export tests.
- `generate/code/`: C skeleton generation tests.
- `generate/diagram/`: diagram generation and view-model tests.
- `scaffold/`: `arforge init` scaffold tests.
- `report/`: project report rendering and file output tests.
- `examples/`: checks tied directly to shipped example projects and the invalid example corpus.

## Where To Add Tests

- Put a new test beside the feature it exercises, not beside the implementation history.
- Use `test_<feature>.py` file names that describe the behavior under test.
- Keep reusable helpers in private support modules such as `tests/_shared.py`; avoid duplicating fixture-path logic across files.
- When a test depends on example projects under `examples/`, keep fixture paths deterministic and prefer explicit sorting.

## Contributor Notes

- Preserve behavior when reorganizing tests: move assertions, do not rewrite semantics unless the task requires it.
- Keep tests isolated from filesystem order and from each other.
- Run `pytest -q` after changes to confirm collection and behavior stay stable.

## Adding A New Feature Test

When a new ARForge feature is added, use this quick checklist:

1. Identify the main user-facing area the feature belongs to.
2. Add the test under the matching folder, such as `schema/`, `model/`, `validation/core/`, `validation/profiles/`, `export/`, `generate/`, `cli/`, `report/`, `scaffold/`, or `examples/`.
3. Create or extend a file named for the feature, using `test_<feature>.py`.
4. Keep the test focused on one capability. If the feature spans multiple areas, add separate tests in each relevant folder instead of one mixed file.
5. Reuse shared helpers for repo paths, XML fragments, and common fixture logic instead of duplicating them.
6. If the feature needs example or invalid fixtures, add deterministic fixtures with clear names and update paths explicitly.
7. Run `pytest -q` and confirm the new tests pass without changing unrelated behavior.

Rule of thumb: ask "Where would a contributor look for tests of this feature first?" and place the test there.
