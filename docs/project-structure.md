# Project Structure

An ARForge project is a set of YAML files referenced by a single aggregator manifest. The manifest tells ARForge where to find each input category. Everything else - validation, export, and generation - flows from that manifest.

## Scaffold layout

Running `arforge init my-project` produces this layout:

```text
my-project/
|-- autosar.project.yaml       <- aggregator manifest
|-- types/
|   |-- base_types.yaml
|   |-- implementation_types.yaml
|   `-- application_types.yaml
|-- units/
|   `-- units.yaml
|-- compu_methods/
|   `-- compu_methods.yaml
|-- modes/
|   `-- operation_mode.yaml
|-- interfaces/
|   |-- If_OperationMode.yaml
|   `-- If_VehicleSpeed.yaml
|-- subcompositions/
|   `-- subcomposition_speed_path.yaml
|-- swcs/
|   |-- SpeedSensor.yaml
|   |-- SpeedReporter.yaml
|   `-- SystemSupervisor.yaml
`-- system.yaml
```

This is a convention, not a constraint. The scaffold is intentionally small enough to read in one sitting, but it already shows the recommended default modeling story: one top-level atomic SWC, one reusable subcomposition, sender-receiver data flow, a mode-switch interface, and delegation across the subcomposition boundary. The manifest can point to files in any layout. Glob patterns are supported for interfaces, SWCs, subcompositions, units, compu methods, and mode declaration groups.

## The aggregator manifest

The manifest is the single entry point for all ARForge commands. It declares the AUTOSAR version, the root ARXML package name, and the location of every input file.

```yaml
# autosar.project.yaml
autosar:
  version: "4.2"
  rootPackage: "MY_PROJECT"
  packageLayoutRef: "packages/company_layout.yaml"

inputs:
  baseTypes: "types/base_types.yaml"
  implementationDataTypes: "types/implementation_types.yaml"
  applicationDataTypes: "types/application_types.yaml"
  units:
    - "units/units.yaml"
  compuMethods:
    - "compu_methods/compu_methods.yaml"
  modeDeclarationGroups:
    - "modes/*.yaml"
  interfaces:
    - "interfaces/*.yaml"
  swcs:
    - "swcs/*.yaml"
  subcompositions:
    - "subcompositions/*.yaml"
  system: "system.yaml"
```

All paths are resolved relative to the manifest file. This means the manifest and its inputs can live anywhere in a repository as long as the relative paths are correct.

`rootPackage` is always the top-level AUTOSAR package emitted by the exporter. `packageLayoutRef` is optional and points to an external package-layout file that controls the subpackage structure below that root package.

## External package layouts

ARForge treats AUTOSAR packages as export-time containers and namespaces for packageable elements. They affect ARXML reference paths and tool compatibility, but they do not define runtime behavior, instance wiring, or architecture semantics.

Use an external package layout file when you need company-specific ARXML package paths:

```yaml
packageLayout:
  name: "CompanyLayout"
  defaults:
    swc: "Components/Common"
    interface: "Interfaces/Common"
    applicationDataType: "DataTypes/Application"
    implementationDataType: "DataTypes/Implementation"
    baseType: "DataTypes/Base"
    compuMethod: "DataTypes/CompuMethods"
    unit: "DataTypes/Units"
    modeDeclarationGroup: "Modes"
    composition: "Components/Compositions"
    system: "System"
  allowedPackages:
    - "Components"
    - "Components/Common"
    - "Components/Brake"
    - "Interfaces"
    - "Interfaces/Common"
    - "Interfaces/Brake"
    - "DataTypes/Application"
    - "DataTypes/Implementation"
    - "DataTypes/Base"
    - "DataTypes/CompuMethods"
    - "DataTypes/Units"
    - "Modes"
    - "System"
```

Packageable top-level elements may then opt into an explicit package:

```yaml
swc:
  name: "BrakeController"
  package: "Components/Brake"
```

Unassigned elements fall back to the category default from the external layout.

Supported explicit `package` targets:

- SWCs
- reusable subcomposition types
- interfaces
- base types
- implementation data types
- application data types
- compu methods
- units
- mode declaration groups
- system

Nested elements do not carry a `package` field. This includes runnables, ports, connectors, operations, data elements, and individual mode declarations. Those remain nested under their owning packageable element.

### Package layout authoring rules

When defining package layouts and per-element package assignments, ARForge currently enforces these rules:

- package paths are relative to `rootPackage`
- package paths must not start with `/`
- package paths must not end with `/`
- package paths must not contain empty segments such as `Components//Brake`
- each segment must be a valid AUTOSAR-style short name using letters, digits, and `_`
- explicit element packages must also appear in `allowedPackages`
- category defaults should also appear in `allowedPackages`

Example explicit assignments across multiple categories:

```yaml
interface:
  name: "If_BrakeTorque"
  type: "senderReceiver"
  package: "Interfaces/Brake"
```

```yaml
applicationDataTypes:
  - name: "App_BrakeTorque"
    implementationTypeRef: "Impl_uint16"
    package: "DataTypes/Application"
```

```yaml
modeDeclarationGroups:
  - name: "Mdg_BrakeMode"
    initialMode: "OFF"
    package: "Modes"
```

## What belongs where

**`types/`** - data type definitions, split across three files by convention.

- `base_types.yaml` - platform-level types (`uint8`, `uint16`, etc.), including a human-friendly `category` field such as `fixedLength`
- `implementation_types.yaml` - implementation data types backed by base types; scalars, arrays, structs
- `application_types.yaml` - application data types with optional constraints, unit references, and compu method references

**`units/`** - physical unit definitions referenced by application types and compu methods.

**`compu_methods/`** - computation method definitions (`linear`, `textTable`) that describe physical scaling for application types.

**`modes/`** - `ModeDeclarationGroup` definitions. Each group defines a named set of modes with an initial mode. Groups are referenced by mode-switch interfaces and resolved transitively through mode-switch ports to `modeSwitchEvents` on runnables. Unused mode groups are flagged by `CORE-014`.

**`interfaces/`** - one file per interface. Each file defines a single sender-receiver, client-server, or mode-switch interface. Keeping one interface per file makes diffs clean and makes glob patterns in the manifest work well.

**`swcs/`** - one file per atomic SWC type. Each file defines a single SWC type with its ports, runnables, events, and ComSpec.

**`subcompositions/`** - reusable composition type definitions. Each file defines one subcomposition type with optional composition boundary ports, inner component prototypes, internal assembly connectors, and optional `delegationConnectors` that map outer composition ports to inner component ports. Subcompositions may instantiate atomic SWCs only in the current hierarchy depth.

```yaml
subcomposition:
  name: "SubComposition_SpeedPath"
  ports:
    - name: "Rp_OperationModeIn"
      direction: "requires"
      interfaceRef: "If_OperationMode"
  components:
    - name: "SpeedSensor_1"
      typeRef: "SpeedSensor"
  delegationConnectors:
    - inner: "SpeedSensor_1.Rp_OperationModeIn"
      outer: "Rp_OperationModeIn"
```

**`system.yaml`** - the top-level system composition. Declares component prototypes whose `typeRef` may target either an atomic SWC type or a subcomposition type. There is one system file per project.

## Build output

Export output is written to the path passed to `arforge export`. By convention this lives under `build/` and should not be committed to source control if it is generated in CI.

Split export (`--split-by-swc`) produces shared/common ARXML, one file per component type, and a distinct root system composition ARXML:

```text
build/
|-- MY_PROJECT_SharedTypes.arxml
|-- SpeedSensor.arxml
|-- SpeedReporter.arxml
|-- SystemSupervisor.arxml
|-- SubComposition_SpeedPath.arxml
`-- DemoSystem.arxml
```

Monolithic export produces a single combined file:

```text
build/all.arxml
```

Code generation writes per-SWC starter artifacts under the path passed to `arforge generate code`, for example:

```text
build/code/
|-- SpeedSensor.h
|-- SpeedSensor.c
|-- SpeedReporter.h
|-- SpeedReporter.c
|-- SystemSupervisor.h
`-- SystemSupervisor.c
```

## VS Code setup

ARForge ships with a `.vscode/` directory that configures the editor automatically when you open the repository root in VS Code.

**Required extensions:**

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [YAML](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) (Red Hat)

Once both extensions are installed, YAML schema autocomplete and inline validation diagnostics activate for the standard ARForge YAML file layout without any manual configuration.

**Configuring VS Code task settings:**

The VS Code tasks resolve the project manifest, optional validation profile, and shared output root from `.vscode/settings.json`:

```jsonc
"arforge.projectFile": "examples/minimal/autosar.project.yaml"
"arforge.validationProfile": "examples/features/validation_profiles/naming.yaml"
"arforge.outputDir": "build"
```

Settings:

- `arforge.projectFile` - active project manifest used by validate, export, report, and generate tasks
- `arforge.validationProfile` - optional profile used by the profile-aware validation task
- `arforge.outputDir` - shared output root for export, report, diagram, and code-generation tasks

Change these to point to your own project files and preferred output root. The tasks pick them up automatically.

**Available tasks** (`Terminal -> Run Task`):

| Task | What it runs |
|---|---|
| `arforge: validate project (core)` | `python -m arforge.cli validate <projectFile> -vv` |
| `arforge: validate project (profile)` | `python -m arforge.cli validate <projectFile> --profile <validationProfile> -vv` |
| `arforge: generate report` | `python -m arforge.cli report <projectFile> --out <outputDir>/docs/Report.md` |
| `arforge: export project (split by swc)` | `python -m arforge.cli export <projectFile> --out <outputDir>/arxml --split-by-swc -vv` |
| `arforge: export project (monolithic)` | `python -m arforge.cli export <projectFile> --out <outputDir>/arxml/project.arxml -vv` |
| `arforge: generate Plantuml` | `python -m arforge.cli generate diagram <projectFile> --out <outputDir>/diagrams` |
| `arforge: generate C-code` | `python -m arforge.cli generate code <projectFile> --lang c --out <outputDir>/code` |
| `arforge: init project` | `python -m arforge.cli init demo-project` |
| `arforge: pytest` | `pytest -q` |

Tasks resolve the correct Python executable for both Linux and Windows using VS Code's `${workspaceFolder}` variable, so no manual path editing is needed on either platform.

This page is the canonical VS Code setup reference. The README and overview intentionally keep only a short summary to avoid repeating the same task table in multiple places.

## Repository-level layout

At the repository level, the ARForge implementation itself is organized as follows. This is relevant for contributors.

```text
arforge/                    <- CLI, loader, model, validation, export, codegen, scaffold
arforge/validation/cases/   <- domain-organized semantic validation cases
schemas/                    <- JSON Schema files for all input categories, including validation profiles
templates/                  <- Jinja2 templates grouped by output kind (`arxml/`, `reports/`, `code/`, `diagrams/`)
examples/                   <- user-facing example projects and fixtures
examples/minimal/           <- starter project that validates and exports successfully
examples/features/          <- focused feature-oriented examples such as validation profiles
examples/invalid/           <- invalid model fixtures used by the test suite
tests/                      <- pytest coverage
docs/                       <- this documentation
.vscode/                    <- VS Code schema, task, and settings configuration
```
