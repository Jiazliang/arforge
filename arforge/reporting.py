from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .exporter import _sort_project_for_export
from .model import ComponentPrototype, Connection, DelegationConnector, Port, Project, SubcompositionType, Swc
from .semantic_validation import ValidationContext


REPORT_TEMPLATE = "project_report.md.j2"


def _env(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def _connector_sort_key(connector: Connection) -> tuple[str, str, str, str, str, str]:
    return (
        connector.from_instance,
        connector.from_port,
        connector.to_instance,
        connector.to_port,
        connector.dataElement or "",
        connector.operation or "",
    )


def _delegation_sort_key(connector: DelegationConnector) -> tuple[str, str, str]:
    return (
        connector.outer_port,
        connector.inner_instance,
        connector.inner_port,
    )


def _type_kind(project: Project, type_name: str) -> str:
    if any(swc.name == type_name for swc in project.swcs):
        return "swc"
    if any(subcomposition.name == type_name for subcomposition in project.subcompositions):
        return "subcomposition"
    return "unknown"


def _kind_label(kind: str) -> str:
    return {
        "swc": "SWC",
        "subcomposition": "Subcomposition",
        "unknown": "Unknown",
    }.get(kind, kind)


def _interface_counts(project: Project) -> dict[str, int]:
    return {
        "sender_receiver": len([interface for interface in project.interfaces if interface.type == "senderReceiver"]),
        "client_server": len([interface for interface in project.interfaces if interface.type == "clientServer"]),
        "mode_switch": len([interface for interface in project.interfaces if interface.type == "modeSwitch"]),
    }


def _component_ports_by_type(project: Project) -> dict[str, list[Port]]:
    ports_by_type: dict[str, list[Port]] = {}
    for swc in project.swcs:
        ports_by_type[swc.name] = list(swc.ports)
    for subcomposition in project.subcompositions:
        ports_by_type[subcomposition.name] = list(subcomposition.ports)
    return ports_by_type


def _normalize_connector_label(connector: Connection) -> str:
    selector = ""
    if connector.dataElement:
        selector = f" [{connector.dataElement}]"
    elif connector.operation:
        selector = f" [{connector.operation}]"
    return f"{connector.from_instance}.{connector.from_port} -> {connector.to_instance}.{connector.to_port}{selector}"


def _normalize_delegation_label(connector: DelegationConnector) -> str:
    return f"{connector.inner_instance}.{connector.inner_port} => {connector.outer_port}"


def _communication_categories(project: Project) -> list[str]:
    counts = _interface_counts(project)
    categories: list[str] = []
    if counts["sender_receiver"] > 0:
        categories.append("Sender-Receiver")
    if counts["client_server"] > 0:
        categories.append("Client-Server")
    if counts["mode_switch"] > 0:
        categories.append("Mode-Switch")
    return categories


def _count_phrase(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


def _summarize_instance(project: Project, instance: ComponentPrototype) -> dict[str, Any]:
    kind = _type_kind(project, instance.typeRef)
    port_count = 0
    runnable_count = 0
    inner_component_count = 0
    if kind == "swc":
        swc = next((swc for swc in project.swcs if swc.name == instance.typeRef), None)
        if swc is not None:
            port_count = len(swc.ports)
            runnable_count = len(swc.runnables)
    elif kind == "subcomposition":
        subcomposition = next((sub for sub in project.subcompositions if sub.name == instance.typeRef), None)
        if subcomposition is not None:
            port_count = len(subcomposition.ports)
            inner_component_count = len(subcomposition.components)
    return {
        "name": instance.name,
        "type_name": instance.typeRef,
        "kind": kind,
        "kind_label": _kind_label(kind),
        "description": instance.description,
        "port_count": port_count,
        "runnable_count": runnable_count,
        "inner_component_count": inner_component_count,
    }


def _build_top_level_architecture(project: Project) -> dict[str, Any]:
    composition = project.system.composition
    connectors = sorted(composition.connectors, key=_connector_sort_key)
    component_kinds = [_type_kind(project, component.typeRef) for component in composition.components]
    return {
        "system_name": project.system.name,
        "composition_name": composition.name,
        "description": composition.description or project.system.description,
        "components": [_summarize_instance(project, component) for component in composition.components],
        "connectors": [
            {
                "label": _normalize_connector_label(connector),
                "description": connector.description,
            }
            for connector in connectors
        ],
        "swc_instance_count": sum(1 for kind in component_kinds if kind == "swc"),
        "subcomposition_instance_count": sum(1 for kind in component_kinds if kind == "subcomposition"),
    }


def _build_subcomposition_summaries(project: Project) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for subcomposition in project.subcompositions:
        connectors = sorted(subcomposition.connectors, key=_connector_sort_key)
        delegations = sorted(subcomposition.delegationConnectors, key=_delegation_sort_key)
        summaries.append(
            {
                "name": subcomposition.name,
                "description": subcomposition.description,
                "ports": [
                    {
                        "name": port.name,
                        "direction": port.direction,
                        "interface_type": port.interfaceType,
                        "interface_ref": port.interfaceRef,
                    }
                    for port in subcomposition.ports
                ],
                "components": [_summarize_instance(project, component) for component in subcomposition.components],
                "assembly_connectors": [
                    {
                        "label": _normalize_connector_label(connector),
                        "description": connector.description,
                    }
                    for connector in connectors
                ],
                "delegation_connectors": [
                    {
                        "label": _normalize_delegation_label(connector),
                        "description": connector.description,
                    }
                    for connector in delegations
                ],
            }
        )
    return summaries


def _build_interface_summary(project: Project) -> dict[str, list[dict[str, Any]]]:
    interfaces_by_type: dict[str, list[dict[str, Any]]] = {
        "sender_receiver": [],
        "client_server": [],
        "mode_switch": [],
    }
    for interface in project.interfaces:
        if interface.type == "senderReceiver":
            interfaces_by_type["sender_receiver"].append(
                {
                    "name": interface.name,
                    "description": interface.description,
                    "data_elements": [data_element.name for data_element in interface.dataElements or []],
                }
            )
        elif interface.type == "clientServer":
            interfaces_by_type["client_server"].append(
                {
                    "name": interface.name,
                    "description": interface.description,
                    "operations": [operation.name for operation in interface.operations or []],
                }
            )
        elif interface.type == "modeSwitch":
            interfaces_by_type["mode_switch"].append(
                {
                    "name": interface.name,
                    "description": interface.description,
                    "mode_group_ref": interface.modeGroupRef,
                }
            )
    return interfaces_by_type


def _build_component_summary(project: Project) -> dict[str, list[dict[str, Any]]]:
    top_level_instances_by_type: dict[str, list[str]] = {}
    for component in project.system.composition.components:
        top_level_instances_by_type.setdefault(component.typeRef, []).append(component.name)

    subcomposition_usage_by_type: dict[str, list[str]] = {}
    for subcomposition in project.subcompositions:
        for component in subcomposition.components:
            subcomposition_usage_by_type.setdefault(component.typeRef, []).append(f"{subcomposition.name}.{component.name}")

    swcs: list[dict[str, Any]] = []
    for swc in project.swcs:
        cyclic_runnables = sorted(
            [runnable for runnable in swc.runnables if runnable.timingEventMs is not None],
            key=lambda runnable: (runnable.timingEventMs or -1, runnable.name),
        )
        swcs.append(
            {
                "name": swc.name,
                "category": swc.category,
                "description": swc.description,
                "port_count": len(swc.ports),
                "runnable_count": len(swc.runnables),
                "top_level_instances": sorted(top_level_instances_by_type.get(swc.name, [])),
                "nested_instances": sorted(subcomposition_usage_by_type.get(swc.name, [])),
                "ports": [
                    {
                        "name": port.name,
                        "direction": port.direction,
                        "interface_type": port.interfaceType,
                        "interface_ref": port.interfaceRef,
                    }
                    for port in swc.ports
                ],
                "cyclic_runnables": [
                    {
                        "name": runnable.name,
                        "period_ms": runnable.timingEventMs,
                    }
                    for runnable in cyclic_runnables
                ],
            }
        )

    return {
        "swcs": swcs,
        "subcompositions": _build_subcomposition_summaries(project),
    }


def _build_unconnected_scope(
    *,
    project: Project,
    scope_name: str,
    scope_kind: str,
    components: list[ComponentPrototype],
    connectors: list[Connection],
    delegation_connectors: list[DelegationConnector] | None = None,
) -> dict[str, Any] | None:
    ports_by_type = _component_ports_by_type(project)
    incoming: dict[tuple[str, str], int] = {}
    outgoing: dict[tuple[str, str], int] = {}

    for connector in connectors:
        outgoing[(connector.from_instance, connector.from_port)] = outgoing.get((connector.from_instance, connector.from_port), 0) + 1
        incoming[(connector.to_instance, connector.to_port)] = incoming.get((connector.to_instance, connector.to_port), 0) + 1

    for delegation in delegation_connectors or []:
        component = next((item for item in components if item.name == delegation.inner_instance), None)
        if component is None:
            continue
        ports = ports_by_type.get(component.typeRef, [])
        port = next((item for item in ports if item.name == delegation.inner_port), None)
        if port is None:
            continue
        key = (delegation.inner_instance, delegation.inner_port)
        if port.direction == "provides":
            outgoing[key] = outgoing.get(key, 0) + 1
        elif port.direction == "requires":
            incoming[key] = incoming.get(key, 0) + 1

    grouped_instances: list[dict[str, Any]] = []
    for component in components:
        ports = ports_by_type.get(component.typeRef, [])
        provides: list[dict[str, Any]] = []
        requires: list[dict[str, Any]] = []
        for port in ports:
            key = (component.name, port.name)
            if port.direction == "provides" and outgoing.get(key, 0) == 0:
                provides.append(
                    {
                        "name": port.name,
                        "interface_type": port.interfaceType,
                        "interface_ref": port.interfaceRef,
                    }
                )
            if port.direction == "requires" and incoming.get(key, 0) == 0:
                requires.append(
                    {
                        "name": port.name,
                        "interface_type": port.interfaceType,
                        "interface_ref": port.interfaceRef,
                    }
                )
        if provides or requires:
            grouped_instances.append(
                {
                    "instance_name": component.name,
                    "type_name": component.typeRef,
                    "kind": _type_kind(project, component.typeRef),
                    "kind_label": _kind_label(_type_kind(project, component.typeRef)),
                    "provides": provides,
                    "requires": requires,
                }
            )

    if not grouped_instances:
        return None

    return {
        "scope_name": scope_name,
        "scope_kind": scope_kind,
        "instances": grouped_instances,
    }


def _build_unconnected_ports_summary(project: Project) -> list[dict[str, Any]]:
    scopes: list[dict[str, Any]] = []
    root_scope = _build_unconnected_scope(
        project=project,
        scope_name=project.system.name,
        scope_kind="top-level system",
        components=list(project.system.composition.components),
        connectors=list(project.system.composition.connectors),
    )
    if root_scope is not None:
        scopes.append(root_scope)

    for subcomposition in project.subcompositions:
        scope = _build_unconnected_scope(
            project=project,
            scope_name=subcomposition.name,
            scope_kind="subcomposition",
            components=list(subcomposition.components),
            connectors=list(subcomposition.connectors),
            delegation_connectors=list(subcomposition.delegationConnectors),
        )
        if scope is not None:
            scopes.append(scope)

    return scopes


def _build_unused_elements_summary(project: Project, ctx: ValidationContext) -> dict[str, Any]:
    unused_ports_by_swc: list[dict[str, Any]] = []
    for swc in project.swcs:
        unused_ports: list[dict[str, str]] = []
        mode_switch_requires_analysis = {
            analysis.port.name: analysis
            for analysis in ctx.iter_mode_switch_requires_port_analysis(swc.name)
        }
        for declared_usage in ctx.iter_declared_port_usage(swc.name):
            port = declared_usage.port
            usage = declared_usage.usage
            is_unused = False
            if port.interfaceType == "senderReceiver":
                is_unused = (port.direction == "provides" and not usage.writes) or (
                    port.direction == "requires" and not usage.reads and not usage.data_receive_events
                )
            elif port.interfaceType == "clientServer":
                is_unused = (port.direction == "requires" and not usage.calls) or (
                    port.direction == "provides" and not usage.operation_invoked_events
                )
            elif port.interfaceType == "modeSwitch" and port.direction == "requires":
                analysis = mode_switch_requires_analysis.get(port.name)
                is_unused = analysis is not None and not analysis.usage.mode_switch_events
            if is_unused:
                unused_ports.append(
                    {
                        "name": port.name,
                        "direction": port.direction,
                        "interface_type": port.interfaceType,
                        "interface_ref": port.interfaceRef,
                    }
                )
        if unused_ports:
            unused_ports_by_swc.append(
                {
                    "swc_name": swc.name,
                    "ports": unused_ports,
                }
            )

    declared_interface_refs = sorted(
        {
            port.interfaceRef
            for swc in project.swcs
            for port in swc.ports
        }
        | {
            port.interfaceRef
            for subcomposition in project.subcompositions
            for port in subcomposition.ports
        }
    )
    unused_interfaces = [
        interface.name
        for interface in project.interfaces
        if interface.name not in declared_interface_refs
    ]
    unused_mode_groups = [
        group.name
        for group in project.modeDeclarationGroups
        if group.name not in ctx.referenced_mode_declaration_groups
    ]

    return {
        "unused_declared_ports": unused_ports_by_swc,
        "unused_interfaces": unused_interfaces,
        "unused_mode_groups": unused_mode_groups,
    }


def _is_pure_cyclic_runnable(runnable: Any) -> bool:
    return (
        runnable.timingEventMs is not None
        and not runnable.operationInvokedEvents
        and not runnable.dataReceiveEvents
        and not runnable.modeSwitchEvents
        and not runnable.initEvent
    )


def _build_scope_timing_relationships(
    *,
    scope_name: str,
    components: list[ComponentPrototype],
    connectors: list[Connection],
    swc_by_name: dict[str, Swc],
) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    instance_by_name = {component.name: component for component in components}
    seen: set[tuple[str, str, str, str, str, str, int, int]] = set()
    for connector in sorted(connectors, key=_connector_sort_key):
        provider_instance = instance_by_name.get(connector.from_instance)
        consumer_instance = instance_by_name.get(connector.to_instance)
        if provider_instance is None or consumer_instance is None:
            continue
        provider_swc = swc_by_name.get(provider_instance.typeRef)
        consumer_swc = swc_by_name.get(consumer_instance.typeRef)
        if provider_swc is None or consumer_swc is None:
            continue
        provider_port = next((port for port in provider_swc.ports if port.name == connector.from_port), None)
        consumer_port = next((port for port in consumer_swc.ports if port.name == connector.to_port), None)
        if provider_port is None or consumer_port is None:
            continue
        if provider_port.interfaceType != "senderReceiver" or consumer_port.interfaceType != "senderReceiver":
            continue
        provider_accesses = [
            (runnable.name, access.dataElement, runnable.timingEventMs)
            for runnable in provider_swc.runnables
            if _is_pure_cyclic_runnable(runnable)
            for access in runnable.writes
            if access.port == connector.from_port and runnable.timingEventMs is not None
        ]
        consumer_accesses = [
            (runnable.name, access.dataElement, runnable.timingEventMs)
            for runnable in consumer_swc.runnables
            if _is_pure_cyclic_runnable(runnable)
            for access in runnable.reads
            if access.port == connector.to_port and runnable.timingEventMs is not None
        ]
        for provider_runnable_name, provider_data_element, producer_period_ms in provider_accesses:
            for consumer_runnable_name, consumer_data_element, consumer_period_ms in consumer_accesses:
                if provider_data_element != consumer_data_element:
                    continue
                identity = (
                    provider_swc.name,
                    connector.from_port,
                    provider_runnable_name,
                    consumer_swc.name,
                    connector.to_port,
                    consumer_runnable_name,
                    producer_period_ms,
                    consumer_period_ms,
                )
                if identity in seen:
                    continue
                seen.add(identity)
                if producer_period_ms == consumer_period_ms:
                    relation = "same period"
                else:
                    relation = "different periods"
                relationships.append(
                    {
                        "scope_name": scope_name,
                        "provider": f"{provider_instance.name}.{connector.from_port}",
                        "provider_swc_name": provider_swc.name,
                        "provider_runnable_name": provider_runnable_name,
                        "consumer": f"{consumer_instance.name}.{connector.to_port}",
                        "consumer_swc_name": consumer_swc.name,
                        "consumer_runnable_name": consumer_runnable_name,
                        "data_element": provider_data_element,
                        "producer_period_ms": producer_period_ms,
                        "consumer_period_ms": consumer_period_ms,
                        "relation": relation,
                    }
                )
    return relationships


def _build_timing_overview(project: Project) -> dict[str, Any]:
    swc_by_name = {swc.name: swc for swc in project.swcs}
    cyclic_runnables = [
        {
            "swc_name": swc.name,
            "runnable_name": runnable.name,
            "period_ms": runnable.timingEventMs,
        }
        for swc in project.swcs
        for runnable in swc.runnables
        if runnable.timingEventMs is not None
    ]
    cyclic_runnables = sorted(
        cyclic_runnables,
        key=lambda item: (item["swc_name"], item["period_ms"], item["runnable_name"]),
    )

    relationships = _build_scope_timing_relationships(
        scope_name=project.system.name,
        components=list(project.system.composition.components),
        connectors=list(project.system.composition.connectors),
        swc_by_name=swc_by_name,
    )
    for subcomposition in project.subcompositions:
        relationships.extend(
            _build_scope_timing_relationships(
                scope_name=subcomposition.name,
                components=list(subcomposition.components),
                connectors=list(subcomposition.connectors),
                swc_by_name=swc_by_name,
            )
        )
    relationships = sorted(
        relationships,
        key=lambda item: (
            item["scope_name"],
            item["provider"],
            item["consumer"],
            item["provider_runnable_name"],
            item["consumer_runnable_name"],
        ),
    )

    return {
        "cyclic_runnables": cyclic_runnables,
        "relationships": relationships,
    }


def build_report_context(project: Project, *, project_path: Path | None = None) -> dict[str, Any]:
    project = _sort_project_for_export(project)
    ctx = ValidationContext(project)
    interface_counts = _interface_counts(project)
    total_component_prototypes = len(project.system.composition.components) + sum(
        len(subcomposition.components) for subcomposition in project.subcompositions
    )
    assembly_connector_count = len(project.system.composition.connectors) + sum(
        len(subcomposition.connectors) for subcomposition in project.subcompositions
    )
    delegation_connector_count = sum(
        len(subcomposition.delegationConnectors) for subcomposition in project.subcompositions
    )
    total_port_count = sum(len(swc.ports) for swc in project.swcs) + sum(
        len(subcomposition.ports) for subcomposition in project.subcompositions
    )
    all_ports = [port for swc in project.swcs for port in swc.ports] + [
        port for subcomposition in project.subcompositions for port in subcomposition.ports
    ]
    provides_port_count = sum(1 for port in all_ports if port.direction == "provides")
    requires_port_count = sum(1 for port in all_ports if port.direction == "requires")

    summary_sentence = (
        f"{_count_phrase(len(project.swcs), 'SWC type')}, "
        f"{_count_phrase(len(project.subcompositions), 'reusable subcomposition type')}, "
        f"{_count_phrase(len(project.interfaces), 'interface')}, and "
        f"{_count_phrase(assembly_connector_count + delegation_connector_count, 'declared connector')}."
    )

    return {
        "project": {
            "path": str(project_path) if project_path is not None else None,
            "root_package": project.rootPackage,
            "system_name": project.system.name,
            "composition_name": project.system.composition.name,
            "autosar_version": project.autosar_version,
            "summary_sentence": summary_sentence,
        },
        "counts": {
            "swc_type_count": len(project.swcs),
            "subcomposition_type_count": len(project.subcompositions),
            "top_level_component_prototype_count": len(project.system.composition.components),
            "nested_component_prototype_count": sum(len(subcomposition.components) for subcomposition in project.subcompositions),
            "total_component_prototype_count": total_component_prototypes,
            "sender_receiver_interface_count": interface_counts["sender_receiver"],
            "client_server_interface_count": interface_counts["client_server"],
            "mode_switch_interface_count": interface_counts["mode_switch"],
            "total_interface_count": len(project.interfaces),
            "total_port_count": total_port_count,
            "provides_port_count": provides_port_count,
            "requires_port_count": requires_port_count,
            "assembly_connector_count": assembly_connector_count,
            "delegation_connector_count": delegation_connector_count,
            "total_connector_count": assembly_connector_count + delegation_connector_count,
        },
        "overview_note": "This report summarizes modeled architecture. Run `arforge validate` separately for findings.",
        "communication_categories": _communication_categories(project),
        "top_level_architecture": _build_top_level_architecture(project),
        "interfaces": _build_interface_summary(project),
        "components": _build_component_summary(project),
        "unconnected_ports": _build_unconnected_ports_summary(project),
        "unused_elements": _build_unused_elements_summary(project, ctx),
        "timing_overview": _build_timing_overview(project),
    }


def render_project_report(
    project: Project,
    *,
    template_dir: Path,
    project_path: Path | None = None,
    template_name: str = REPORT_TEMPLATE,
) -> str:
    context = build_report_context(project, project_path=project_path)
    env = _env(template_dir)
    template = env.get_template(template_name)
    rendered = template.render(**context)
    rendered = re.sub(r"\n{3,}", "\n\n", rendered)
    return rendered.rstrip() + "\n"


def write_project_report(
    project: Project,
    *,
    template_dir: Path,
    out: Path,
    project_path: Path | None = None,
    template_name: str = REPORT_TEMPLATE,
) -> Path:
    rendered = render_project_report(
        project,
        template_dir=template_dir,
        project_path=project_path,
        template_name=template_name,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    return out
