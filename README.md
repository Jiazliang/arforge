# ARForge

> YAML-first AUTOSAR Classic SWC design. Version-controlled, CI-friendly, no license server.

![AUTOSAR Classic 4.2](https://img.shields.io/badge/AUTOSAR-Classic%204.2-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)
![Python](https://img.shields.io/badge/python-3.x-lightgrey)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey)
![Tests](https://img.shields.io/badge/tests-pytest-yellow)

ARForge lets you design AUTOSAR Classic SWCs and compositions in plain YAML, validate them against semantic rules, and export deterministic AUTOSAR-aligned ARXML for the currently supported scope - without a GUI tool or license server. It runs on Linux and Windows, integrates with Visual Studio Code, and fits naturally into any CI pipeline.

---

## Why ARForge

AUTOSAR SWC design in GUI-based tools is expensive, opaque, and hostile to version control. Diffs are unreadable, validation is manual, and the toolchain cannot run in CI. ARForge is designed from the ground up for the opposite: a YAML source of truth that is readable, diffable, and automatable.

| | |
|---|---|
| **Text-first design** | SWCs, compositions, interfaces, modes, and types - all in human-readable YAML |
| **Semantic validation** | Stable finding codes across supported constructs. Catches design problems before export |
| **Validation profiles** | Optional profile YAML for project-specific rule modules, rule enable/disable control, and extensions-only execution |
| **Clean ARXML export** | Deterministic, ordered AUTOSAR-aligned output for the currently supported feature set |
| **External package layout** | Optional company-specific ARXML package namespaces with per-element package assignment and deterministic references |
| **CI-ready CLI** | Validate, report, and export in a pipeline with no GUI dependency or license server |
| **VS Code integration** | YAML schema autocomplete, inline diagnostics, and task runner built in |

---

## Who this is for

ARForge is aimed at AUTOSAR engineers, independent consultants, and teams who want SWC design to live in version control and run in CI - without a commercial toolchain. It works well for greenfield SWC development, architecture work done offline, and automated ARXML generation from a controlled source of truth.

---

## What ARForge covers

Current implementation targets a practical AUTOSAR Classic 4.2 subset:

| Area | Details |
|---|---|
| **Data types** | Base, implementation, and application types; scalar, array, and struct; units and compu methods (linear, text table) |
| **Sender-Receiver interfaces** | Data elements, implicit/explicit/queued ComSpec, receiver init values, queue length validation |
| **Client-Server interfaces** | Operations, in/out/inout arguments, return types, possible errors, sync/async call modes, timeout configuration |
| **Mode-Switch interfaces** | `ModeDeclarationGroup` definitions, mode manager and user ports, `ModeSwitchEvent` runnable triggers |
| **SWC types** | Provides/requires ports, runnables, `TimingEvent`, `InitEvent`, `OperationInvokedEvent`, `DataReceiveEvent`, `ModeSwitchEvent` |
| **Runnable access** | `reads`, `writes`, `calls`, `raisesErrors` - all validated against port direction and interface kind |
| **System composition** | Component prototypes, SWC type references, port-level assembly connectors for SR, CS, and mode-switch |
| **Validation** | Stable finding codes, three severity levels (error/warning/info), verbose diagnostics |
| **Export** | Jinja2-based ARXML, monolithic or split-by-SWC, deterministic ordering, shared rendering logic across both modes |
| **Code skeletons** | Template-driven C `.h` / `.c` starter files generated from validated SWC models |
| **Diagrams** | Unified `generate diagram` command for PlantUML architecture views |
| **Reports** | Deterministic Markdown architecture summaries via `arforge report` |

---

## Quickstart

### Install

**Linux / macOS**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows**
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### A minimal SWC in YAML

```yaml
# swcs/SpeedSensor.yaml
swc:
  name: "SpeedSensor"
  description: "Publishes the current vehicle speed."
  ports:
    - name: "Pp_VehicleSpeed"
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
    - name: "Pp_PowerState"
      direction: "provides"
      interfaceRef: "If_PowerState"
  runnables:
    - name: "Runnable_PublishVehicleSpeed"
      timingEventMs: 10
      writes:
        - port: "Pp_VehicleSpeed"
          dataElement: "VehicleSpeed"
```

### Typical workflow

```bash
# Initialize a new project scaffold
python -m arforge.cli init my-project

# Validate - stable finding codes on any semantic issue
python -m arforge.cli validate examples/minimal/autosar.project.yaml

# Validate with a sample naming profile
python -m arforge.cli validate examples/minimal/autosar.project.yaml --profile examples/features/validation_profiles/naming.yaml

# Validate with a stricter project-governance profile
python -m arforge.cli validate examples/minimal/autosar.project.yaml --profile examples/features/validation_profiles/strict_hygiene.yaml

# Export - monolithic or split by component type
python -m arforge.cli export examples/minimal/autosar.project.yaml --out build/out --split-by-swc

# Generate a Markdown architecture report
python -m arforge.cli report examples/minimal/autosar.project.yaml --out build/docs/Report.md

# Generate a structural Markdown diff between two model versions
python -m arforge.cli diff examples/minimal/autosar.project.yaml examples/minimal/autosar.project.yaml --out build/docs/diff.md

# Compare the working tree project against a version stored in Git
python -m arforge.cli diff examples/minimal/autosar.project.yaml --base-git-ref HEAD --out build/docs/diff.md

# Generate starter C skeletons for SWCs
python -m arforge.cli generate code examples/minimal/autosar.project.yaml --lang c --out build/code

# Generate architecture diagrams
python -m arforge.cli generate diagram examples/minimal/autosar.project.yaml --out build/diagrams
```

`report` summarizes what a model contains, while `diff` summarizes what changed between two model versions for pull requests, architecture reviews, and CI artifacts. `generate code` produces deterministic starter skeletons for each SWC, for example `<SwcName>.h` and `<SwcName>.c`. The output is intentionally scaffold-level code with `Rte_Read_*`, `Rte_Write_*`, and `Rte_Call_*` placeholders rather than full AUTOSAR RTE integration.

The diagram generator writes:
- `composition_<System>.puml`
- `subcomposition_<Subcomposition>.puml`
- `interfaces_wiring.puml`
- `interfaces_contracts.puml`
- `behavior_<SWC>.puml`

### Run tests

```bash
pytest -q
```

> The test suite covers valid and invalid inputs across all supported AUTOSAR constructs. Every validation rule has explicit test cases for both correct and incorrect models.

---

## VS Code integration

ARForge includes a `.vscode/` configuration for YAML schema validation, autocomplete, and task runner integration out of the box.

The full setup instructions, task list, and VS Code task settings live in [docs/project-structure.md](docs/project-structure.md#vs-code-setup). If you just want the essentials:

- install the VS Code `Python` and `YAML` extensions
- open the repository root in VS Code
- set `arforge.projectFile`, optional `arforge.validationProfile`, and `arforge.outputDir` in `.vscode/settings.json`

---

## Documentation

Start with [docs/index.md](docs/index.md).

| Doc | Contents |
|---|---|
| [Overview](docs/overview.md) | What ARForge does and where it fits in a workflow |
| [Project Structure](docs/project-structure.md) | Project manifest, scaffold layout, build output, and VS Code setup |
| [Modeling Concepts](docs/modeling-concepts.md) | Full YAML modeling reference with examples |
| [Validation](docs/validation.md) | Validation rule families and severities |
| [Validation Profiles](docs/validation-profiles.md) | Project-specific validation extensions and profile format |
| [Custom Validation Rules](docs/custom-validation-rules.md) | How to write rule functions, inspect validation context, and emit findings |
| [CLI](docs/cli.md) | All commands and options |
| [Architecture](docs/architecture.md) | Internal pipeline, for contributors |
| [Roadmap](docs/roadmap.md) | Current capabilities and planned features |

---

## Contributing

Issues and pull requests are welcome. See `CONTRIBUTING.md` for contribution expectations and the maintainer-led project model.

---

## License

Apache-2.0. See `DISCLAIMER.md` for project independence and affiliation notes.

---

## Contact

**Bojan Zivkovic** - questions, feedback, collaboration, or consulting inquiries welcome via [LinkedIn](https://www.linkedin.com/in/bojanzivkovic86) or GitHub Issues.
