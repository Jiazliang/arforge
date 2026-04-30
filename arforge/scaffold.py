"""Starter-project scaffold generation for `arforge init`.

This module creates the recommended on-disk project layout, including example
inputs and README content for first-time users bootstrapping a new model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict


def _with_header(*header_lines: str, body: str) -> str:
    header = "\n".join(f"# {line}" for line in header_lines)
    return f"{header}\n{body}"


def project_yaml(system_name: str) -> str:
    return _with_header(
        "ARForge: Project input manifest",
        "Lists the YAML files that make up this AUTOSAR project.",
        body=f"""autosar:
  version: "4.2"
  rootPackage: "{system_name.upper()}"

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
""",
    )


def readme_md(system_name: str, *, no_example: bool = False) -> str:
    example_note = (
        "This scaffold is the recommended small reference project for a new ARForge model.\n\n"
        "It stays compact, but it already demonstrates the core modeling flow:\n\n"
        "- `types/` defines reusable data types.\n"
        "- `modes/operation_mode.yaml` defines the mode declaration group used by the starter flow.\n"
        "- `interfaces/If_VehicleSpeed.yaml` and `interfaces/If_OperationMode.yaml` define the sender-receiver and mode-switch interfaces used by ports.\n"
        "- `swcs/` defines the atomic SWC types: a top-level `SystemSupervisor` and the reusable inner `SpeedSensor` and `SpeedReporter` building blocks, including both `modeSwitchEvents` and runnable `modeConditions`.\n"
        "- `subcompositions/subcomposition_speed_path.yaml` defines a reusable subcomposition with boundary ports, internal assembly connectors, and delegation connectors.\n"
        f"- `system.yaml` instantiates the reusable subcomposition together with one standalone atomic SWC in `{system_name}`.\n"
    )
    if no_example:
        example_note = (
            "This scaffold creates the project structure without example interfaces or SWCs.\n\n"
            "- Add reusable data types under `types/`.\n"
            "- Update the mode declaration groups under `modes/`.\n"
            "- Add interface definitions under `interfaces/`.\n"
            "- Add SWC type definitions under `swcs/`.\n"
            "- Add reusable subcomposition types under `subcompositions/` when needed.\n"
            "- Define top-level component instances and connectors in `system.yaml`.\n"
        )
    return f"""# {system_name}

ARForge project scaffold for AUTOSAR Classic modeling.

{example_note}
Validate the project:

```bash
python -m arforge.cli validate autosar.project.yaml
```

Export ARXML:

```bash
python -m arforge.cli export autosar.project.yaml --out build/out --split-by-swc
```

Generate C skeletons:

```bash
python -m arforge.cli generate code autosar.project.yaml --lang c --out build/code
```
"""


def base_types_yaml() -> str:
    return _with_header(
        "ARForge: Base type definitions",
        "Defines low-level platform types used by implementation data types.",
        body="""baseTypes:
  - name: "uint8"
    description: "Unsigned 8-bit platform integer."
    bitLength: 8
    signedness: "unsigned"
    nativeDeclaration: "uint8"
    category: "fixedLength"
  - name: "uint16"
    description: "Unsigned 16-bit platform integer."
    bitLength: 16
    signedness: "unsigned"
    nativeDeclaration: "uint16"
    category: "fixedLength"
""",
    )


def implementation_types_yaml() -> str:
    return _with_header(
        "ARForge: Implementation data types",
        "Defines type-level implementation data types backed by platform base types.",
        body="""implementationDataTypes:
  - name: "Impl_VehicleSpeed_U16"
    description: "Raw implementation type for a vehicle speed sample."
    baseTypeRef: "uint16"
""",
    )


def application_types_yaml() -> str:
    return _with_header(
        "ARForge: Application data types",
        "Defines project-level application types used by interfaces.",
        body="""applicationDataTypes:
  - name: "App_VehicleSpeed"
    description: "Vehicle speed value shared between the scaffolded SWC types."
    implementationTypeRef: "Impl_VehicleSpeed_U16"
    constraint:
      min: 0
      max: 250
    unitRef: "km_per_h"
    compuMethodRef: "CM_VehicleSpeed_Kph"
""",
    )


def units_yaml() -> str:
    return _with_header(
        "ARForge: Units",
        "Physical units referenced by application data types and compu methods.",
        body="""units:
  - name: "km_per_h"
    description: "Vehicle speed unit used by the scaffolded example."
    displayName: "km/h"
""",
    )


def compu_methods_yaml() -> str:
    return _with_header(
        "ARForge: Compu methods",
        "Simple physical scaling definitions for application data types.",
        body="""compuMethods:
  - name: "CM_VehicleSpeed_Kph"
    description: "Identity scaling for the starter vehicle speed value."
    category: "linear"
    unitRef: "km_per_h"
    factor: 1.0
    offset: 0.0
    physMin: 0
    physMax: 250
""",
    )


def mode_declaration_groups_yaml() -> str:
    return _with_header(
        "ARForge: Mode declaration groups",
        "Defines AUTOSAR mode declaration groups used by mode-switch interfaces.",
        body="""modeDeclarationGroups:
  - name: "Mdg_OperationMode"
    description: "Operation modes used by the scaffolded starter project."
    category: "explicitOrder"
    initialMode: "OFF"
    onTransitionValue: 255
    modes:
      - name: "OFF"
        value: 0
      - name: "ACTIVE"
        value: 1
      - name: "SERVICE"
        value: 2
""",
    )


def interface_vehicle_speed_yaml() -> str:
    return _with_header(
        "ARForge: Interface definition",
        "Defines a Sender-Receiver, Client-Server, or Mode-Switch interface used by SWC ports.",
        body="""interface:
  name: "If_VehicleSpeed"
  description: "Sender-receiver interface for the current vehicle speed."
  type: "senderReceiver"
  dataElements:
    - name: "VehicleSpeed"
      description: "Latest measured vehicle speed sample."
      typeRef: "App_VehicleSpeed"
""",
    )


def interface_operation_mode_yaml() -> str:
    return _with_header(
        "ARForge: Interface definition",
        "Defines a Sender-Receiver, Client-Server, or Mode-Switch interface used by SWC ports.",
        body="""interface:
  name: "If_OperationMode"
  description: "Mode switch interface for the starter project operation mode."
  type: "modeSwitch"
  modeGroupRef: "Mdg_OperationMode"
""",
    )


def swc_speed_sensor_yaml() -> str:
    return _with_header(
        "ARForge: Software Component Type",
        "Defines ports, runnables, and internal behavior for one AUTOSAR SWC type.",
        body="""swc:
  name: "SpeedSensor"
  description: "Publishes the current vehicle speed and reacts to the delegated operation mode."
  runnables:
    - name: "Runnable_PublishVehicleSpeed"
      description: "Writes the latest vehicle speed sample to the provided port while the delegated operation mode is ACTIVE."
      timingEventMs: 10
      modeConditions:
        - port: "Rp_OperationModeIn"
          mode: "ACTIVE"
      writes:
        - port: "Pp_VehicleSpeed"
          dataElement: "VehicleSpeed"
    - name: "Runnable_OnOperationActive"
      description: "React to the delegated operation mode entering ACTIVE."
      modeSwitchEvents:
        - port: "Rp_OperationModeIn"
          mode: "ACTIVE"
  ports:
    - name: "Pp_VehicleSpeed"
      description: "Provided sender-receiver port for publishing speed."
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
    - name: "Rp_OperationModeIn"
      description: "Required mode switch port delegated from the subcomposition boundary."
      direction: "requires"
      interfaceRef: "If_OperationMode"
    - name: "Pp_OperationMode"
      description: "Provided mode switch port forwarded to the internal reporter."
      direction: "provides"
      interfaceRef: "If_OperationMode"
""",
    )


def swc_speed_reporter_yaml() -> str:
    return _with_header(
        "ARForge: Software Component Type",
        "Defines ports, runnables, and internal behavior for one AUTOSAR SWC type.",
        body="""swc:
  name: "SpeedReporter"
  description: "Consumes the internal speed sample and republishes it on the subcomposition boundary."
  runnables:
    - name: "Runnable_ReportVehicleSpeed"
      description: "Reads the latest vehicle speed sample from the internal sender-receiver port and exposes it on the boundary-facing output while the forwarded operation mode is ACTIVE."
      timingEventMs: 10
      modeConditions:
        - port: "Rp_OperationMode"
          mode: "ACTIVE"
      reads:
        - port: "Rp_VehicleSpeed"
          dataElement: "VehicleSpeed"
      writes:
        - port: "Pp_VehicleSpeedOut"
          dataElement: "VehicleSpeed"
    - name: "Runnable_OnOperationActive"
      description: "React to the system entering the ACTIVE operation mode."
      modeSwitchEvents:
        - port: "Rp_OperationMode"
          mode: "ACTIVE"
  ports:
    - name: "Rp_VehicleSpeed"
      description: "Required sender-receiver port for receiving speed with an explicit nonqueued receiver ComSpec."
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
      comSpec:
        mode: "explicit"
        initValue: 0
    - name: "Rp_OperationMode"
      description: "Required mode switch port for the forwarded operation mode."
      direction: "requires"
      interfaceRef: "If_OperationMode"
    - name: "Pp_VehicleSpeedOut"
      description: "Provided sender-receiver port delegated to the subcomposition boundary."
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
""",
    )


def swc_system_supervisor_yaml() -> str:
    return _with_header(
        "ARForge: Software Component Type",
        "Defines ports, runnables, and internal behavior for one AUTOSAR SWC type.",
        body="""swc:
  name: "SystemSupervisor"
  description: "Top-level SWC that drives the example operation mode and reads the speed value returned by the reusable subcomposition."
  runnables:
    - name: "Runnable_InitOperationModeSource"
      description: "Acts as the top-level source for the starter project operation mode."
      initEvent: true
    - name: "Runnable_ReadVehicleSpeed"
      description: "Reads the speed value exposed by the reusable subcomposition."
      timingEventMs: 20
      reads:
        - port: "Rp_VehicleSpeed"
          dataElement: "VehicleSpeed"
  ports:
    - name: "Pp_OperationMode"
      description: "Provided mode switch port connected to the subcomposition input boundary."
      direction: "provides"
      interfaceRef: "If_OperationMode"
    - name: "Rp_VehicleSpeed"
      description: "Required sender-receiver port connected to the subcomposition output boundary."
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
      comSpec:
        mode: "explicit"
        initValue: 0
""",
    )


def subcomposition_speed_path_yaml() -> str:
    return _with_header(
        "ARForge: Subcomposition type",
        "Defines reusable inner component prototypes and their internal assembly connectors.",
        body="""subcomposition:
  name: "SubComposition_SpeedPath"
  description: "Reusable subcomposition that accepts an operation mode on its boundary, keeps the sensor-to-reporter wiring internal, and exposes a speed output."
  ports:
    # These boundary ports define the external API of the reusable subcomposition.
    - name: "Rp_OperationModeIn"
      description: "Required outer composition port delegated to the internal sensor operation-mode input."
      direction: "requires"
      interfaceRef: "If_OperationMode"
    - name: "Pp_VehicleSpeedOut"
      description: "Provided outer composition port delegated from the internal reporter speed output."
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
  components:
    - name: "SpeedSensor_1"
      description: "Internal speed publisher instance."
      typeRef: "SpeedSensor"
    - name: "SpeedReporter_1"
      description: "Internal speed reporter instance."
      typeRef: "SpeedReporter"
  connectors:
    - from: "SpeedSensor_1.Pp_VehicleSpeed"
      description: "Connects the published speed sample to the internal reporter."
      to: "SpeedReporter_1.Rp_VehicleSpeed"
    - from: "SpeedSensor_1.Pp_OperationMode"
      description: "Connects the forwarded operation mode to the internal reporter."
      to: "SpeedReporter_1.Rp_OperationMode"
  delegationConnectors:
    - inner: "SpeedSensor_1.Rp_OperationModeIn"
      outer: "Rp_OperationModeIn"
    - inner: "SpeedReporter_1.Pp_VehicleSpeedOut"
      outer: "Pp_VehicleSpeedOut"
""",
    )


def system_yaml(system_name: str) -> str:
    return _with_header(
        "ARForge: System composition",
        "Defines component prototypes (instances) and connectors between their ports.",
        body=f"""system:
  name: "{system_name}"
  description: "Starter AUTOSAR system showing one top-level atomic SWC connected to one reusable subcomposition through composition boundary ports."
  composition:
    name: "Composition_{system_name}"
    description: "Top-level composition for the scaffolded starter project."
    # These are component prototypes (instances in the system).
    # typeRef may point to either an atomic SWC type or a reusable subcomposition type.
    components:
      - name: "SpeedPath_0"
        description: "Instance of the reusable speed-path subcomposition."
        typeRef: "SubComposition_SpeedPath"
      - name: "SystemSupervisor_0"
        description: "Standalone top-level atomic SWC instance connected to the reusable speed-path subcomposition."
        typeRef: "SystemSupervisor"
    connectors:
      - from: "SystemSupervisor_0.Pp_OperationMode"
        description: "Feeds the top-level operation mode output into the subcomposition boundary."
        to: "SpeedPath_0.Rp_OperationModeIn"
      - from: "SpeedPath_0.Pp_VehicleSpeedOut"
        description: "Returns the speed value exposed by the subcomposition back to the standalone SWC."
        to: "SystemSupervisor_0.Rp_VehicleSpeed"
""",
    )


def structure_only_system_yaml(system_name: str) -> str:
    return _with_header(
        "ARForge: System composition",
        "Add components and connectors here when you are ready to model the system.",
        body=f"""# Example shape:
# system:
#   name: "{system_name}"
#   composition:
#     name: "Composition_{system_name}"
#     components:
#       - name: "MyComponent_1"
#         typeRef: "MyComponent"
#       - name: "MySubcomposition_1"
#         typeRef: "MySubcomposition"
#     connectors:
#       - from: "MyProvider_1.Pp_Port"
#         to: "MyConsumer_1.Rp_Port"
""",
    )


def scaffold_files(system_name: str, *, no_example: bool = False) -> Dict[Path, str]:
    files: Dict[Path, str] = {
        Path("README.md"): readme_md(system_name, no_example=no_example),
        Path("autosar.project.yaml"): project_yaml(system_name),
        Path("types/base_types.yaml"): base_types_yaml(),
        Path("types/implementation_types.yaml"): implementation_types_yaml(),
        Path("types/application_types.yaml"): application_types_yaml(),
        Path("units/units.yaml"): units_yaml(),
        Path("compu_methods/compu_methods.yaml"): compu_methods_yaml(),
        Path("modes/operation_mode.yaml"): mode_declaration_groups_yaml(),
    }

    if no_example:
        files[Path("system.yaml")] = structure_only_system_yaml(system_name)
        return files

    files[Path("interfaces/If_VehicleSpeed.yaml")] = interface_vehicle_speed_yaml()
    files[Path("interfaces/If_OperationMode.yaml")] = interface_operation_mode_yaml()
    files[Path("swcs/SpeedSensor.yaml")] = swc_speed_sensor_yaml()
    files[Path("swcs/SpeedReporter.yaml")] = swc_speed_reporter_yaml()
    files[Path("swcs/SystemSupervisor.yaml")] = swc_system_supervisor_yaml()
    files[Path("subcompositions/subcomposition_speed_path.yaml")] = subcomposition_speed_path_yaml()
    files[Path("system.yaml")] = system_yaml(system_name)
    return files


def scaffold_project(path: Path, *, name: str = "DemoSystem", force: bool = False, no_example: bool = False) -> list[Path]:
    target = path.resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"Target path exists and is not empty: {target}")

    target.mkdir(parents=True, exist_ok=True)
    files = scaffold_files(name, no_example=no_example)
    for rel_dir in [
        Path("interfaces"),
        Path("swcs"),
        Path("types"),
        Path("units"),
        Path("compu_methods"),
        Path("modes"),
        Path("subcompositions"),
    ]:
        (target / rel_dir).mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for rel_path in sorted(files.keys(), key=lambda p: p.as_posix()):
        out_path = target / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(files[rel_path], encoding="utf-8")
        written.append(out_path)
    return written
