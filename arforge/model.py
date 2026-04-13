from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


SWC_CATEGORY_APPLICATION = "application"
SWC_CATEGORY_SERVICE = "service"
SWC_CATEGORY_COMPLEX_DEVICE_DRIVER = "complexDeviceDriver"
BASE_TYPE_CATEGORY_FIXED_LENGTH = "FIXED_LENGTH"
BASE_TYPE_CATEGORY_ALIASES = {
    "fixedLength": BASE_TYPE_CATEGORY_FIXED_LENGTH,
    "fixed_length": BASE_TYPE_CATEGORY_FIXED_LENGTH,
    BASE_TYPE_CATEGORY_FIXED_LENGTH: BASE_TYPE_CATEGORY_FIXED_LENGTH,
}

SWC_CATEGORY_TO_COMPONENT_TYPE = {
    SWC_CATEGORY_APPLICATION: "APPLICATION-SW-COMPONENT-TYPE",
    SWC_CATEGORY_SERVICE: "SERVICE-SW-COMPONENT-TYPE",
    SWC_CATEGORY_COMPLEX_DEVICE_DRIVER: "COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE",
}

MODE_DECLARATION_GROUP_CATEGORY_EXPLICIT_ORDER = "EXPLICIT_ORDER"
MODE_DECLARATION_GROUP_CATEGORY_ALIASES = {
    "explicitOrder": MODE_DECLARATION_GROUP_CATEGORY_EXPLICIT_ORDER,
    MODE_DECLARATION_GROUP_CATEGORY_EXPLICIT_ORDER: MODE_DECLARATION_GROUP_CATEGORY_EXPLICIT_ORDER,
}

@dataclass(frozen=True)
class BaseType:
    name: str
    description: str | None = None
    bitLength: int | None = None
    signedness: str | None = None
    nativeDeclaration: str | None = None
    category: str = BASE_TYPE_CATEGORY_FIXED_LENGTH


@dataclass(frozen=True)
class ImplementationField:
    name: str
    typeRef: str
    description: str | None = None


@dataclass(frozen=True)
class ImplementationDataType:
    name: str
    description: str | None = None
    baseTypeRef: str | None = None
    kind: str | None = None
    fields: List[ImplementationField] = field(default_factory=list)
    elementTypeRef: str | None = None
    length: int | None = None

    @property
    def is_struct(self) -> bool:
        return bool(self.fields) or self.kind == "struct"

    @property
    def is_array(self) -> bool:
        return self.kind == "array"


@dataclass(frozen=True)
class ApplicationDataType:
    name: str
    implementationTypeRef: str
    description: str | None = None
    constraint: "ConstraintRange | None" = None
    unitRef: str | None = None
    compuMethodRef: str | None = None


@dataclass(frozen=True)
class ConstraintRange:
    min: float | int
    max: float | int


@dataclass(frozen=True)
class Unit:
    name: str
    description: str | None = None
    displayName: str | None = None


@dataclass(frozen=True)
class TextTableEntry:
    value: int
    label: str


@dataclass(frozen=True)
class CompuMethod:
    name: str
    category: str
    description: str | None = None
    unitRef: str | None = None
    factor: float | None = None
    offset: float | None = None
    physMin: float | None = None
    physMax: float | None = None
    entries: List[TextTableEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ModeDeclaration:
    name: str
    value: int | None = None


@dataclass(frozen=True)
class ModeDeclarationGroup:
    name: str
    initialMode: str
    description: str | None = None
    category: str = MODE_DECLARATION_GROUP_CATEGORY_EXPLICIT_ORDER
    onTransitionValue: int | None = None
    modes: List[ModeDeclaration] = field(default_factory=list)


@dataclass(frozen=True)
class DataElement:
    name: str
    typeRef: str
    description: str | None = None

@dataclass(frozen=True)
class Operation:
    name: str
    description: str | None = None
    arguments: List["OperationArgument"] = field(default_factory=list)
    returnType: str = "void"
    possibleErrors: List["ApplicationError"] = field(default_factory=list)


@dataclass(frozen=True)
class ApplicationError:
    name: str
    code: int | None = None
    description: str | None = None


@dataclass(frozen=True)
class OperationArgument:
    name: str
    direction: str
    typeRef: str
    description: str | None = None

@dataclass(frozen=True)
class Interface:
    name: str
    type: str  # senderReceiver | clientServer | modeSwitch
    description: str | None = None
    modeGroupRef: str | None = None
    dataElements: List[DataElement] | None = None
    operations: List[Operation] | None = None

@dataclass(frozen=True)
class Runnable:
    name: str
    description: str | None = None
    timingEventMs: int | None = None
    initEvent: bool = False
    reads: List["DataAccess"] = field(default_factory=list)
    writes: List["DataAccess"] = field(default_factory=list)
    calls: List["OperationCall"] = field(default_factory=list)
    operationInvokedEvents: List["OperationInvokedEvent"] = field(default_factory=list)
    dataReceiveEvents: List["DataReceiveEvent"] = field(default_factory=list)
    modeSwitchEvents: List["ModeSwitchEvent"] = field(default_factory=list)
    raisesErrors: List["OperationErrorRaise"] = field(default_factory=list)


@dataclass(frozen=True)
class DataAccess:
    port: str
    dataElement: str


@dataclass(frozen=True)
class OperationCall:
    port: str
    operation: str
    timeoutMs: int | None = None


@dataclass(frozen=True)
class OperationInvokedEvent:
    port: str
    operation: str
    description: str | None = None


@dataclass(frozen=True)
class DataReceiveEvent:
    port: str
    dataElement: str
    description: str | None = None


@dataclass(frozen=True)
class ModeSwitchEvent:
    port: str
    mode: str
    description: str | None = None


@dataclass(frozen=True)
class OperationErrorRaise:
    operation: str
    error: str


# Backward-compatible aliases for earlier internal names.
SrAccess = DataAccess
CsCall = OperationCall

@dataclass(frozen=True)
class ComSpec:
    mode: str | None = None
    queueLength: int | None = None
    callMode: str | None = None
    timeoutMs: int | None = None
    initValue: int | float | str | bool | None = None

@dataclass(frozen=True)
class Port:
    name: str
    direction: str  # provides | requires
    interfaceRef: str
    interfaceType: str  # senderReceiver | clientServer | modeSwitch
    modeGroupRef: str | None = None
    description: str | None = None
    comSpec: ComSpec | None = None

@dataclass(frozen=True)
class Swc:
    name: str
    runnables: List[Runnable]
    ports: List[Port]
    description: str | None = None
    category: str = SWC_CATEGORY_APPLICATION

    @property
    def component_type_tag(self) -> str:
        return SWC_CATEGORY_TO_COMPONENT_TYPE[self.category]

    @property
    def component_type_dest(self) -> str:
        return self.component_type_tag

@dataclass(frozen=True)
class Connection:
    from_instance: str
    from_port: str
    to_instance: str
    to_port: str
    description: str | None = None
    dataElement: str | None = None
    operation: str | None = None

    @property
    def port_pair_key(self) -> tuple[str, str, str, str]:
        return (
            self.from_instance,
            self.from_port,
            self.to_instance,
            self.to_port,
        )

    @property
    def selector_key(self) -> tuple[str, str]:
        return (
            self.dataElement or "",
            self.operation or "",
        )

    @property
    def identity_key(self) -> tuple[str, str, str, str]:
        return self.port_pair_key

@dataclass(frozen=True)
class ComponentPrototype:
    name: str
    typeRef: str
    description: str | None = None


@dataclass(frozen=True)
class DelegationConnector:
    inner_instance: str
    inner_port: str
    outer_port: str
    description: str | None = None

    @property
    def inner_ref(self) -> str:
        return f"{self.inner_instance}.{self.inner_port}"

    @property
    def identity_key(self) -> tuple[str, str, str]:
        return (
            self.inner_instance,
            self.inner_port,
            self.outer_port,
        )


@dataclass(frozen=True)
class Composition:
    name: str
    components: List[ComponentPrototype]
    connectors: List[Connection]
    description: str | None = None


@dataclass(frozen=True)
class SubcompositionType:
    name: str
    components: List[ComponentPrototype]
    connectors: List[Connection]
    description: str | None = None
    ports: List[Port] = field(default_factory=list)
    delegationConnectors: List[DelegationConnector] = field(default_factory=list)


@dataclass(frozen=True)
class System:
    name: str
    composition: Composition
    description: str | None = None

    @property
    def instances(self) -> List[ComponentPrototype]:
        return self.composition.components

    @property
    def connections(self) -> List[Connection]:
        return self.composition.connectors

@dataclass(frozen=True)
class Project:
    autosar_version: str
    rootPackage: str
    baseTypes: List[BaseType]
    implementationDataTypes: List[ImplementationDataType]
    applicationDataTypes: List[ApplicationDataType]
    units: List[Unit]
    compuMethods: List[CompuMethod]
    modeDeclarationGroups: List[ModeDeclarationGroup]
    interfaces: List[Interface]
    swcs: List[Swc]
    subcompositions: List[SubcompositionType]
    system: System

    @property
    def datatypes(self) -> List[ImplementationDataType]:
        # Backward-compatibility alias used in parts of the codebase.
        return self.implementationDataTypes

    @property
    def connections(self) -> List[Connection]:
        return self.system.connections

def _split_endpoint(ep: str) -> Tuple[str, str]:
    swc, port = ep.split(".", 1)
    return swc, port


def _parse_application_errors(errors: List[Any]) -> List[ApplicationError]:
    parsed: List[ApplicationError] = []
    for error in errors:
        if isinstance(error, dict):
            parsed.append(
                ApplicationError(
                    name=str(error.get("name", "")),
                    code=error.get("code"),
                    description=error.get("description"),
                )
            )

    return sorted(
        parsed,
        key=lambda e: (
            e.name,
            -1 if e.code is None else e.code,
        ),
    )


def _parse_components(components: List[Dict[str, Any]]) -> List[ComponentPrototype]:
    return [
        ComponentPrototype(
            name=component["name"],
            typeRef=component["typeRef"],
            description=component.get("description"),
        )
        for component in components
    ]


def _parse_connectors(connectors: List[Dict[str, Any]]) -> List[Connection]:
    parsed: List[Connection] = []
    for connector in connectors:
        from_instance, from_port = _split_endpoint(connector["from"])
        to_instance, to_port = _split_endpoint(connector["to"])
        parsed.append(
            Connection(
                from_instance=from_instance,
                from_port=from_port,
                to_instance=to_instance,
                to_port=to_port,
                description=connector.get("description"),
                dataElement=connector.get("dataElement"),
                operation=connector.get("operation"),
            )
        )
    return parsed


def _parse_delegation_connectors(connectors: List[Dict[str, Any]]) -> List[DelegationConnector]:
    parsed: List[DelegationConnector] = []
    for connector in connectors:
        inner_instance, inner_port = _split_endpoint(connector["inner"])
        parsed.append(
            DelegationConnector(
                inner_instance=inner_instance,
                inner_port=inner_port,
                outer_port=connector["outer"],
                description=connector.get("description"),
            )
        )
    return parsed


def _build_port(port_data: Dict[str, Any], iface_by_name: Dict[str, Interface]) -> Port:
    interface_name = port_data["interfaceRef"]
    interface = iface_by_name.get(interface_name)
    # interfaceType is used by templates; unknown handled by validation layer
    interface_type = interface.type if interface else "senderReceiver"
    com_spec_data = port_data.get("comSpec")
    com_spec = ComSpec(**com_spec_data) if com_spec_data is not None else None
    return Port(
        name=port_data["name"],
        direction=port_data["direction"],
        interfaceRef=interface_name,
        interfaceType=interface_type,
        modeGroupRef=interface.modeGroupRef if interface and interface.type == "modeSwitch" else None,
        description=port_data.get("description"),
        comSpec=com_spec,
    )


def _parse_ports(ports: List[Dict[str, Any]], iface_by_name: Dict[str, Interface]) -> List[Port]:
    return [_build_port(port_data, iface_by_name) for port_data in ports]


def _normalize_base_type_category(category: str | None) -> str:
    return BASE_TYPE_CATEGORY_ALIASES.get(category or "fixedLength", BASE_TYPE_CATEGORY_FIXED_LENGTH)

def from_dict(d: Dict[str, Any]) -> Project:
    autosar = d["autosar"]
    base_types = [
        BaseType(
            **{
                **bt,
                "category": _normalize_base_type_category(bt.get("category")),
            }
        )
        for bt in d.get("baseTypes", [])
    ]
    impl_types = []
    for idt in d.get("implementationDataTypes", []):
        impl_types.append(
            ImplementationDataType(
                name=idt["name"],
                description=idt.get("description"),
                baseTypeRef=idt.get("baseTypeRef"),
                kind=idt.get("kind"),
                fields=[ImplementationField(**f) for f in idt.get("fields", [])],
                elementTypeRef=idt.get("elementTypeRef"),
                length=idt.get("length"),
            )
        )
    app_types = []
    for adt in d.get("applicationDataTypes", []):
        constraint_data = adt.get("constraint")
        constraint = ConstraintRange(**constraint_data) if constraint_data is not None else None
        app_types.append(
            ApplicationDataType(
                name=adt["name"],
                implementationTypeRef=adt["implementationTypeRef"],
                description=adt.get("description"),
                constraint=constraint,
                unitRef=adt.get("unitRef"),
                compuMethodRef=adt.get("compuMethodRef"),
            )
        )
    units = [Unit(**u) for u in d.get("units", [])]
    compu_methods = []
    for cm in d.get("compuMethods", []):
        compu_methods.append(
            CompuMethod(
                name=cm["name"],
                category=cm["category"],
                description=cm.get("description"),
                unitRef=cm.get("unitRef"),
                factor=cm.get("factor"),
                offset=cm.get("offset"),
                physMin=cm.get("physMin"),
                physMax=cm.get("physMax"),
                entries=[TextTableEntry(**entry) for entry in cm.get("entries", [])],
            )
        )
    mode_declaration_groups = []
    for mdg in d.get("modeDeclarationGroups", []):
        raw_category = mdg.get("category", "explicitOrder")
        mode_declaration_groups.append(
            ModeDeclarationGroup(
                name=mdg["name"],
                description=mdg.get("description"),
                category=MODE_DECLARATION_GROUP_CATEGORY_ALIASES.get(
                    raw_category,
                    raw_category,
                ),
                initialMode=mdg["initialMode"],
                onTransitionValue=mdg.get("onTransitionValue"),
                modes=[
                    ModeDeclaration(
                        name=mode["name"],
                        value=mode.get("value"),
                    )
                    if isinstance(mode, dict)
                    else ModeDeclaration(name=mode)
                    for mode in mdg.get("modes", [])
                ],
            )
        )

    ifaces: List[Interface] = []
    for itf in d.get("interfaces", []):
        if itf["type"] == "senderReceiver":
            des = [DataElement(**de) for de in itf.get("dataElements", [])]
            ifaces.append(
                Interface(
                    name=itf["name"],
                    type=itf["type"],
                    description=itf.get("description"),
                    modeGroupRef=None,
                    dataElements=des,
                    operations=None,
                )
            )
        elif itf["type"] == "clientServer":
            ops = []
            for op in itf.get("operations", []):
                op_args = [OperationArgument(**arg) for arg in op.get("arguments", [])]
                ops.append(
                    Operation(
                        name=op["name"],
                        description=op.get("description"),
                        arguments=op_args,
                        returnType=op.get("returnType", "void"),
                        possibleErrors=_parse_application_errors(op.get("possibleErrors", [])),
                    )
                )
            ifaces.append(
                Interface(
                    name=itf["name"],
                    type=itf["type"],
                    description=itf.get("description"),
                    modeGroupRef=None,
                    dataElements=None,
                    operations=ops,
                )
            )
        else:
            ifaces.append(
                Interface(
                    name=itf["name"],
                    type=itf["type"],
                    description=itf.get("description"),
                    modeGroupRef=itf.get("modeGroupRef"),
                    dataElements=None,
                    operations=None,
                )
            )

    iface_by_name = {i.name: i for i in ifaces}

    swcs: List[Swc] = []
    for s in d.get("swcs", []):
        runs = [
            Runnable(
                name=r["name"],
                description=r.get("description"),
                timingEventMs=r.get("timingEventMs"),
                initEvent=bool(r.get("initEvent", False)),
                reads=sorted(
                    [DataAccess(**acc) for acc in r.get("reads", [])],
                    key=lambda acc: (acc.port, acc.dataElement),
                ),
                writes=sorted(
                    [DataAccess(**acc) for acc in r.get("writes", [])],
                    key=lambda acc: (acc.port, acc.dataElement),
                ),
                calls=sorted(
                    [OperationCall(**acc) for acc in r.get("calls", [])],
                    key=lambda acc: (
                        acc.port,
                        acc.operation,
                        -1 if acc.timeoutMs is None else acc.timeoutMs,
                    ),
                ),
                operationInvokedEvents=sorted(
                    [OperationInvokedEvent(**e) for e in r.get("operationInvokedEvents", [])],
                    key=lambda e: (e.port, e.operation),
                ),
                dataReceiveEvents=sorted(
                    [DataReceiveEvent(**e) for e in r.get("dataReceiveEvents", [])],
                    key=lambda e: (e.port, e.dataElement),
                ),
                modeSwitchEvents=sorted(
                    [ModeSwitchEvent(**e) for e in r.get("modeSwitchEvents", [])],
                    key=lambda e: (e.port, e.mode),
                ),
                raisesErrors=sorted(
                    [OperationErrorRaise(**e) for e in r.get("raisesErrors", [])],
                    key=lambda e: (e.operation, e.error),
                ),
            )
            for r in s.get("runnables", [])
        ]
        swcs.append(
            Swc(
                name=s["name"],
                runnables=runs,
                ports=_parse_ports(s.get("ports", []), iface_by_name),
                description=s.get("description"),
                category=s.get("category", SWC_CATEGORY_APPLICATION),
            )
        )

    subcompositions: List[SubcompositionType] = []
    for subcomposition_data in d.get("subcompositions", []):
        subcompositions.append(
            SubcompositionType(
                name=subcomposition_data["name"],
                description=subcomposition_data.get("description"),
                ports=_parse_ports(subcomposition_data.get("ports", []), iface_by_name),
                components=_parse_components(subcomposition_data.get("components", [])),
                connectors=_parse_connectors(subcomposition_data.get("connectors", [])),
                delegationConnectors=_parse_delegation_connectors(subcomposition_data.get("delegationConnectors", [])),
            )
        )

    system_data = d.get("system")
    if system_data:
        composition_data = system_data["composition"]
        composition = Composition(
            name=composition_data["name"],
            components=_parse_components(composition_data.get("components", [])),
            connectors=_parse_connectors(composition_data.get("connectors", [])),
            description=composition_data.get("description"),
        )
        system = System(
            name=system_data["name"],
            composition=composition,
            description=system_data.get("description"),
        )
    else:
        raise KeyError("Missing required 'system' model.")

    return Project(
        autosar_version=autosar["version"],
        rootPackage=autosar["rootPackage"],
        baseTypes=base_types,
        implementationDataTypes=impl_types,
        applicationDataTypes=app_types,
        units=units,
        compuMethods=compu_methods,
        modeDeclarationGroups=mode_declaration_groups,
        interfaces=ifaces,
        swcs=swcs,
        subcompositions=subcompositions,
        system=system,
    )
