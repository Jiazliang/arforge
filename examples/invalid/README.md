# Invalid Fixtures

This directory contains intentionally invalid ARForge models.

They are kept under `examples/invalid/` because the validation test corpus still loads them from here, but they are not meant to be starter examples for users.

Use this folder when you are:

- working on schema or semantic validation behavior
- adding a new invalid fixture for a finding code
- running targeted validation checks from the CLI

Ignore this folder if you are learning ARForge or looking for a clean project to copy.
Start with [`examples/minimal/`](../minimal/) instead, and use [`examples/features/`](../features/) for focused sample material.

Fixture guidance:

- top-level `project_*.yaml` files are usually small aggregator manifests that trigger one validation scenario
- sibling folders such as `interfaces/`, `swcs/`, `types/`, and `support/` provide shared helper inputs
- fixture names should make the failing scenario obvious and deterministic
