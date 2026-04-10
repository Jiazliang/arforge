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
        "This scaffold includes a small runnable sender-receiver example:\n\n"
        "- `types/` defines reusable data types.\n"
        "- `modes/power_state.yaml` defines a simple mode declaration group.\n"
        "- `interfaces/If_VehicleSpeed.yaml` and `interfaces/If_PowerState.yaml` define the example interfaces used by ports.\n"
        "- `swcs/` defines atomic SWC types, including a standalone `DiagManager` and the reusable building blocks used inside a subcomposition.\n"
        "- `subcompositions/subcomposition_speed_cluster.yaml` defines a reusable subcomposition that exposes composition boundary ports, instantiates atomic SWCs, wires its internal connectors, and maps outer ports through delegation connectors.\n"
        "- `system.yaml` instantiates that subcomposition type plus one standalone atomic SWC at the top level.\n"
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
  - name: "uint16"
    description: "Unsigned 16-bit platform integer."
    bitLength: 16
    signedness: "unsigned"
    nativeDeclaration: "uint16"
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
    description: "Vehicle speed value shared between the demo SWC types."
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
    description: "Identity scaling for the demo vehicle speed value."
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
  - name: "Mdg_PowerState"
    description: "Power state modes used by the scaffolded mode-switch interface."
    initialMode: "OFF"
    modes:
      - "OFF"
      - "ON"
      - "SLEEP"
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


def interface_power_state_yaml() -> str:
    return _with_header(
        "ARForge: Interface definition",
        "Defines a Sender-Receiver, Client-Server, or Mode-Switch interface used by SWC ports.",
body="""interface:
  name: "If_PowerState"
  description: "Mode switch interface for ECU power state."
  type: "modeSwitch"
  modeGroupRef: "Mdg_PowerState"
""",
    )


def swc_speed_sensor_yaml() -> str:
    return _with_header(
        "ARForge: Software Component Type",
        "Defines ports, runnables, and internal behavior for one AUTOSAR SWC type.",
body="""swc:
  name: "SpeedSensor"
  description: "SWC type that reacts to the external power-state input and publishes the current vehicle speed."
  runnables:
    - name: "Runnable_PublishVehicleSpeed"
      description: "Writes the latest vehicle speed sample to the provided port."
      timingEventMs: 10
      writes:
        - port: "Pp_VehicleSpeed"
          dataElement: "VehicleSpeed"
    - name: "Runnable_OnPowerOn"
      description: "React to the delegated ECU power mode entering ON."
      modeSwitchEvents:
        - port: "Rp_PowerStateIn"
          mode: "ON"
  ports:
    - name: "Pp_VehicleSpeed"
      description: "Provided sender-receiver port for publishing speed."
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
    - name: "Rp_PowerStateIn"
      description: "Required mode switch port delegated from the subcomposition boundary."
      direction: "requires"
      interfaceRef: "If_PowerState"
    - name: "Pp_PowerState"
      description: "Provided mode switch port forwarded to the internal display."
      direction: "provides"
      interfaceRef: "If_PowerState"
""",
    )


def swc_speed_display_yaml() -> str:
    return _with_header(
        "ARForge: Software Component Type",
        "Defines ports, runnables, and internal behavior for one AUTOSAR SWC type.",
body="""swc:
  name: "SpeedDisplay"
  description: "SWC type that reads vehicle speed through explicit, implicit, and queued receiver semantics."
  runnables:
    - name: "Runnable_ReadVehicleSpeed"
      description: "Reads the latest vehicle speed sample from the explicit required port and forwards it outside the subcomposition."
      timingEventMs: 10
      reads:
        - port: "Rp_VehicleSpeed"
          dataElement: "VehicleSpeed"
      writes:
        - port: "Pp_VehicleSpeedOut"
          dataElement: "VehicleSpeed"
    - name: "Runnable_ReadVehicleSpeedImplicit"
      description: "Reads the latest vehicle speed sample from the implicit required port."
      timingEventMs: 10
      reads:
        - port: "Rp_VehicleSpeedImplicit"
          dataElement: "VehicleSpeed"
    - name: "Runnable_ReadVehicleSpeedQueued"
      description: "Reads the latest vehicle speed sample from the queued required port."
      timingEventMs: 10
      reads:
        - port: "Rp_VehicleSpeedQueued"
          dataElement: "VehicleSpeed"
    - name: "Runnable_OnPowerOn"
      description: "React to the ECU entering the ON power mode."
      modeSwitchEvents:
        - port: "Rp_PowerState"
          mode: "ON"
  ports:
    - name: "Rp_VehicleSpeed"
      description: "Required sender-receiver port for receiving speed."
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
      comSpec:
        mode: "explicit"
    - name: "Rp_VehicleSpeedImplicit"
      description: "Required sender-receiver port for receiving speed with implicit semantics."
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
      comSpec:
        mode: "implicit"
    - name: "Rp_VehicleSpeedQueued"
      description: "Required sender-receiver port for receiving speed with queued semantics."
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
      comSpec:
        mode: "queued"
        queueLength: 4
    - name: "Rp_PowerState"
      description: "Required mode switch port for ECU power state."
      direction: "requires"
      interfaceRef: "If_PowerState"
    - name: "Pp_VehicleSpeedOut"
      description: "Provided sender-receiver port delegated to the subcomposition boundary."
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
""",
    )


def swc_diag_manager_yaml() -> str:
    return _with_header(
        "ARForge: Software Component Type",
        "Defines ports, runnables, and internal behavior for one AUTOSAR SWC type.",
body="""swc:
  name: "DiagManager"
  description: "Standalone atomic SWC type used to show that one top-level SWC can connect to a reusable subcomposition through boundary ports."
  runnables:
    - name: "Runnable_PublishPowerState"
      description: "Acts as the top-level power-state source for the reusable subcomposition."
      initEvent: true
    - name: "Runnable_ReadClusterSpeed"
      description: "Reads the speed value exposed by the reusable subcomposition."
      timingEventMs: 10
      reads:
        - port: "Rp_VehicleSpeed"
          dataElement: "VehicleSpeed"
  ports:
    - name: "Pp_PowerState"
      description: "Provided mode switch port connected to the subcomposition input boundary."
      direction: "provides"
      interfaceRef: "If_PowerState"
    - name: "Rp_VehicleSpeed"
      description: "Required sender-receiver port connected to the subcomposition output boundary."
      direction: "requires"
      interfaceRef: "If_VehicleSpeed"
      comSpec:
        mode: "explicit"
""",
    )


def subcomposition_speed_cluster_yaml() -> str:
    return _with_header(
        "ARForge: Subcomposition type",
        "Defines reusable inner component prototypes and their internal assembly connectors.",
body="""subcomposition:
  name: "SubComposition_SpeedCluster"
  description: "Reusable subcomposition that accepts a boundary power-state input, keeps the sensor-to-display wiring internal, and exposes a boundary speed output."
  ports:
    - name: "Rp_PowerStateIn"
      description: "Required outer composition port delegated to the internal sensor power-state input."
      direction: "requires"
      interfaceRef: "If_PowerState"
    - name: "Pp_VehicleSpeedOut"
      description: "Provided outer composition port delegated from the internal display speed output."
      direction: "provides"
      interfaceRef: "If_VehicleSpeed"
  components:
    - name: "SpeedSensor_1"
      description: "Internal speed publisher instance."
      typeRef: "SpeedSensor"
    - name: "SpeedDisplay_1"
      description: "Internal speed consumer instance."
      typeRef: "SpeedDisplay"
  connectors:
    - from: "SpeedSensor_1.Pp_VehicleSpeed"
      description: "Connects the published speed sample to the explicit receiver port."
      to: "SpeedDisplay_1.Rp_VehicleSpeed"
    - from: "SpeedSensor_1.Pp_VehicleSpeed"
      description: "Connects the published speed sample to the implicit receiver port."
      to: "SpeedDisplay_1.Rp_VehicleSpeedImplicit"
    - from: "SpeedSensor_1.Pp_VehicleSpeed"
      description: "Connects the published speed sample to the queued receiver port."
      to: "SpeedDisplay_1.Rp_VehicleSpeedQueued"
    - from: "SpeedSensor_1.Pp_PowerState"
      description: "Connects the ECU power-state mode to the display instance."
      to: "SpeedDisplay_1.Rp_PowerState"
  delegationConnectors:
    - inner: "SpeedSensor_1.Rp_PowerStateIn"
      outer: "Rp_PowerStateIn"
    - inner: "SpeedDisplay_1.Pp_VehicleSpeedOut"
      outer: "Pp_VehicleSpeedOut"
""",
    )


def system_yaml(system_name: str) -> str:
    return _with_header(
        "ARForge: System composition",
        "Defines component prototypes (instances) and connectors between their ports.",
body=f"""system:
  name: "{system_name}"
  description: "Demo AUTOSAR system showing one standalone atomic SWC connected to one reusable subcomposition through composition boundary ports."
  composition:
    name: "Composition_{system_name}"
    description: "Top-level composition for the scaffolded hierarchical example."
    # These are component prototypes (instances in the system).
    # typeRef may point to either an atomic SWC type or a reusable subcomposition type.
    components:
      - name: "SpeedCluster_0"
        description: "Instance of the reusable speed-cluster subcomposition."
        typeRef: "SubComposition_SpeedCluster"
      - name: "DiagManager_0"
        description: "Standalone top-level atomic SWC instance connected to the reusable speed-cluster subcomposition."
        typeRef: "DiagManager"
    connectors:
      - from: "DiagManager_0.Pp_PowerState"
        description: "Feeds the top-level power-state output into the subcomposition boundary."
        to: "SpeedCluster_0.Rp_PowerStateIn"
      - from: "SpeedCluster_0.Pp_VehicleSpeedOut"
        description: "Returns the speed value exposed by the subcomposition back to the standalone SWC."
        to: "DiagManager_0.Rp_VehicleSpeed"
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
        Path("modes/power_state.yaml"): mode_declaration_groups_yaml(),
    }

    if no_example:
        files[Path("system.yaml")] = structure_only_system_yaml(system_name)
        return files

    files[Path("interfaces/If_VehicleSpeed.yaml")] = interface_vehicle_speed_yaml()
    files[Path("interfaces/If_PowerState.yaml")] = interface_power_state_yaml()
    files[Path("swcs/SpeedSensor.yaml")] = swc_speed_sensor_yaml()
    files[Path("swcs/SpeedDisplay.yaml")] = swc_speed_display_yaml()
    files[Path("swcs/DiagManager.yaml")] = swc_diag_manager_yaml()
    files[Path("subcompositions/subcomposition_speed_cluster.yaml")] = subcomposition_speed_cluster_yaml()
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
