"""ARXML export pipeline for monolithic and split outputs.

This module transforms validated project models into deterministic AUTOSAR XML
artifacts, including shared type files, per-component files, and system output.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
from time import perf_counter
from typing import Dict, List, Literal, Optional
from xml.etree import ElementTree as ET

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .model import (
    CompuMethod,
    ComponentPrototype,
    Composition,
    Connection,
    DelegationConnector,
    Interface,
    ModeDeclarationGroup,
    Operation,
    Project,
    Runnable,
    SubcompositionType,
    Swc,
)
from .arxml_paths import ArxmlPathResolver, build_package_tree, join_arxml_path

SHARED_TEMPLATE = "arxml/shared_42.arxml.j2"
SWC_TEMPLATE = "arxml/swc_42.arxml.j2"
COMPOSITION_TEMPLATE = "arxml/composition_42.arxml.j2"
SYSTEM_TEMPLATE = "arxml/system_42.arxml.j2"
MONOLITHIC_TEMPLATE = "arxml/all_42.arxml.j2"
AUTOSAR_XML_NAMESPACE = "http://autosar.org/schema/r4.0"
XSI_XML_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"


@dataclass(frozen=True)
class InputPatternExpansion:
    pattern: str
    matched_files: List[Path]


@dataclass(frozen=True)
class ExportInputSummary:
    base_types_file: Optional[Path]
    implementation_types_file: Optional[Path]
    application_types_file: Optional[Path]
    unit_patterns: List[InputPatternExpansion]
    compu_method_patterns: List[InputPatternExpansion]
    mode_declaration_group_patterns: List[InputPatternExpansion]
    interface_patterns: List[InputPatternExpansion]
    swc_patterns: List[InputPatternExpansion]
    subcomposition_patterns: List[InputPatternExpansion]
    system_file: Optional[Path]


@dataclass(frozen=True)
class ExportModelSummary:
    datatypes_count: int
    mode_declaration_groups_count: int
    interfaces_count: int
    sr_interfaces_count: int
    cs_interfaces_count: int
    ms_interfaces_count: int
    swcs_count: int
    subcompositions_count: int
    instances_count: int
    connectors_count: int


@dataclass(frozen=True)
class OutputArtifact:
    path: Path
    size_bytes: int


@dataclass(frozen=True)
class ExportReport:
    project_path: Optional[Path]
    autosar_version: str
    layout: str
    template_dir: Path
    templates: Dict[str, str]
    input_summary: Optional[ExportInputSummary]
    model_summary: ExportModelSummary
    timings_ms: Dict[str, float]
    outputs: List[OutputArtifact]


@dataclass(frozen=True)
class ArxmlPortRef:
    dest: str
    ref: str


@dataclass(frozen=True)
class ArxmlPrototypePortRef:
    context_component_ref: str
    port: ArxmlPortRef


@dataclass(frozen=True)
class ArxmlAssemblyConnector:
    short_name: str
    provider: ArxmlPrototypePortRef
    requester: ArxmlPrototypePortRef


@dataclass(frozen=True)
class ArxmlDelegationConnector:
    short_name: str
    inner: ArxmlPrototypePortRef
    outer: ArxmlPortRef


@dataclass(frozen=True)
class SrPortComSpecMetadata:
    data_element_name: str
    data_element_ref: str
    unit_ref: str | None = None


@dataclass(frozen=True)
class CsOperationComSpecMetadata:
    operation_name: str
    operation_ref: str


@dataclass(frozen=True)
class ArxmlDisabledModeIref:
    context_port_ref: str
    context_mode_declaration_group_prototype_ref: str
    target_mode_declaration_ref: str


CompositionOwnerKind = Literal["component_type", "root_system"]


@dataclass(frozen=True)
class CompositionArxmlContext:
    owner_path: str

    def component_prototype_ref(self, prototype_name: str) -> str:
        return join_arxml_path(self.owner_path, prototype_name)

    def composition_outer_port_ref(self, port_name: str) -> str:
        return join_arxml_path(self.owner_path, port_name)


def _env(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("xml", "arxml", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


ET.register_namespace("", AUTOSAR_XML_NAMESPACE)
ET.register_namespace("xsi", XSI_XML_NAMESPACE)


def _pretty_print_xml(xml: str) -> str:
    root = ET.fromstring(xml)
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode", short_empty_elements=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


def _split_interfaces(project: Project):
    sr = [i for i in project.interfaces if i.type == "senderReceiver"]
    cs = [i for i in project.interfaces if i.type == "clientServer"]
    ms = [i for i in project.interfaces if i.type == "modeSwitch"]
    sr = sorted(sr, key=lambda x: x.name)
    cs = sorted(cs, key=lambda x: x.name)
    ms = sorted(ms, key=lambda x: x.name)
    return sr, cs, ms


def _connection_sort_key(conn: Connection) -> tuple[str, str, str, str]:
    return (
        conn.from_instance,
        conn.from_port,
        conn.to_instance,
        conn.to_port,
    )


def _sort_compu_method(compu_method: CompuMethod) -> CompuMethod:
    return replace(
        compu_method,
        entries=sorted(compu_method.entries, key=lambda entry: (entry.value, entry.label)),
    )


def _sort_operation(operation: Operation) -> Operation:
    # Preserve authored argument order because it defines the exported signature.
    return replace(
        operation,
        arguments=list(operation.arguments),
        possibleErrors=sorted(
            operation.possibleErrors,
            key=lambda err: (
                err.name,
                -1 if err.code is None else err.code,
            ),
        ),
    )


def _sort_interface(interface: Interface) -> Interface:
    if interface.type == "senderReceiver":
        return replace(
            interface,
            dataElements=sorted(interface.dataElements or [], key=lambda data_element: data_element.name),
        )

    operations = sorted((interface.operations or []), key=lambda operation: operation.name)
    return replace(interface, operations=[_sort_operation(operation) for operation in operations])


def _sort_mode_declaration_group(group: ModeDeclarationGroup) -> ModeDeclarationGroup:
    # Preserve authored mode order because MODE-DECLARATION-GROUP uses explicit ordering.
    return replace(group, modes=list(group.modes))


def _collect_interface_errors(interface: Interface) -> list[object]:
    unique_errors: dict[str, object] = {}
    for operation in interface.operations or []:
        for error in operation.possibleErrors:
            unique_errors.setdefault(error.name, error)
    return list(unique_errors.values())


def _sort_runnable(runnable: Runnable) -> Runnable:
    return replace(
        runnable,
        reads=sorted(runnable.reads, key=lambda access: (access.port, access.dataElement)),
        writes=sorted(runnable.writes, key=lambda access: (access.port, access.dataElement)),
        calls=sorted(
            runnable.calls,
            key=lambda call: (
                call.port,
                call.operation,
                -1 if call.timeoutMs is None else call.timeoutMs,
            ),
        ),
        operationInvokedEvents=sorted(
            runnable.operationInvokedEvents,
            key=lambda event: (event.port, event.operation),
        ),
        dataReceiveEvents=sorted(
            runnable.dataReceiveEvents,
            key=lambda event: (event.port, event.dataElement),
        ),
        modeSwitchEvents=sorted(
            runnable.modeSwitchEvents,
            key=lambda event: (event.port, event.mode),
        ),
        modeConditions=sorted(
            runnable.modeConditions,
            key=lambda condition: (condition.port, condition.mode),
        ),
        raisesErrors=sorted(
            runnable.raisesErrors,
            key=lambda raised_error: (raised_error.operation, raised_error.error),
        ),
    )


def _sort_swc(swc: Swc) -> Swc:
    return replace(
        swc,
        ports=sorted(swc.ports, key=lambda port: port.name),
        runnables=sorted(
            (_sort_runnable(runnable) for runnable in swc.runnables),
            key=lambda runnable: runnable.name,
        ),
    )


def _delegation_sort_key(conn: DelegationConnector) -> tuple[str, str, str]:
    return (
        conn.outer_port,
        conn.inner_instance,
        conn.inner_port,
    )


def _sort_subcomposition(subcomposition: SubcompositionType) -> SubcompositionType:
    return replace(
        subcomposition,
        ports=sorted(subcomposition.ports, key=lambda port: port.name),
        components=sorted(subcomposition.components, key=lambda component: component.name),
        connectors=sorted(subcomposition.connectors, key=_connection_sort_key),
        delegationConnectors=sorted(subcomposition.delegationConnectors, key=_delegation_sort_key),
    )


def _component_type_dests(project: Project, resolver: ArxmlPathResolver) -> Dict[str, str]:
    dests = {swc.name: resolver.component_type_dest(swc.name) for swc in project.swcs}
    dests.update({subcomposition.name: resolver.component_type_dest(subcomposition.name) for subcomposition in project.subcompositions})
    return dests


def _component_type_refs(project: Project, resolver: ArxmlPathResolver) -> Dict[str, str]:
    refs = {swc.name: resolver.component_type_ref(swc.name) for swc in project.swcs}
    refs.update({subcomposition.name: resolver.component_type_ref(subcomposition.name) for subcomposition in project.subcompositions})
    return refs


def _build_sr_port_comspec_metadata(project: Project, swc: Swc, resolver: ArxmlPathResolver) -> dict[str, SrPortComSpecMetadata]:
    interfaces_by_name = {interface.name: interface for interface in project.interfaces}
    application_types_by_name = {data_type.name: data_type for data_type in project.applicationDataTypes}
    metadata: dict[str, SrPortComSpecMetadata] = {}
    for port in swc.ports:
        if port.interfaceType != "senderReceiver" or port.comSpec is None:
            continue
        interface = interfaces_by_name.get(port.interfaceRef)
        if interface is None or not interface.dataElements:
            continue
        data_element = interface.dataElements[0]
        application_type = application_types_by_name.get(data_element.typeRef)
        metadata[port.name] = SrPortComSpecMetadata(
            data_element_name=data_element.name,
            data_element_ref=resolver.interface_data_element(interface.name, data_element.name),
            unit_ref=application_type.unitRef if application_type is not None else None,
        )
    return metadata


def _build_cs_port_comspec_metadata(project: Project, swc: Swc, resolver: ArxmlPathResolver) -> dict[str, list[CsOperationComSpecMetadata]]:
    interfaces_by_name = {interface.name: interface for interface in project.interfaces}
    metadata: dict[str, list[CsOperationComSpecMetadata]] = {}
    for port in swc.ports:
        if port.interfaceType != "clientServer" or port.direction != "requires":
            continue
        interface = interfaces_by_name.get(port.interfaceRef)
        if interface is None or not interface.operations:
            continue
        metadata[port.name] = [
            CsOperationComSpecMetadata(
                operation_name=operation.name,
                operation_ref=resolver.interface_operation(interface.name, operation.name),
            )
            for operation in interface.operations
        ]
    return metadata


def _build_runnable_disabled_mode_irefs(project: Project, swc: Swc, resolver: ArxmlPathResolver) -> dict[str, list[ArxmlDisabledModeIref]]:
    ports_by_name = {port.name: port for port in swc.ports}
    mode_groups_by_name = {group.name: group for group in project.modeDeclarationGroups}
    runnable_disabled_mode_irefs: dict[str, list[ArxmlDisabledModeIref]] = {}

    for runnable in swc.runnables:
        allowed_modes_by_port: dict[str, set[str]] = {}
        for condition in runnable.modeConditions:
            allowed_modes_by_port.setdefault(condition.port, set()).add(condition.mode)

        disabled_mode_irefs: list[ArxmlDisabledModeIref] = []
        for port_name in sorted(allowed_modes_by_port):
            port = ports_by_name.get(port_name)
            if port is None or not port.modeGroupRef:
                continue

            mode_group = mode_groups_by_name.get(port.modeGroupRef)
            if mode_group is None:
                continue

            allowed_modes = allowed_modes_by_port[port_name]
            for mode in mode_group.modes:
                if mode.name in allowed_modes:
                    continue
                disabled_mode_irefs.append(
                    ArxmlDisabledModeIref(
                        context_port_ref=resolver.swc_port(swc.name, port.name),
                        context_mode_declaration_group_prototype_ref=resolver.interface_mode_group_prototype(port.interfaceRef),
                        target_mode_declaration_ref=resolver.mode_declaration(mode_group.name, mode.name),
                    )
                )

        runnable_disabled_mode_irefs[runnable.name] = sorted(
            disabled_mode_irefs,
            key=lambda item: (
                item.context_port_ref,
                item.context_mode_declaration_group_prototype_ref,
                item.target_mode_declaration_ref,
            ),
        )

    return runnable_disabled_mode_irefs


def _component_type_port_ref(
    resolver: ArxmlPathResolver,
    component_type_name: str,
    port_name: str,
    direction: str,
) -> ArxmlPortRef:
    if direction == "provides":
        dest = "P-PORT-PROTOTYPE"
    elif direction == "requires":
        dest = "R-PORT-PROTOTYPE"
    else:
        raise ValueError(f"Unsupported port direction: {direction}")
    return ArxmlPortRef(
        dest=dest,
        ref=join_arxml_path(resolver.component_type_ref(component_type_name), port_name),
    )


def _component_port_by_name(component_ports: list[object]) -> dict[str, object]:
    return {port.name: port for port in component_ports}


def _build_component_ports_by_type(project: Project) -> dict[str, dict[str, object]]:
    ports_by_type: dict[str, dict[str, object]] = {}
    for swc in project.swcs:
        ports_by_type[swc.name] = _component_port_by_name(swc.ports)
    for subcomposition in project.subcompositions:
        ports_by_type[subcomposition.name] = _component_port_by_name(subcomposition.ports)
    return ports_by_type


def _resolve_prototype_port_ref(
    *,
    context: CompositionArxmlContext,
    resolver: ArxmlPathResolver,
    instance_by_name: dict[str, ComponentPrototype],
    component_ports_by_type: dict[str, dict[str, object]],
    instance_name: str,
    port_name: str,
    expected_direction: str,
) -> ArxmlPrototypePortRef:
    instance = instance_by_name.get(instance_name)
    if instance is None:
        raise ValueError(f"Unknown component prototype '{instance_name}' in composition '{context.owner_name}'.")

    type_ports = component_ports_by_type.get(instance.typeRef)
    if type_ports is None:
        raise ValueError(f"Unknown component type '{instance.typeRef}' for prototype '{instance_name}'.")

    port = type_ports.get(port_name)
    if port is None:
        raise ValueError(f"Unknown port '{port_name}' on component type '{instance.typeRef}'.")
    if port.direction != expected_direction:
        raise ValueError(
            f"Port '{instance.typeRef}.{port_name}' has direction '{port.direction}', expected '{expected_direction}'."
        )

    return ArxmlPrototypePortRef(
        context_component_ref=context.component_prototype_ref(instance_name),
        port=_component_type_port_ref(
            resolver,
            component_type_name=instance.typeRef,
            port_name=port_name,
            direction=port.direction,
        ),
    )


def _safe_filename_stem(value: Optional[str], fallback: str) -> str:
    candidate = (value or "").strip()
    candidate = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate)
    candidate = candidate.strip("._-")
    return candidate or fallback


def _shared_output_name(project: Project) -> str:
    stem = _safe_filename_stem(
        project.rootPackage or project.system.name or project.system.composition.name,
        "Shared",
    )
    return f"{stem}_SharedTypes.arxml"


def _system_output_name(project: Project) -> str:
    stem = _safe_filename_stem(
        project.system.name or project.system.composition.name or project.rootPackage,
        "system",
    )
    return f"{stem}.arxml"


def _sort_project_for_export(project: Project) -> Project:
    implementation_types = []
    for implementation_type in sorted(project.implementationDataTypes, key=lambda data_type: data_type.name):
        # Preserve authored field order because structure layout can be semantically meaningful.
        implementation_types.append(replace(implementation_type, fields=list(implementation_type.fields)))

    return replace(
        project,
        baseTypes=sorted(project.baseTypes, key=lambda data_type: data_type.name),
        implementationDataTypes=implementation_types,
        applicationDataTypes=sorted(project.applicationDataTypes, key=lambda data_type: data_type.name),
        units=sorted(project.units, key=lambda unit: unit.name),
        compuMethods=sorted(
            (_sort_compu_method(compu_method) for compu_method in project.compuMethods),
            key=lambda compu_method: compu_method.name,
        ),
        modeDeclarationGroups=sorted(
            (_sort_mode_declaration_group(group) for group in project.modeDeclarationGroups),
            key=lambda group: group.name,
        ),
        interfaces=sorted((_sort_interface(interface) for interface in project.interfaces), key=lambda interface: interface.name),
        swcs=sorted((_sort_swc(swc) for swc in project.swcs), key=lambda swc: swc.name),
        subcompositions=sorted(
            (_sort_subcomposition(subcomposition) for subcomposition in project.subcompositions),
            key=lambda subcomposition: subcomposition.name,
        ),
        system=replace(
            project.system,
            composition=replace(
                project.system.composition,
                components=sorted(project.system.composition.components, key=lambda component: component.name),
                connectors=sorted(project.system.composition.connectors, key=_connection_sort_key),
            ),
        ),
    )


def _model_summary(project: Project) -> ExportModelSummary:
    sr, cs, ms = _split_interfaces(project)
    return ExportModelSummary(
        datatypes_count=(
            len(project.baseTypes)
            + len(project.implementationDataTypes)
            + len(project.applicationDataTypes)
            + len(project.units)
            + len(project.compuMethods)
        ),
        mode_declaration_groups_count=len(project.modeDeclarationGroups),
        interfaces_count=len(project.interfaces),
        sr_interfaces_count=len(sr),
        cs_interfaces_count=len(cs),
        ms_interfaces_count=len(ms),
        swcs_count=len(project.swcs),
        subcompositions_count=len(project.subcompositions),
        instances_count=len(project.system.composition.components),
        connectors_count=len(project.system.composition.connectors),
    )


def _build_connections_for_composition(
    project: Project,
    context: CompositionArxmlContext,
    resolver: ArxmlPathResolver,
    components: List[ComponentPrototype],
    connectors: List[Connection],
) -> List[ArxmlAssemblyConnector]:
    swc_by_name = {swc.name: swc for swc in project.swcs}
    instance_by_name = {instance.name: instance for instance in components}
    component_ports_by_type = _build_component_ports_by_type(project)

    def _is_sender_receiver(conn) -> bool:
        from_instance = instance_by_name.get(conn.from_instance)
        if from_instance is None:
            return False
        from_swc = swc_by_name.get(from_instance.typeRef)
        if from_swc is None:
            return False
        from_port = next((port for port in from_swc.ports if port.name == conn.from_port), None)
        if from_port is None:
            return False
        return from_port.interfaceType == "senderReceiver"

    unique_connectors = []
    seen_port_pairs: set[tuple[str, str, str, str]] = set()
    for connector in connectors:
        if _is_sender_receiver(connector):
            if connector.port_pair_key in seen_port_pairs:
                continue
            seen_port_pairs.add(connector.port_pair_key)
        else:
            if connector.identity_key in seen_port_pairs:
                continue
            seen_port_pairs.add(connector.identity_key)
        unique_connectors.append(connector)

    return [
        ArxmlAssemblyConnector(
            short_name=f"Conn_{idx}",
            provider=_resolve_prototype_port_ref(
                context=context,
                resolver=resolver,
                instance_by_name=instance_by_name,
                component_ports_by_type=component_ports_by_type,
                instance_name=c.from_instance,
                port_name=c.from_port,
                expected_direction="provides",
            ),
            requester=_resolve_prototype_port_ref(
                context=context,
                resolver=resolver,
                instance_by_name=instance_by_name,
                component_ports_by_type=component_ports_by_type,
                instance_name=c.to_instance,
                port_name=c.to_port,
                expected_direction="requires",
            ),
        )
        for idx, c in enumerate(unique_connectors, start=1)
    ]


def _build_connections(project: Project) -> List[ArxmlAssemblyConnector]:
    resolver = ArxmlPathResolver(project)
    return _build_connections_for_composition(
        project,
        CompositionArxmlContext(
            owner_path=resolver.system_composition(project.system.composition.name),
        ),
        resolver,
        project.system.composition.components,
        project.system.composition.connectors,
    )


def _type_trefs(project: Project, resolver: ArxmlPathResolver) -> Dict[str, object]:
    refs: Dict[str, object] = {}
    for data_type in project.baseTypes:
        refs[data_type.name] = resolver.type_ref_target(data_type.name)
    for data_type in project.implementationDataTypes:
        refs[data_type.name] = resolver.type_ref_target(data_type.name)
    for data_type in project.applicationDataTypes:
        refs[data_type.name] = resolver.type_ref_target(data_type.name)
    return refs


def _build_delegation_connectors(project: Project, subcomposition: SubcompositionType) -> List[ArxmlDelegationConnector]:
    resolver = ArxmlPathResolver(project)
    context = CompositionArxmlContext(
        owner_path=resolver.composition(subcomposition.name),
    )
    instance_by_name = {instance.name: instance for instance in subcomposition.components}
    component_ports_by_type = _build_component_ports_by_type(project)
    outer_ports_by_name = {port.name: port for port in subcomposition.ports}
    return [
        ArxmlDelegationConnector(
            short_name=f"DelegationConn_{idx}",
            inner=_resolve_prototype_port_ref(
                context=context,
                resolver=resolver,
                instance_by_name=instance_by_name,
                component_ports_by_type=component_ports_by_type,
                instance_name=connector.inner_instance,
                port_name=connector.inner_port,
                expected_direction=outer_ports_by_name[connector.outer_port].direction,
            ),
            outer=_component_type_port_ref(
                resolver,
                component_type_name=subcomposition.name,
                port_name=connector.outer_port,
                direction=outer_ports_by_name[connector.outer_port].direction,
            ),
        )
        for idx, connector in enumerate(subcomposition.delegationConnectors, start=1)
    ]


def render_shared(project: Project, template_dir: Path, template_name: str = SHARED_TEMPLATE) -> str:
    env = _env(template_dir)
    tpl = env.get_template(template_name)
    project = _sort_project_for_export(project)
    resolver = ArxmlPathResolver(project)
    sr, cs, ms = _split_interfaces(project)
    return _pretty_print_xml(
        tpl.render(
            root_pkg=project.rootPackage,
            package_tree=build_package_tree(
                resolver,
                base_types=project.baseTypes,
                implementation_data_types=project.implementationDataTypes,
                application_data_types=project.applicationDataTypes,
                units=project.units,
                compu_methods=project.compuMethods,
                mode_declaration_groups=project.modeDeclarationGroups,
                interfaces=project.interfaces,
            ),
            paths=resolver,
            type_trefs=_type_trefs(project, resolver),
            cs_interface_errors={interface.name: _collect_interface_errors(interface) for interface in cs},
        )
    )


def render_swc(project: Project, swc: Swc, template_dir: Path, template_name: str = SWC_TEMPLATE) -> str:
    env = _env(template_dir)
    tpl = env.get_template(template_name)
    project = _sort_project_for_export(project)
    swc = next(candidate for candidate in project.swcs if candidate.name == swc.name)
    resolver = ArxmlPathResolver(project)
    return _pretty_print_xml(
        tpl.render(
            root_pkg=project.rootPackage,
            package_tree=build_package_tree(resolver, swcs=[swc]),
            paths=resolver,
            type_trefs=_type_trefs(project, resolver),
            swc_sr_port_metadata={swc.name: _build_sr_port_comspec_metadata(project, swc, resolver)},
            swc_cs_port_metadata={swc.name: _build_cs_port_comspec_metadata(project, swc, resolver)},
            swc_runnable_disabled_mode_irefs={swc.name: _build_runnable_disabled_mode_irefs(project, swc, resolver)},
            cs_interface_errors={},
        )
    )


def render_composition_type(
    project: Project,
    subcomposition: SubcompositionType,
    template_dir: Path,
    template_name: str = COMPOSITION_TEMPLATE,
) -> str:
    env = _env(template_dir)
    tpl = env.get_template(template_name)
    project = _sort_project_for_export(project)
    subcomposition = next(candidate for candidate in project.subcompositions if candidate.name == subcomposition.name)
    resolver = ArxmlPathResolver(project)
    component_type_dests = _component_type_dests(project, resolver)
    component_type_refs = _component_type_refs(project, resolver)
    composition_model = {
        "name": subcomposition.name,
        "description": subcomposition.description,
        "ports": subcomposition.ports,
        "components": subcomposition.components,
        "connections": _build_connections_for_composition(
            project,
            CompositionArxmlContext(owner_path=resolver.composition(subcomposition.name)),
            resolver,
            subcomposition.components,
            subcomposition.connectors,
        ),
        "delegation_connectors": _build_delegation_connectors(project, subcomposition),
    }
    return _pretty_print_xml(
        tpl.render(
            root_pkg=project.rootPackage,
            package_tree=build_package_tree(resolver, subcompositions=[subcomposition]),
            paths=resolver,
            type_trefs=_type_trefs(project, resolver),
            subcomposition_models={subcomposition.name: composition_model},
            component_type_dests=component_type_dests,
            component_type_refs=component_type_refs,
            cs_interface_errors={},
        )
    )


def render_system(project: Project, template_dir: Path, template_name: str = SYSTEM_TEMPLATE) -> str:
    env = _env(template_dir)
    tpl = env.get_template(template_name)
    project = _sort_project_for_export(project)
    resolver = ArxmlPathResolver(project)
    connections = _build_connections(project)
    component_type_dests = _component_type_dests(project, resolver)
    component_type_refs = _component_type_refs(project, resolver)
    return _pretty_print_xml(
        tpl.render(
            root_pkg=project.rootPackage,
            package_tree=build_package_tree(resolver, systems=[project.system]),
            paths=resolver,
            type_trefs=_type_trefs(project, resolver),
            system_models={
                project.system.name: {
                    "system_name": project.system.name,
                    "composition_name": project.system.composition.name,
                    "components": project.system.composition.components,
                    "connections": connections,
                }
            },
            component_type_dests=component_type_dests,
            component_type_refs=component_type_refs,
            cs_interface_errors={},
        )
    )


def write_outputs_with_report(
    project: Project,
    template_dir: Path,
    out: Path,
    split_by_swc: bool,
    *,
    project_path: Optional[Path] = None,
    autosar_version: Optional[str] = None,
    input_summary: Optional[ExportInputSummary] = None,
    stage_timings_ms: Optional[Dict[str, float]] = None,
) -> ExportReport:
    project = _sort_project_for_export(project)
    timings_ms = dict(stage_timings_ms or {})
    outputs: List[OutputArtifact] = []

    render_started = perf_counter()
    if not split_by_swc:
        env = _env(template_dir)
        tpl = env.get_template(MONOLITHIC_TEMPLATE)
        resolver = ArxmlPathResolver(project)
        swcs = project.swcs
        sr, cs, ms = _split_interfaces(project)
        connections = _build_connections(project)
        component_type_dests = _component_type_dests(project, resolver)
        component_type_refs = _component_type_refs(project, resolver)
        subcompositions = [
            {
                "name": subcomposition.name,
                "description": subcomposition.description,
                "ports": subcomposition.ports,
                "components": subcomposition.components,
                "connections": _build_connections_for_composition(
                    project,
                    CompositionArxmlContext(owner_path=resolver.composition(subcomposition.name)),
                    resolver,
                    subcomposition.components,
                    subcomposition.connectors,
                ),
                "delegation_connectors": _build_delegation_connectors(project, subcomposition),
            }
            for subcomposition in project.subcompositions
        ]
        rendered = {
            out: _pretty_print_xml(
                tpl.render(
                    root_pkg=project.rootPackage,
                    package_tree=build_package_tree(
                        resolver,
                        base_types=project.baseTypes,
                        implementation_data_types=project.implementationDataTypes,
                        application_data_types=project.applicationDataTypes,
                        units=project.units,
                        compu_methods=project.compuMethods,
                        mode_declaration_groups=project.modeDeclarationGroups,
                        interfaces=project.interfaces,
                        swcs=project.swcs,
                        subcompositions=project.subcompositions,
                        systems=[project.system],
                    ),
                    paths=resolver,
                    type_trefs=_type_trefs(project, resolver),
                    cs_interface_errors={interface.name: _collect_interface_errors(interface) for interface in cs},
                    swc_sr_port_metadata={swc.name: _build_sr_port_comspec_metadata(project, swc, resolver) for swc in swcs},
                    swc_cs_port_metadata={swc.name: _build_cs_port_comspec_metadata(project, swc, resolver) for swc in swcs},
                    swc_runnable_disabled_mode_irefs={
                        swc.name: _build_runnable_disabled_mode_irefs(project, swc, resolver) for swc in swcs
                    },
                    subcomposition_models={item["name"]: item for item in subcompositions},
                    system_models={
                        project.system.name: {
                            "system_name": project.system.name,
                            "composition_name": project.system.composition.name,
                            "components": project.system.composition.components,
                            "connections": connections,
                        }
                    },
                    component_type_dests=component_type_dests,
                    component_type_refs=component_type_refs,
                )
            )
        }
        layout = "monolithic"
        templates = {"monolithic": MONOLITHIC_TEMPLATE}
    else:
        rendered = {}
        target_dir = out
        rendered[target_dir / _shared_output_name(project)] = render_shared(project, template_dir, template_name=SHARED_TEMPLATE)
        for swc in project.swcs:
            rendered[target_dir / f"{swc.name}.arxml"] = render_swc(project, swc=swc, template_dir=template_dir, template_name=SWC_TEMPLATE)
        for subcomposition in project.subcompositions:
            rendered[target_dir / f"{subcomposition.name}.arxml"] = render_composition_type(
                project,
                subcomposition=subcomposition,
                template_dir=template_dir,
                template_name=COMPOSITION_TEMPLATE,
            )
        rendered[target_dir / _system_output_name(project)] = render_system(project, template_dir, template_name=SYSTEM_TEMPLATE)
        layout = "split-by-swc"
        templates = {
            "shared": SHARED_TEMPLATE,
            "swc": SWC_TEMPLATE,
            "composition": COMPOSITION_TEMPLATE,
            "system": SYSTEM_TEMPLATE,
        }
    timings_ms["rendering"] = (perf_counter() - render_started) * 1000.0

    write_started = perf_counter()
    if not split_by_swc:
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        out.mkdir(parents=True, exist_ok=True)

    for path, xml in rendered.items():
        path.write_text(xml, encoding="utf-8")
        outputs.append(OutputArtifact(path=path, size_bytes=path.stat().st_size))
    timings_ms["writing"] = (perf_counter() - write_started) * 1000.0

    return ExportReport(
        project_path=project_path,
        autosar_version=autosar_version or project.autosar_version,
        layout=layout,
        template_dir=template_dir,
        templates=templates,
        input_summary=input_summary,
        model_summary=_model_summary(project),
        timings_ms=timings_ms,
        outputs=outputs,
    )


def write_outputs(project: Project, template_dir: Path, out: Path, split_by_swc: bool) -> List[Path]:
    report = write_outputs_with_report(project, template_dir=template_dir, out=out, split_by_swc=split_by_swc)
    return [artifact.path for artifact in report.outputs]
