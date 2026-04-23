# Custom Validation Rules

ARForge supports project-specific semantic validation through validation profiles. You do not need to modify `arforge/validation/cases/` or any other core file to add your own policy layer.

Use custom rules when you want to enforce conventions such as:

- naming patterns
- project-specific modeling restrictions
- stricter hygiene checks than the built-in `CORE-*` rules

The extension model is intentionally simple:

- ARForge always has built-in core semantic rules
- a validation profile can run `core+extensions` or `extensions-only`
- extension rules live in normal Python modules outside ARForge core
- the profile YAML tells ARForge which modules to import and which rule functions to run

For profile structure details, see [Validation Profiles](./validation-profiles.md). This page focuses on authoring the rules themselves.

## Rule authoring contract

A custom rule is:

- a Python function
- decorated with `@validation_rule(...)`
- called with one `ValidationContext`
- expected to return `list[Finding]`

Minimal complete example:

```python
from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="PRJ-101",
    name="PortPrefixConvention",
    description="Checks that provides ports start with Pp_ and requires ports start with Rp_.",
    tags=("project", "naming", "ports"),
    default_severity="warning",
)
def rule_check_port_prefixes(context):
    findings: list[Finding] = []

    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        for port in sorted(swc.ports, key=lambda item: item.name):
            expected_prefix = "Pp_" if port.direction == "provides" else "Rp_"
            if port.name.startswith(expected_prefix):
                continue
            findings.append(
                Finding(
                    code="PRJ-102-PORT-PREFIX",
                    severity="warning",
                    message=f"Port '{swc.name}.{port.name}' should start with '{expected_prefix}'.",
                    location=f"swc:{swc.name}.port:{port.name}",
                )
            )

    return findings
```

This matches the same extension mechanism used by the sample modules in [examples/validation_profiles/rules/](../examples/validation_profiles/rules/).

## Metadata declared by `@validation_rule`

The decorator stores the metadata ARForge needs to wrap your function into a normal validation case:

- `code`: stable rule family code such as `PRJ-101`
- `name`: short human-readable name shown in verbose case output
- `description`: one-sentence summary of what the rule checks
- `tags`: optional tuple of category labels
- `default_severity`: default severity for the case; useful when your findings follow one severity consistently

Important behavior:

- the decorator metadata is required
- the `code` must be unique in the active ruleset
- if your profile loads a rule function without decorator metadata, validation fails clearly
- if two active rules use the same `code`, validation fails clearly

Rule-family code vs finding code:

- the decorator `code` is the rule family code used by profile `enable` and `disable`
- individual findings can use the family code directly, or a suffixed detail code such as `PRJ-102-PORT-PREFIX`

## What `context` contains

Custom rules receive `arforge.semantic_validation.ValidationContext`. This is the same typed analysis object used by ARForge core rules.

### Main project model

The top-level entry point is `context.project`, which is an `arforge.model.Project`.

Common objects reachable from it:

- `context.project.system`: top-level `System`
- `context.project.system.composition.components`: top-level `ComponentPrototype` instances
- `context.project.system.composition.connectors`: top-level `Connection` objects
- `context.project.swcs`: list of `Swc` component types
- `context.project.interfaces`: list of `Interface`
- `context.project.subcompositions`: list of `SubcompositionType`
- `context.project.modeDeclarationGroups`: list of `ModeDeclarationGroup`
- `context.project.baseTypes`, `implementationDataTypes`, `applicationDataTypes`
- `context.project.units`, `context.project.compuMethods`

User-facing mapping to model classes:

- SWC type: `arforge.model.Swc`
- port: `arforge.model.Port`
- runnable: `arforge.model.Runnable`
- interface: `arforge.model.Interface`
- top-level instance: `arforge.model.ComponentPrototype`
- top-level connector: `arforge.model.Connection`
- subcomposition type: `arforge.model.SubcompositionType`

### Indexed lookups and precomputed analysis

`ValidationContext` also builds deterministic lookup tables so your rule does not need to rescan the whole model every time.

Useful indexes:

- `context.swc_by_name`: `dict[str, Swc]`
- `context.iface_by_name`: `dict[str, Interface]`
- `context.subcomposition_by_name`: `dict[str, SubcompositionType]`
- `context.instance_by_name`: `dict[str, ComponentPrototype]`
- `context.ports_by_swc`: `dict[str, dict[str, Port]]`
- `context.runnable_by_swc`: `dict[str, dict[str, Runnable]]`
- `context.instances_by_swc_name`: `dict[str, list[ComponentPrototype]]`
- `context.base_type_by_name`
- `context.implementation_type_by_name`
- `context.application_type_by_name`
- `context.datatype_by_name`
- `context.mode_declaration_group_by_name`
- `context.unit_by_name`
- `context.compu_method_by_name`

Connectivity and usage indexes:

- `context.instantiated_port_connections`: top-level instantiated port connectivity keyed by `(instance_name, port_name)`
- `context.runnable_port_usage_by_swc_port`: runnable access keyed by `(swc_name, port_name)`
- `context.sr_timing_communications`: precomputed sender-receiver cyclic timing relationships

These are especially useful when your rule wants to inspect:

- whether a top-level instance port is wired
- whether a declared port is used by any runnable
- whether a cyclic SR producer/consumer pair has a timing relationship

### Helper methods

Helpful context helpers exposed intentionally for rule authors:

- `context.find_swc_port(swc_name, port_name) -> Port | None`
- `context.find_instance_swc(instance_name) -> Swc | None`
- `context.find_top_level_component_type_kind(type_name) -> str | None`
- `context.find_subcomposition(name) -> SubcompositionType | None`
- `context.find_instance_port_connectivity(instance_name, port_name) -> InstancePortConnectivity | None`
- `context.find_swc_port_usage(swc_name, port_name) -> SwcPortUsage`
- `context.iter_declared_port_usage(swc_name) -> tuple[DeclaredPortUsage, ...]`
- `context.iter_mode_switch_requires_port_analysis(swc_name) -> tuple[ModeSwitchRequiresPortAnalysis, ...]`

These helper return types are also defined in `arforge.semantic_validation`:

- `InstancePortConnectivity`
- `SwcPortUsage`
- `DeclaredPortUsage`
- `ModeSwitchRequiresPortAnalysis`
- `SrTimingCommunication`

### Practical interpretation of the available data

What you can inspect cleanly today:

- project/system model through `context.project`
- SWCs, ports, runnables, events, and top-level component instances
- interfaces and datatype definitions
- top-level system connectors and instantiated top-level port connectivity
- subcomposition type definitions in `context.project.subcompositions`

Current limitation to keep in mind:

- the convenience connectivity indexes are built for top-level instantiated atomic SWC ports
- ARForge does not currently expose a separate public helper layer for subcomposition-internal instantiated connectivity
- if you need subcomposition structure, inspect `context.project.subcompositions` directly rather than assuming a helper exists

## Emitting findings

Return `Finding` objects from `arforge.semantic_validation`:

```python
Finding(
    code="PRJ-202-CONNECTED-PORT-UNUSED",
    severity="warning",
    message="Connected port 'SpeedMonitor_0.Rp_VehicleSpeed' is wired but no runnable reads or dataReceiveEvents use it.",
    location="system.component:SpeedMonitor_0.port:Rp_VehicleSpeed",
)
```

`Finding` fields:

- `code`: stable machine-readable identifier
- `severity`: `error`, `warning`, or `info`
- `message`: clear human-readable explanation
- `location`: optional stable location string for CLI output

Recommended conventions:

- choose one stable family code per rule, for example `PRJ-202`
- use suffixed finding codes for concrete situations, for example `PRJ-202-PORT-UNUSED`
- keep messages specific and actionable
- use stable naming in `location` strings, for example `swc:<name>.port:<name>` or `system.component:<name>.port:<name>`

Determinism matters:

- sort anything you iterate, even if source YAML order looks stable
- do not include random values, timestamps, or nondeterministic object reprs in messages
- keep code/message/location generation stable so CI diffs stay clean

## Example A: naming convention rule

This example is directly aligned with the sample profile in [examples/validation_profiles/naming.yaml](../examples/validation_profiles/naming.yaml).

```python
from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="PRJ-102",
    name="PortPrefixConvention",
    description="Checks that provides ports start with Pp_ and requires ports start with Rp_.",
    tags=("project", "naming", "ports"),
    default_severity="warning",
)
def rule_check_port_prefixes(context):
    findings: list[Finding] = []

    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        for port in sorted(swc.ports, key=lambda item: item.name):
            expected_prefix = "Pp_" if port.direction == "provides" else "Rp_"
            if port.name.startswith(expected_prefix):
                continue
            findings.append(
                Finding(
                    code="PRJ-102-PORT-PREFIX",
                    severity="warning",
                    message=f"Port '{swc.name}.{port.name}' should start with '{expected_prefix}'.",
                    location=f"swc:{swc.name}.port:{port.name}",
                )
            )

    return findings
```

Why this is a good first custom rule:

- it uses only `context.project.swcs`
- it shows deterministic iteration
- it emits one finding per offending port
- it does not depend on deeper connectivity helpers

## Example B: structural hygiene rule

This example shows a small project-policy check using the typed model directly.

```python
from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="PRJ-210",
    name="SwcMustDeclarePortsAndRunnables",
    description="Flags SWCs that declare no ports or no runnables.",
    tags=("project", "structure", "hygiene"),
    default_severity="warning",
)
def rule_require_swc_structure(context):
    findings: list[Finding] = []

    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        if not swc.ports:
            findings.append(
                Finding(
                    code="PRJ-210-NO-PORTS",
                    severity="warning",
                    message=f"SWC '{swc.name}' declares no ports.",
                    location=f"swc:{swc.name}",
                )
            )
        if not swc.runnables:
            findings.append(
                Finding(
                    code="PRJ-210-NO-RUNNABLES",
                    severity="warning",
                    message=f"SWC '{swc.name}' declares no runnables.",
                    location=f"swc:{swc.name}",
                )
            )

    return findings
```

Variation using the richer context helpers:

- use `context.iter_declared_port_usage(swc.name)` to detect declared-but-unused ports
- use `context.find_instance_port_connectivity(instance.name, port.name)` to check whether top-level ports are wired
- use `context.sr_timing_communications` if your project policy depends on cyclic SR timing

The sample file [examples/validation_profiles/rules/hygiene_rules.py](../examples/validation_profiles/rules/hygiene_rules.py) shows this style with real working rules.

## Wiring rules through a profile

Example layout:

```text
my_project/
  validation/
    profile.yaml
    custom_rules.py
```

Example `custom_rules.py`:

```python
from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="PRJ-210",
    name="SwcMustDeclarePortsAndRunnables",
    description="Flags SWCs that declare no ports or no runnables.",
    default_severity="warning",
)
def rule_require_swc_structure(context):
    findings: list[Finding] = []
    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        if not swc.runnables:
            findings.append(
                Finding(
                    code="PRJ-210-NO-RUNNABLES",
                    severity="warning",
                    message=f"SWC '{swc.name}' declares no runnables.",
                    location=f"swc:{swc.name}",
                )
            )
    return findings
```

Matching `profile.yaml`:

```yaml
profile:
  name: "MyProjectRules"
  mode: "core+extensions"

extensions:
  - module: "custom_rules"
    rules:
      - "rule_require_swc_structure"
```

How loading works:

- ARForge temporarily adds the directory containing `profile.yaml` to `sys.path`
- the `module` field is imported as a normal Python module path
- ARForge then loads the named functions from that module

That means these all work, as long as they are importable relative to the profile directory:

- `module: "custom_rules"`
- `module: "rules.naming_rules"`

CLI example:

```bash
python -m arforge.cli validate examples/autosar.project.yaml --profile examples/validation_profiles/strict_hygiene.yaml
```

This command uses the same extension mechanism your own project profile would use.

## Best practices

- Keep rules deterministic. Always sort SWCs, ports, interfaces, instances, and connectors before iterating.
- Use stable rule codes. Treat the decorator `code` as a public contract once the rule is adopted in a project.
- Prefer documented `ValidationContext` attributes and helpers over reaching into unrelated internal modules.
- Keep each rule focused. One rule should check one policy family, not an entire project style guide.
- Write messages for engineers, not for the implementation. Say what is wrong and what naming or structure is expected.
- Reuse `context` indexes when possible instead of repeatedly scanning the entire model.
- Add tests for your custom rules, especially if they become part of CI policy for a project.

## Working reference material in this repository

If you want copyable starting points, use these files:

- [docs/validation-profiles.md](./validation-profiles.md)
- [examples/validation_profiles/naming.yaml](../examples/validation_profiles/naming.yaml)
- [examples/validation_profiles/strict_hygiene.yaml](../examples/validation_profiles/strict_hygiene.yaml)
- [examples/validation_profiles/rules/naming_rules.py](../examples/validation_profiles/rules/naming_rules.py)
- [examples/validation_profiles/rules/hygiene_rules.py](../examples/validation_profiles/rules/hygiene_rules.py)

Together, they show:

- profile YAML shape
- module import and rule loading
- rule metadata declaration
- context usage
- finding creation
- extensions-only versus core-plus-extensions execution
