# Architecture

This page describes the internal design of ARForge. It is intended for contributors and for engineers who want to understand how the tool works under the hood.

## Processing pipeline

ARForge uses a common load-and-model-build foundation, but not every command takes the same path after that.

Validation and validation-gated generators follow this pipeline:

```
project.yaml
     ->
load_aggregator_with_report()
     -> glob expansion + YAML parsing + JSON Schema validation
merged raw input
     ->
model build
     -> typed internal model
semantic validation
     -> ValidationReport with sorted findings
rendered output generation  (only if no error findings)
     ->
output files
```

The `report` command is intentionally different: it loads the project, builds the typed model, and then renders a descriptive architecture summary without requiring semantic validation success. This keeps `report` complementary to `validate` rather than making it another validation surface.

Each stage has a clear responsibility and a hard boundary. The loader does not reason about semantics. The semantic validator does not render output. The rendering backends do not re-validate.

## Module responsibilities

**`arforge/cli.py`**
User-facing commands and console output. Formats findings, prints summaries, handles exit codes. Does not contain business logic.

**`arforge/validate.py`**
Project loading. Resolves the manifest path, expands glob patterns, parses YAML files, validates each file against its JSON Schema, and merges the parsed data into a unified raw input structure. Produces a load report that captures schema errors before semantic validation begins.

**`arforge/model.py`**
Internal data model. Converts the merged raw input into a typed internal representation. The model is what semantic validation and the rendering backends operate on - not raw dicts.

**`arforge/semantic_validation.py`**
Validation runner, finding model, and validation context. Defines `Finding`, `ValidationReport`, `ValidationCase`, and the indexes used by individual cases (port lookup by name, interface lookup by type, etc.). Runs cases in sorted order. Sorts findings deterministically.

**`arforge/validation/cases/`**
Domain-organized semantic validation case implementations. Each module covers a specific area of the AUTOSAR model:

| Module | Domain |
|---|---|
| `common.py` | Global uniqueness |
| `interfaces.py` | Interface semantics |
| `types.py` | Base type metadata, application constraints |
| `modes.py` | Mode declaration group structure, initial mode, unused groups |
| `swc.py` | SWC structure, port references, runnable access, ComSpec, events |
| `system.py` | System instance types, connection semantics |
| `connectivity.py` | SR/CS/MS port connectivity, multiplicity analysis, usage analysis, declared port usage |
| `timing.py` | SR timing mismatch analysis |

**`arforge/validation_cases.py`**
Compatibility export surface. Re-exports the domain case modules for backward-compatible imports.

**`arforge/validation_registry.py`**
Ruleset registry. Maps ruleset names to lists of `ValidationCase` instances. Currently contains one ruleset: `core`. The registry is the extension point for adding OEM-specific or project-specific rulesets.

**`arforge/exporter.py`**
Export orchestration. Builds the rendering context from the validated model, drives Jinja2 template rendering, and writes output files. Handles split and monolithic layout. Enforces deterministic output ordering.

**`arforge/reporting.py`**
Architecture report orchestration. Builds a normalized report context from the loaded model, summarizes counts and architecture facts, and renders Markdown through Jinja2 templates. Reuses stable model and validation-context analysis helpers where appropriate, but does not act as a validation command.

**`arforge/codegen.py`**
Code generation orchestration. Builds a normalized per-SWC code-generation model from the validated project, resolves straightforward type mappings, renders language-specific Jinja2 templates, and writes deterministic per-SWC code artifacts.

**`arforge/scaffold.py`**
Project scaffold generation for `arforge init`. Writes the directory structure and example files.

**`templates/`**
Jinja2 templates for all rendered outputs. The current tree groups templates by output kind, including ARXML export templates under `templates/arxml/`, report templates under `templates/reports/`, diagram templates, and code-generation templates under `templates/code/c/`.

**`schemas/*.json`**
JSON Schema files for each input category. Used by the loader for structural validation before semantic validation runs.

**`.vscode/`**
VS Code configuration. `settings.json` maps YAML schemas to file patterns for inline autocomplete and diagnostics. `tasks.json` defines platform-aware task runners for init, validate, report, export, diagram generation, code generation, and pytest - with separate `windows`, `linux`, and `osx` command entries resolving the correct `.venv` Python executable on each platform.

## Validation architecture

Each semantic rule is a `ValidationCase` subclass with:

- a stable `case_id` (`CORE-XXX`)
- a `name` and `description`
- a `run(ctx)` method that returns a list of `Finding` objects

Cases are independent. They do not call each other. The runner executes them in sorted order by code, making execution order deterministic regardless of registration order.

The `ValidationContext` built by the runner contains pre-built indexes - interface lookup by name, port lookup by SWC, instance lookup by name - so individual cases do not need to traverse the full model for every check.

Findings carry a `code`, `message`, and `severity`. The `code` field uses a hierarchical naming scheme: the group prefix (`CORE-022`) identifies the rule family, the suffix (`-READ-UNKNOWN-PORT`) identifies the specific condition within that rule. This makes findings greppable and stable across versions.

## Rendering architecture

The rendering backends receive the project model and build rendering contexts - plain data structures that the Jinja2 templates can consume without any further model traversal.

Output ordering is enforced explicitly in the rendering context, not left to dict iteration order. This guarantees that repeated generation runs on the same model produce byte-identical artifacts for a given backend.

Validation-gated backends such as ARXML export and code generation operate on semantically validated models. The architecture report backend operates on a successfully loaded model and intentionally keeps validation findings out of the primary report output.

The `--templates` CLI option allows substituting the built-in template directory with a custom one. This is the designed extension point for OEM-specific output profiles - custom templates can add vendor extensions, change package structure, or enforce naming conventions without modifying ARForge itself.

## Adding a validation rule

1. Choose the appropriate domain module under `arforge/validation/cases/` or create a new one for a new domain.
2. Add a new `ValidationCase` subclass with a stable `CORE-XXX` code that does not collide with existing codes.
3. Register it in the `core` ruleset via `arforge/validation_registry.py`.
4. Add an invalid fixture under `examples/invalid/` that triggers the new finding. Follow the naming convention in `examples/invalid/README.md`.
5. Add a test case in `tests/test_examples.py` that asserts the expected finding code.

The invalid fixture corpus serves as both documentation and regression protection. Every rule must have at least one fixture that proves it fires.
