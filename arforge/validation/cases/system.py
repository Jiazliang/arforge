"""System and subcomposition semantic validation cases.

This module validates top-level component prototype references together with
connector semantics in both the system composition and reusable
subcompositions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from ...model import ComponentPrototype, Connection
from ...semantic_validation import Finding, ValidationCase, ValidationContext


def _connection_sort_key(connector: Connection) -> tuple[str, str, str, str, str, str]:
    return (
        connector.from_instance,
        connector.from_port,
        connector.to_instance,
        connector.to_port,
        connector.dataElement or "",
        connector.operation or "",
    )


@dataclass(frozen=True)
class _CompositionValidationSpec:
    scope_name: str
    components: List[ComponentPrototype]
    connectors: List[Connection]
    allowed_component_type_kinds: tuple[str, ...]
    unknown_type_code: str
    nested_type_code: str | None = None


def _component_map(components: Iterable[ComponentPrototype]) -> Dict[str, ComponentPrototype]:
    return {component.name: component for component in components}


def _validate_component_types(ctx: ValidationContext, spec: _CompositionValidationSpec, case: ValidationCase) -> List[Finding]:
    findings: List[Finding] = []
    for component in sorted(spec.components, key=lambda item: item.name):
        kind = ctx.find_top_level_component_type_kind(component.typeRef)
        if kind is None:
            findings.append(
                case.finding(
                    f"{spec.scope_name} component prototype '{component.name}' references unknown type '{component.typeRef}'.",
                    code=spec.unknown_type_code,
                )
            )
            continue
        if kind not in spec.allowed_component_type_kinds and spec.nested_type_code is not None:
            findings.append(
                case.finding(
                    f"{spec.scope_name} component prototype '{component.name}' references subcomposition type '{component.typeRef}', "
                    "but nested subcompositions are not supported in this iteration.",
                    code=spec.nested_type_code,
                )
            )
    return findings


def _validate_connectors(ctx: ValidationContext, spec: _CompositionValidationSpec, case: ValidationCase) -> List[Finding]:
    findings: List[Finding] = []
    components_by_name = _component_map(spec.components)
    seen_sr_port_pairs: set[tuple[str, str, str, str]] = set()
    seen_cs_port_pairs: set[tuple[str, str, str, str]] = set()
    seen_ms_port_pairs: set[tuple[str, str, str, str]] = set()

    for conn in sorted(spec.connectors, key=_connection_sort_key):
        from_component = components_by_name.get(conn.from_instance)
        if from_component is None:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector references unknown from instance '{conn.from_instance}'.",
                    code=f"{case.case_id}-UNKNOWN-FROM-INSTANCE",
                )
            )
            continue

        to_component = components_by_name.get(conn.to_instance)
        if to_component is None:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector references unknown to instance '{conn.to_instance}'.",
                    code=f"{case.case_id}-UNKNOWN-TO-INSTANCE",
                )
            )
            continue

        from_swc = ctx.swc_by_name.get(from_component.typeRef)
        to_swc = ctx.swc_by_name.get(to_component.typeRef)
        if from_swc is None or to_swc is None:
            continue

        from_port = ctx.find_swc_port(from_swc.name, conn.from_port)
        to_port = ctx.find_swc_port(to_swc.name, conn.to_port)

        if from_port is None:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector from '{conn.from_instance}.{conn.from_port}' references unknown port on type '{from_swc.name}'.",
                    code=f"{case.case_id}-UNKNOWN-FROM-PORT",
                )
            )
            continue
        if to_port is None:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector to '{conn.to_instance}.{conn.to_port}' references unknown port on type '{to_swc.name}'.",
                    code=f"{case.case_id}-UNKNOWN-TO-PORT",
                )
            )
            continue

        if from_port.direction != "provides":
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector from '{conn.from_instance}.{conn.from_port}' must be a provides-port.",
                    code=f"{case.case_id}-FROM-DIRECTION",
                )
            )
        if to_port.direction != "requires":
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector to '{conn.to_instance}.{conn.to_port}' must be a requires-port.",
                    code=f"{case.case_id}-TO-DIRECTION",
                )
            )

        if from_port.interfaceRef != to_port.interfaceRef:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector interface mismatch: '{conn.from_instance}.{conn.from_port}' uses '{from_port.interfaceRef}' but "
                    f"'{conn.to_instance}.{conn.to_port}' uses '{to_port.interfaceRef}'.",
                    code=f"{case.case_id}-INTERFACE-MISMATCH",
                )
            )
            continue

        interface = ctx.iface_by_name.get(from_port.interfaceRef)
        if interface is None:
            continue

        if conn.dataElement and conn.operation:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector {conn.from_instance}.{conn.from_port} -> {conn.to_instance}.{conn.to_port} "
                    "must not define both dataElement and operation.",
                    code=f"{case.case_id}-MULTIPLE-SELECTORS",
                )
            )
            continue

        if interface.type == "senderReceiver":
            if conn.operation:
                findings.append(
                    case.finding(
                        f"{spec.scope_name} senderReceiver connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} cannot set operation.",
                        code=f"{case.case_id}-SR-INVALID-OPERATION",
                    )
                )
            if conn.port_pair_key in seen_sr_port_pairs:
                findings.append(
                    case.finding(
                        f"Duplicate senderReceiver connector '{conn.from_instance}.{conn.from_port}' -> "
                        f"'{conn.to_instance}.{conn.to_port}' is not allowed; SR connectors are unique per port pair.",
                        code=f"{case.case_id}-SR-DUPLICATE-PORT-PAIR",
                    )
                )
            else:
                seen_sr_port_pairs.add(conn.port_pair_key)
        elif interface.type == "clientServer":
            if from_port.interfaceType != "clientServer" or to_port.interfaceType != "clientServer":
                findings.append(
                    case.finding(
                        f"{spec.scope_name} clientServer connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} must connect ports typed by clientServer interfaces.",
                        code=f"{case.case_id}-CS-INTERFACE-TYPE",
                    )
                )
            if conn.dataElement:
                findings.append(
                    case.finding(
                        f"{spec.scope_name} clientServer connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} cannot set dataElement.",
                        code=f"{case.case_id}-CS-INVALID-DATAELEMENT",
                    )
                )
            if conn.port_pair_key in seen_cs_port_pairs:
                findings.append(
                    case.finding(
                        f"Duplicate clientServer connector '{conn.from_instance}.{conn.from_port}' -> "
                        f"'{conn.to_instance}.{conn.to_port}' is not allowed; C/S connectors are unique per port pair.",
                        code=f"{case.case_id}-CS-DUPLICATE-PORT-PAIR",
                    )
                )
            else:
                seen_cs_port_pairs.add(conn.port_pair_key)
            if conn.operation:
                findings.append(
                    case.finding(
                        f"{spec.scope_name} clientServer connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} must not set operation; C/S connectors are port-level.",
                        code=f"{case.case_id}-CS-INVALID-OPERATION",
                    )
                )
        elif interface.type == "modeSwitch":
            if from_port.interfaceType != "modeSwitch" or to_port.interfaceType != "modeSwitch":
                findings.append(
                    case.finding(
                        f"{spec.scope_name} modeSwitch connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} must connect ports typed by modeSwitch interfaces.",
                        code=f"{case.case_id}-MS-INTERFACE-TYPE",
                    )
                )
            if conn.dataElement:
                findings.append(
                    case.finding(
                        f"{spec.scope_name} modeSwitch connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} cannot set dataElement.",
                        code=f"{case.case_id}-MS-INVALID-DATAELEMENT",
                    )
                )
            if conn.port_pair_key in seen_ms_port_pairs:
                findings.append(
                    case.finding(
                        f"Duplicate modeSwitch connector '{conn.from_instance}.{conn.from_port}' -> "
                        f"'{conn.to_instance}.{conn.to_port}' is not allowed; mode-switch connectors are unique per port pair.",
                        code=f"{case.case_id}-MS-DUPLICATE-PORT-PAIR",
                    )
                )
            else:
                seen_ms_port_pairs.add(conn.port_pair_key)
            if conn.operation:
                findings.append(
                    case.finding(
                        f"{spec.scope_name} modeSwitch connector {conn.from_instance}.{conn.from_port} -> "
                        f"{conn.to_instance}.{conn.to_port} must not set operation.",
                        code=f"{case.case_id}-MS-INVALID-OPERATION",
                    )
                )
        else:
            findings.append(
                case.finding(
                    f"{spec.scope_name} connector {conn.from_instance}.{conn.from_port} -> {conn.to_instance}.{conn.to_port} "
                    f"uses unsupported interface type '{interface.type}'.",
                    code=f"{case.case_id}-UNKNOWN-INTERFACE-TYPE",
                )
            )

    return findings


class SystemInstanceTypeCase(ValidationCase):
    case_id = "CORE-030"
    name = "SystemInstanceTypes"
    description = "Checks that top-level system component prototypes reference known atomic SWC types or subcomposition types."
    tags = ("core", "system")

    def applicability(self, ctx: ValidationContext) -> tuple[bool, str | None]:
        if not ctx.project.system.composition.components:
            return False, "no system component prototypes defined"
        return True, None

    def run(self, ctx: ValidationContext) -> List[Finding]:
        spec = _CompositionValidationSpec(
            scope_name="System",
            components=ctx.project.system.composition.components,
            connectors=ctx.project.system.composition.connectors,
            allowed_component_type_kinds=("swc", "subcomposition"),
            unknown_type_code="CORE-030-UNKNOWN-COMPONENT-TYPE",
        )
        return _validate_component_types(ctx, spec, self)


class SubcompositionTypeCase(ValidationCase):
    case_id = "CORE-031"
    name = "SubcompositionInstanceTypes"
    description = "Checks that subcomposition internal component prototypes resolve to atomic SWC types and rejects nested subcompositions."
    tags = ("core", "system", "subcomposition")

    def applicability(self, ctx: ValidationContext) -> tuple[bool, str | None]:
        if not ctx.project.subcompositions:
            return False, "no subcompositions defined"
        return True, None

    def run(self, ctx: ValidationContext) -> List[Finding]:
        findings: List[Finding] = []
        for subcomposition in sorted(ctx.project.subcompositions, key=lambda item: item.name):
            spec = _CompositionValidationSpec(
                scope_name=f"Subcomposition '{subcomposition.name}'",
                components=subcomposition.components,
                connectors=subcomposition.connectors,
                allowed_component_type_kinds=("swc",),
                unknown_type_code="CORE-031-UNKNOWN-SWC-TYPE",
                nested_type_code="CORE-031-NESTED-SUBCOMPOSITION",
            )
            findings.extend(_validate_component_types(ctx, spec, self))
        return findings


class ConnectionSemanticCase(ValidationCase):
    case_id = "CORE-040"
    name = "ConnectionSemantics"
    description = "Checks top-level system assembly connectors and port compatibility semantics."
    tags = ("core", "system", "connections")

    def applicability(self, ctx: ValidationContext) -> tuple[bool, str | None]:
        if not ctx.project.system.composition.connectors:
            return False, "no system connectors defined"
        return True, None

    def run(self, ctx: ValidationContext) -> List[Finding]:
        spec = _CompositionValidationSpec(
            scope_name="System",
            components=ctx.project.system.composition.components,
            connectors=ctx.project.system.composition.connectors,
            allowed_component_type_kinds=("swc", "subcomposition"),
            unknown_type_code="CORE-030-UNKNOWN-COMPONENT-TYPE",
        )
        return _validate_connectors(ctx, spec, self)


class SubcompositionConnectionSemanticCase(ValidationCase):
    case_id = "CORE-032"
    name = "SubcompositionConnectionSemantics"
    description = "Checks internal subcomposition assembly connectors and port compatibility semantics."
    tags = ("core", "system", "connections", "subcomposition")

    def applicability(self, ctx: ValidationContext) -> tuple[bool, str | None]:
        if not any(subcomposition.connectors for subcomposition in ctx.project.subcompositions):
            return False, "no subcomposition connectors defined"
        return True, None

    def run(self, ctx: ValidationContext) -> List[Finding]:
        findings: List[Finding] = []
        for subcomposition in sorted(ctx.project.subcompositions, key=lambda item: item.name):
            spec = _CompositionValidationSpec(
                scope_name=f"Subcomposition '{subcomposition.name}'",
                components=subcomposition.components,
                connectors=subcomposition.connectors,
                allowed_component_type_kinds=("swc",),
                unknown_type_code="CORE-031-UNKNOWN-SWC-TYPE",
                nested_type_code="CORE-031-NESTED-SUBCOMPOSITION",
            )
            findings.extend(_validate_connectors(ctx, spec, self))
        return findings


class SubcompositionPortDefinitionCase(ValidationCase):
    case_id = "CORE-033"
    name = "SubcompositionPortDefinitions"
    description = "Checks subcomposition boundary ports for unique names, valid directions, and resolvable interface references."
    tags = ("core", "system", "subcomposition", "ports")

    def applicability(self, ctx: ValidationContext) -> tuple[bool, str | None]:
        if not any(subcomposition.ports for subcomposition in ctx.project.subcompositions):
            return False, "no subcomposition boundary ports defined"
        return True, None

    def run(self, ctx: ValidationContext) -> List[Finding]:
        findings: List[Finding] = []
        for subcomposition in sorted(ctx.project.subcompositions, key=lambda item: item.name):
            port_names = [port.name for port in subcomposition.ports]
            if len(set(port_names)) != len(port_names):
                findings.append(
                    self.finding(
                        f"Subcomposition '{subcomposition.name}' has duplicate composition port names.",
                        code="CORE-033-PORT-DUPLICATE",
                    )
                )

            for port in sorted(subcomposition.ports, key=lambda item: item.name):
                if port.direction not in {"provides", "requires"}:
                    findings.append(
                        self.finding(
                            f"Subcomposition '{subcomposition.name}' port '{port.name}' has invalid direction '{port.direction}'.",
                            code="CORE-033-DIRECTION",
                        )
                    )

                interface = ctx.iface_by_name.get(port.interfaceRef)
                if interface is None:
                    findings.append(
                        self.finding(
                            f"Subcomposition '{subcomposition.name}' port '{port.name}' references unknown interface '{port.interfaceRef}'.",
                            code="CORE-033-UNKNOWN-INTERFACE-REF",
                        )
                    )
                    continue

                if port.interfaceType != interface.type:
                    findings.append(
                        self.finding(
                            f"Internal mismatch: subcomposition port '{subcomposition.name}.{port.name}' interfaceType '{port.interfaceType}' != interface '{interface.type}'.",
                            code="CORE-033-INTERFACE-TYPE-MISMATCH",
                        )
                    )

        return findings
