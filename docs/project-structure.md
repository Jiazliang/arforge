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
|   `-- power_state.yaml
|-- interfaces/
|   |-- If_VehicleSpeed.yaml
|   `-- If_PowerState.yaml
|-- subcompositions/
|   `-- subcomposition_speed_cluster.yaml
|-- swcs/
|   |-- SpeedSensor.yaml
|   |-- SpeedDisplay.yaml
|   `-- DiagManager.yaml
`-- system.yaml
```

This is a convention, not a constraint. The manifest can point to files in any layout. Glob patterns are supported for interfaces, SWCs, subcompositions, units, compu methods, and mode declaration groups.

## The aggregator manifest

The manifest is the single entry point for all ARForge commands. It declares the AUTOSAR version, the root ARXML package name, and the location of every input file.

```yaml
# autosar.project.yaml
autosar:
  version: "4.2"
  rootPackage: "MY_PROJECT"

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
  name: "SubComposition_SpeedCluster"
  ports:
    - name: "Rp_VehicleSpeedIn"
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
  components:
    - name: "SpeedDisplay_1"
      typeRef: "SpeedDisplay"
  delegationConnectors:
    - inner: "SpeedDisplay_1.Rp_VehicleSpeed"
      outer: "Rp_VehicleSpeedIn"
```

**`system.yaml`** - the top-level system composition. Declares component prototypes whose `typeRef` may target either an atomic SWC type or a subcomposition type. There is one system file per project.

## Build output

Export output is written to the path passed to `arforge export`. By convention this lives under `build/` and should not be committed to source control if it is generated in CI.

Split export (`--split-by-swc`) produces shared/common ARXML, one file per component type, and a distinct root system composition ARXML:

```text
build/
|-- MY_PROJECT_SharedTypes.arxml
|-- DiagManager.arxml
|-- SpeedSensor.arxml
|-- SpeedDisplay.arxml
|-- SubComposition_SpeedCluster.arxml
`-- DemoSystem.arxml
```

Monolithic export produces a single combined file:

```text
build/all.arxml
```

Code generation writes per-SWC starter artifacts under the path passed to `arforge generate code`, for example:

```text
build/code/
|-- DiagManager.h
|-- DiagManager.c
|-- SpeedSensor.h
|-- SpeedSensor.c
|-- SpeedDisplay.h
`-- SpeedDisplay.c
```

## VS Code setup

ARForge ships with a `.vscode/` directory that configures the editor automatically when you open the repository root in VS Code.

**Required extensions:**

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [YAML](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) (Red Hat)

Once both extensions are installed, YAML schema autocomplete and inline validation diagnostics activate for the standard ARForge YAML file layout without any manual configuration.

**Configuring the active project file:**

The VS Code tasks resolve the project manifest from a single setting in `.vscode/settings.json`:

```jsonc
"arforge.projectFile": "examples/autosar.project.yaml"
```

Change this path to point to your own project manifest. The validate, export, and generate tasks pick it up automatically.

**Available tasks** (`Terminal -> Run Task`):

| Task | What it runs |
|---|---|
| `arforge: validate project` | `python -m arforge.cli validate <projectFile> -vv` |
| `arforge: export project (split by swc)` | `python -m arforge.cli export <projectFile> --out build/arxml --split-by-swc -vv` |
| `arforge: export project (monolithic)` | `python -m arforge.cli export <projectFile> --out build/arxml/DemoProject.arxml -vv` |
| `arforge: generate Plantuml` | `python -m arforge.cli generate diagram <projectFile> --out build/diagrams_plantuml` |
| `arforge: generate C-code` | `python -m arforge.cli generate code <projectFile> --lang c --out build/code` |
| `arforge: init project` | `python -m arforge.cli init demo-project` |
| `arforge: pytest` | `pytest -q` |

Tasks resolve the correct Python executable for both Linux and Windows using VS Code's `${workspaceFolder}` variable, so no manual path editing is needed on either platform.

This page is the canonical VS Code setup reference. The README and overview intentionally keep only a short summary to avoid repeating the same task table in multiple places.

## Repository-level layout

At the repository level, the ARForge implementation itself is organized as follows. This is relevant for contributors.

```text
arforge/                    <- CLI, loader, model, validation, export, codegen, scaffold
arforge/validation/cases/   <- domain-organized semantic validation cases
schemas/                    <- JSON Schema files for all input categories
templates/                  <- Jinja2 ARXML, codegen, and diagram templates
examples/                   <- valid example project
examples/invalid/           <- invalid model fixtures used by the test suite
tests/                      <- pytest coverage
docs/                       <- this documentation
.vscode/                    <- VS Code schema, task, and settings configuration
```
