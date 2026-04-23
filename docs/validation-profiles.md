# Validation Profiles

Validation profiles let you customize semantic validation without modifying ARForge core rules.

Use a profile when you need:

- project-specific extension rules
- rule enable/disable control
- a run that combines built-in rules with project rules
- an extensions-only run for policy checks or onboarding experiments

If you want to learn how to write the rule functions themselves, start with [Custom Validation Rules](./custom-validation-rules.md). This page focuses on how profiles assemble and load those rules.

## Extension model

ARForge has two validation layers:

- built-in core semantic rules (`CORE-*`)
- optional project-specific extension rules loaded by profile

Profile modes:

- `core+extensions`: run built-in core rules plus extension rules
- `extensions-only`: run only the extension rules listed in the profile

After that active set is assembled, profile `rules.enable` and `rules.disable` are applied by rule family code.

## CLI usage

```bash
python -m arforge.cli validate autosar.project.yaml --profile validation_profiles/naming.yaml
```

Behavior:

- without `--profile`: ARForge runs the built-in `core` ruleset
- with `--profile`: ARForge loads the profile, imports the listed extension modules, resolves one deterministic active ruleset, and runs that ruleset through the normal validation runner

## Profile format

```yaml
profile:
  name: "MyProjectRules"
  mode: "core+extensions"

rules:
  disable:
    - "CORE-047"

extensions:
  - module: "rules.naming_rules"
    rules:
      - "rule_check_swc_names"
      - "rule_check_port_prefixes"
```

Fields:

- `profile.name`: human-readable profile name shown in the resolved ruleset label
- `profile.mode`: `core+extensions` or `extensions-only`
- `rules.enable`: optional rule family codes to keep active
- `rules.disable`: optional rule family codes to remove from the active set
- `extensions`: Python modules plus explicit rule function names to load from each module

Notes:

- `enable` and `disable` work on rule family codes such as `CORE-041` or `PRJ-201`
- detailed findings may still use suffixed codes such as `PRJ-201-PORT-UNCONNECTED`
- invalid profile structure is not ignored; ARForge fails with a clear error

## How extension modules are loaded

Each `extensions[].module` value is imported as a normal Python module path.

ARForge temporarily adds the directory containing the profile YAML to `sys.path` before importing. That means a profile can load:

- a module next to the profile, such as `custom_rules`
- a small package path under the profile directory, such as `rules.naming_rules`

Import failures and missing rule functions are fatal:

- missing module: validation fails with a clear import error
- missing function: validation fails with a clear lookup error
- missing `@validation_rule(...)` metadata: validation fails with a clear extension API error
- duplicate rule family code in the active ruleset: validation fails clearly

## Sample profiles in this repository

ARForge includes working sample profiles in [examples/validation_profiles/](../examples/validation_profiles/):

- [naming.yaml](../examples/validation_profiles/naming.yaml)
  Uses `extensions-only` mode to run just naming-policy rules.
- [strict_hygiene.yaml](../examples/validation_profiles/strict_hygiene.yaml)
  Uses `core+extensions` mode and replaces a few generic core hygiene warnings with project-specific stricter checks.
- [rules/naming_rules.py](../examples/validation_profiles/rules/naming_rules.py)
  Shows naming-convention rule functions.
- [rules/hygiene_rules.py](../examples/validation_profiles/rules/hygiene_rules.py)
  Shows structural and connectivity policy rules.

Quick-start commands:

```bash
python -m arforge.cli validate examples/autosar.project.yaml --profile examples/validation_profiles/naming.yaml
python -m arforge.cli validate examples/autosar.project.yaml --profile examples/validation_profiles/strict_hygiene.yaml
python -m arforge.cli validate examples/validation_profiles/fixtures/profile_demo.project.yaml --profile examples/validation_profiles/naming.yaml
```

## Writing the rule functions

Validation profiles only wire rules in. The rule authoring contract lives here:

- [Custom Validation Rules](./custom-validation-rules.md)

That page covers:

- rule function signature
- `@validation_rule(...)` metadata
- available `ValidationContext` data and helper objects
- how to create and return `Finding` objects
- copyable naming and structural-hygiene examples
