# Sample Validation Profiles

This directory contains small, copyable validation profile examples for ARForge.

For the full authoring guide, see:

- `docs/validation-profiles.md` for profile YAML structure and loading
- `docs/custom-validation-rules.md` for rule function authoring, available context, and finding creation

Profiles included:

- `naming.yaml`
  Runs only project-specific naming rules (`extensions-only` mode).
  Useful when a team wants a lightweight conventions check without the full core ruleset.
- `strict_hygiene.yaml`
  Runs core validation plus stricter project policy rules (`core+extensions` mode).
  It also disables a few generic warning-style core hygiene rules and replaces them with project-specific checks.

Rule modules live in `rules/`:

- `rules/naming_rules.py`
- `rules/hygiene_rules.py`

Fixture project:

- `fixtures/profile_demo.project.yaml`

This fixture is intentionally non-conforming so the sample profiles produce visible findings in tests and local experimentation.

Example commands:

```bash
python -m arforge.cli validate examples/autosar.project.yaml --profile examples/validation_profiles/naming.yaml
python -m arforge.cli validate examples/autosar.project.yaml --profile examples/validation_profiles/strict_hygiene.yaml
python -m arforge.cli validate examples/validation_profiles/fixtures/profile_demo.project.yaml --profile examples/validation_profiles/naming.yaml
```
