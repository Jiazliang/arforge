# Validation Profiles

Validation profiles let you customize semantic validation without modifying ARForge core rules.

Use a profile when you need:

- project-specific naming conventions
- project-specific restrictions or policies
- rule enable/disable control
- future-ready configuration points for rule severity or similar options

Core validation remains intact. Profiles only change which rules are loaded and which of those loaded rules are active for a given run.

## CLI usage

```bash
python -m arforge.cli validate autosar.project.yaml --profile validation_profiles/profile.yaml
```

Behavior:

- without `--profile`: ARForge runs the built-in `core` rules only
- with `--profile`: ARForge loads the profile, imports extension modules, builds one deterministic active ruleset, and runs that ruleset through the same validation runner

## Profile format

```yaml
profile:
  name: "MyProjectRules"
  mode: "core+extensions"

rules:
  enable:
    - "MY-001"
    - "MY-002"
  disable:
    - "CORE-014"

extensions:
  - module: "project_validation_rules"
    rules:
      - "rule_check_swc_naming"
      - "rule_forbid_sync_calls"
```

Fields:

- `profile.name`: human-readable profile name shown in the resolved ruleset label
- `profile.mode`: `core+extensions` or `extensions-only`
- `rules.enable`: rule family codes to keep active in the selected mode
- `rules.disable`: rule family codes to remove from the active set
- `extensions`: explicit list of Python modules and the rule functions to load from each module

Mode behavior:

- `core+extensions`: start from built-in core rules, add extension rules, then apply `enable` and `disable`
- `extensions-only`: start from extension rules only, ignore built-in core rules completely, then apply `enable` and `disable`

Notes:

- `enable` and `disable` act on rule family codes such as `CORE-041` or `MY-001`
- finding detail codes may still use suffixes such as `CORE-041-SR-READ-UNCONNECTED`
- invalid config is not ignored; ARForge fails with a clear error

## How extension modules are loaded

Each `extensions[].module` value is imported as a normal Python module path.

ARForge temporarily adds the directory containing `profile.yaml` to `sys.path` before importing, so a module placed next to the profile can be loaded with a simple module name such as `project_validation_rules`.

Import failures and missing rule functions are fatal:

- missing module: validation fails with a clear import error
- missing function: validation fails with a clear lookup error
- missing rule metadata: validation fails with a clear extension API error

## Writing a custom rule

Extension rules are plain Python functions decorated with `@validation_rule(...)`.

```python
from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="MY-001",
    name="SwcPascalCaseNames",
    description="Checks that SWC type names start with an uppercase letter.",
    tags=("project", "naming", "swc"),
    default_severity="warning",
)
def rule_check_swc_naming(context):
    findings = []
    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        if not swc.name or not swc.name[0].isupper():
            findings.append(
                Finding(
                    code="MY-001-SWC-NAME",
                    severity="warning",
                    message=f"SWC '{swc.name}' must start with an uppercase letter.",
                    location=f"swc:{swc.name}",
                )
            )
    return findings
```

Rule contract:

- function signature: `def rule_name(context):`
- input: one `ValidationContext`
- output: `list[Finding]`
- metadata: supplied by `@validation_rule(...)`

Decorator metadata:

- `code`: stable rule family code such as `MY-001`
- `name`: short human-readable rule name
- `description`: one-sentence rule description
- `tags`: optional category/domain tags
- `default_severity`: default severity for findings created by the rule when you want to mirror the rule-level default in your own logic

The `code` must be unique across the active ruleset. If an extension rule reuses a built-in `CORE-XXX` code or collides with another extension rule, validation fails clearly.

## Validation context API

Extension rules receive the same `ValidationContext` used by core rules. This is the public extension API surface.

Common attributes:

- `context.project`: full typed project model
- `context.swc_by_name`: `dict[str, Swc]`
- `context.iface_by_name`: `dict[str, Interface]`
- `context.instance_by_name`: `dict[str, ComponentPrototype]`
- `context.subcomposition_by_name`: `dict[str, SubcompositionType]`
- `context.ports_by_swc`: ports indexed by SWC name and port name
- `context.runnable_by_swc`: runnables indexed by SWC name and runnable name
- `context.instances_by_swc_name`: instantiated components grouped by type
- `context.instantiated_port_connections`: connectivity indexed by `(instance_name, port_name)`
- `context.runnable_port_usage_by_swc_port`: runnable access grouped by `(swc_name, port_name)`
- `context.sr_timing_communications`: precomputed SR timing relationships

Helpful methods:

- `context.find_swc_port(swc_name, port_name)`
- `context.find_instance_swc(instance_name)`
- `context.find_subcomposition(name)`
- `context.find_instance_port_connectivity(instance_name, port_name)`
- `context.find_swc_port_usage(swc_name, port_name)`
- `context.iter_declared_port_usage(swc_name)`
- `context.iter_mode_switch_requires_port_analysis(swc_name)`

Guidelines for extension authors:

- sort your own iteration explicitly for deterministic output
- return stable finding codes and messages
- keep rule functions independent; do not call other rules
- prefer `context` indexes over repeated full-model scans when available

## Findings

Return normal `Finding` objects from `arforge.semantic_validation`.

```python
Finding(
    code="MY-002-INSTANCE-SUFFIX",
    severity="warning",
    message="System instance 'DiagManager' should end with a numeric suffix.",
    location="system.component:DiagManager",
)
```

Recommended pattern:

- use the rule family code for enable/disable, for example `MY-002`
- use suffixed finding codes for specific conditions, for example `MY-002-INSTANCE-SUFFIX`

## Registration

You do not register extension rules in any core ARForge file.

Registration happens only through the profile:

1. write a Python module with one or more decorated validation functions
2. list the module path in `extensions`
3. list the function names in `extensions[].rules`
4. run `arforge validate ... --profile validation_profiles/profile.yaml`

## Working examples

ARForge includes a complete example profile and extension module:

- profile: [examples/validation_profiles/profile.yaml](../examples/validation_profiles/profile.yaml)
- rules: [examples/validation_profiles/project_validation_rules.py](../examples/validation_profiles/project_validation_rules.py)

Example rules included there:

- naming rule: SWC names should start with an uppercase letter
- structural rule: top-level instance names should end with `_<number>`
