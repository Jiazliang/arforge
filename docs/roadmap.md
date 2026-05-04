# Roadmap

This roadmap describes what ARForge currently supports and where it is going. It communicates direction, not release commitments.

---

## Current capabilities

ARForge currently provides a practical SWC design and generation pipeline for an AUTOSAR Classic 4.2-aligned subset, running on Linux and Windows with VS Code integration.

### CLI and tooling

- `arforge init` - project scaffold generation with working example
- `arforge validate` - schema + semantic validation with verbose modes (`-v`, `-vv`)
- `arforge validate --profile <profile.yaml>` - profile-aware validation with project-specific extension rules and rule filtering
- `arforge export` - validated ARXML export, monolithic or split by SWC
- external package layout support via `autosar.packageLayoutRef`
- `arforge report` - deterministic Markdown architecture summary for reviews, CI artifacts, and handoffs
- `arforge diff` - deterministic Markdown structural diff between two model versions for PR reviews and architecture change discussions
- `arforge generate diagram` - PlantUML architecture and behavior diagram generation
- `arforge generate code` - template-driven C starter skeleton generation
- VS Code integration - YAML schema autocomplete, inline diagnostics, and task runner
- pytest suite with valid and invalid fixtures covering all supported constructs

### Data types

- base types with bit length, signedness, native declaration, and normalized export category
- implementation data types - scalar, array, struct with nested struct validation and cycle detection
- application data types with physical constraints, unit references, and compu method references
- units and compu methods - `linear` and `textTable` (enumeration) categories
- constraint validation against base type ranges

### Interfaces

- sender-receiver interfaces with data elements
- client-server interfaces with operations, in/out/inout arguments, return types, possible errors
- mode-switch interfaces with `ModeDeclarationGroup` references
- `ModeDeclarationGroup` definitions as first-class model artifacts

### SWC types

- SWC categories: `application`, `service`, `complexDeviceDriver`
- provides and requires ports for all three interface kinds
- ComSpec - SR implicit/explicit/queued with queue length validation and optional receiver init values; CS synchronous/asynchronous with timeout configuration
- runnable definitions with all standard AUTOSAR event triggers: `TimingEvent`, `InitEvent`, `OperationInvokedEvent`, `DataReceiveEvent`, `ModeSwitchEvent`
- runnable access definitions: `reads`, `writes`, `calls`, `raisesErrors` - all validated against port direction and interface kind
- generated C runnable declarations and stubs with AUTOSAR-style `Rte_Read_*`, `Rte_Write_*`, and `Rte_Call_*` placeholders

### System composition

- component prototypes with SWC and reusable subcomposition type references
- port-level assembly connectors for SR, CS, and mode-switch flows
- reusable subcomposition types with boundary ports and delegation connectors
- deterministic connector export ordering
- packages as export-time namespaces only; package layout does not alter component wiring or behavior

### Validation

- two-stage validation: JSON Schema + semantic
- stable `CORE-*` finding codes organized in domain modules
- three severity levels: `error`, `warning`, `info`
- package-layout validation for defaults, allowed packages, explicit package assignments, and duplicate resolved ARXML paths
- connectivity validation for SR, CS, and mode-switch ports
- port usage analysis - warnings for connected but unused ports
- sender-receiver multiplicity analysis (`CORE-045`) - warns when multiple providers feed the same SR requires port
- declared port usage analysis (`CORE-047`) - warns when SWC ports are never accessed by any runnable, independent of system connectors
- mode-switch usage analysis (`CORE-048`) - warns when connected mode-switch ports are never used by runnable `modeSwitchEvents`
- unused mode declaration group detection (`CORE-014`)
- SR timing mismatch analysis - warns when consumer runs faster or slower than producer
- validation profiles and extension rules - profile YAML with `core+extensions` / `extensions-only`, dynamic rule loading, and rule enable/disable filtering
- deterministic finding order - stable CI output across runs

### Rendering

- Jinja2-based ARXML templates
- Jinja2-based Markdown report templates
- Jinja2-based Markdown diff templates
- Jinja2-based diagram templates
- Jinja2-based C code-generation templates
- deterministic output ordering - repeated exports and generations produce identical output
- monolithic and split-by-SWC export layouts
- centralized ARXML path resolution for component, interface, datatype, mode, and system references
- custom template directory support (`--templates`) for OEM-specific profiles

---

## Near-term

**Authoring experience polish**
The baseline authoring experience is already in place: JSON Schema metadata drives editor autocomplete and inline diagnostics, the scaffold includes a readable working example, and common loading/validation failures already surface explicit messages. Near-term work here is incremental polish rather than first-time delivery - refining schema hints further, improving wording for common failure modes, and continuing to simplify the starter project materials.

---

## Medium-term

**AUTOSAR 4.3 / 4.4 support**
Versioned template and schema architecture (`--schema-version` flag) to support multiple AUTOSAR Classic schema targets. The internal model and validation layer are designed to be version-agnostic; the version-specific work is in the templates and schema files.

**Nested composition support**
Reusable subcomposition types are already supported at one level. The remaining planned work is deeper nesting: compositions within compositions within compositions, beyond the current single reusable-subcomposition layer.

**VS Code extension**
A dedicated VS Code extension providing YAML schema autocomplete, inline validation diagnostics, and model preview for ARForge projects. The JSON schemas in `schemas/` are the foundation - the extension makes them accessible without manual schema configuration in any project.

---

## Longer-term

**ARXML import (partial, best-effort)**
Import of interface definitions and data type packages from supplier-provided ARXML into ARForge YAML. Scoped to the shared type and interface layer - not full round-trip import of compositions or OEM-extended ARXMLs. The goal is to eliminate the manual retyping of supplier interfaces, not to solve full ARXML round-trip.

**Adaptive Platform (AP) support**
Experimental support for selected AUTOSAR Adaptive Platform constructs. The Classic Platform remains the primary focus; AP support would be additive and clearly scoped.

---

## What is deliberately out of scope

ARForge covers the SWC design layer. The following are intentionally not modeled:

- RTE contract header generation - tightly coupled to BSW and RTE vendor configuration, outside the SWC design boundary
- OS task and alarm configuration
- BSW module configuration (COM, DCM, NvM, etc.)
- Memory mapping and linker configuration
- ECU extract generation

Staying within this scope keeps ARForge's outputs trustworthy and its maintenance tractable.
