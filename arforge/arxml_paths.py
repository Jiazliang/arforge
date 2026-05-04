"""ARXML package layout defaults, validation helpers, and path resolution.

This module centralizes package-layout defaults, package-path validation, and
deterministic ARXML reference building so loaders, validators, and exporters
can share the same package assignment logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .model import (
    ApplicationDataType,
    BaseType,
    CompuMethod,
    Interface,
    ModeDeclarationGroup,
    PackageLayout,
    Project,
    SubcompositionType,
    Swc,
    System,
    Unit,
)

PACKAGE_CATEGORY_BASE_TYPE = "baseType"
PACKAGE_CATEGORY_IMPLEMENTATION_DATA_TYPE = "implementationDataType"
PACKAGE_CATEGORY_APPLICATION_DATA_TYPE = "applicationDataType"
PACKAGE_CATEGORY_UNIT = "unit"
PACKAGE_CATEGORY_COMPU_METHOD = "compuMethod"
PACKAGE_CATEGORY_MODE_DECLARATION_GROUP = "modeDeclarationGroup"
PACKAGE_CATEGORY_INTERFACE = "interface"
PACKAGE_CATEGORY_SWC = "swc"
PACKAGE_CATEGORY_COMPOSITION = "composition"
PACKAGE_CATEGORY_SYSTEM = "system"
PACKAGE_CATEGORY_DATA_CONSTRAINT = "dataConstraint"

SUPPORTED_PACKAGE_CATEGORIES: tuple[str, ...] = (
    PACKAGE_CATEGORY_BASE_TYPE,
    PACKAGE_CATEGORY_IMPLEMENTATION_DATA_TYPE,
    PACKAGE_CATEGORY_APPLICATION_DATA_TYPE,
    PACKAGE_CATEGORY_UNIT,
    PACKAGE_CATEGORY_COMPU_METHOD,
    PACKAGE_CATEGORY_MODE_DECLARATION_GROUP,
    PACKAGE_CATEGORY_INTERFACE,
    PACKAGE_CATEGORY_SWC,
    PACKAGE_CATEGORY_COMPOSITION,
    PACKAGE_CATEGORY_SYSTEM,
)

ALL_PACKAGE_CATEGORIES: tuple[str, ...] = SUPPORTED_PACKAGE_CATEGORIES + (PACKAGE_CATEGORY_DATA_CONSTRAINT,)

INTERNAL_PACKAGE_DEFAULTS: dict[str, str] = {
    PACKAGE_CATEGORY_BASE_TYPE: "BaseTypes",
    PACKAGE_CATEGORY_IMPLEMENTATION_DATA_TYPE: "ImplementationDataTypes",
    PACKAGE_CATEGORY_APPLICATION_DATA_TYPE: "ApplicationDataTypes",
    PACKAGE_CATEGORY_UNIT: "Units",
    PACKAGE_CATEGORY_COMPU_METHOD: "CompuMethods",
    PACKAGE_CATEGORY_MODE_DECLARATION_GROUP: "Modes",
    PACKAGE_CATEGORY_INTERFACE: "Interfaces",
    PACKAGE_CATEGORY_SWC: "Components",
    PACKAGE_CATEGORY_COMPOSITION: "Components",
    PACKAGE_CATEGORY_SYSTEM: "System",
    PACKAGE_CATEGORY_DATA_CONSTRAINT: "DataConstrs",
}

INTERNAL_ALLOWED_PACKAGES: tuple[str, ...] = (
    "BaseTypes",
    "ImplementationDataTypes",
    "ApplicationDataTypes",
    "Units",
    "CompuMethods",
    "Modes",
    "Interfaces",
    "Components",
    "System",
    "DataConstrs",
)


def default_package_layout() -> dict[str, Any]:
    return {
        "name": "DefaultLayout",
        "description": "Backward-compatible default ARXML package layout.",
        "defaults": dict(INTERNAL_PACKAGE_DEFAULTS),
        "allowedPackages": list(INTERNAL_ALLOWED_PACKAGES),
    }


def merged_package_defaults(layout: PackageLayout) -> dict[str, str]:
    defaults = dict(INTERNAL_PACKAGE_DEFAULTS)
    defaults.update(layout.defaults)
    return defaults


def merged_allowed_packages(layout: PackageLayout) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for package_path in list(layout.allowedPackages) + list(INTERNAL_ALLOWED_PACKAGES):
        if package_path not in seen:
            ordered.append(package_path)
            seen.add(package_path)
    return tuple(ordered)


def validate_package_path_syntax(path: str) -> list[str]:
    errors: list[str] = []
    if not path:
        return ["must not be empty"]
    if path.startswith("/"):
        errors.append("must not start with '/'")
    if path.endswith("/"):
        errors.append("must not end with '/'")
    segments = path.split("/")
    if any(segment == "" for segment in segments):
        errors.append("must not contain empty path segments")
    for segment in segments:
        if not segment:
            continue
        if not segment.replace("_", "").isalnum():
            errors.append(f"contains invalid short-name segment '{segment}'")
    return errors


def package_path_parents(path: str) -> list[str]:
    parts = path.split("/")
    return ["/".join(parts[:idx]) for idx in range(1, len(parts))]


def join_arxml_path(*parts: str) -> str:
    clean = [part.strip("/") for part in parts if part and part.strip("/")]
    return "/" + "/".join(clean)


@dataclass(frozen=True)
class TypeRefTarget:
    ref: str
    dest: str
    package: str


@dataclass(frozen=True)
class PackageNode:
    name: str
    path: str
    base_types: tuple[BaseType, ...] = ()
    implementation_data_types: tuple[Any, ...] = ()
    application_data_types: tuple[ApplicationDataType, ...] = ()
    data_constraints: tuple[ApplicationDataType, ...] = ()
    units: tuple[Unit, ...] = ()
    compu_methods: tuple[CompuMethod, ...] = ()
    mode_declaration_groups: tuple[ModeDeclarationGroup, ...] = ()
    interfaces: tuple[Interface, ...] = ()
    swcs: tuple[Swc, ...] = ()
    subcompositions: tuple[SubcompositionType, ...] = ()
    systems: tuple[System, ...] = ()
    children: tuple["PackageNode", ...] = ()


class ArxmlPathResolver:
    """Central resolver for AUTOSAR package assignment and ARXML paths."""

    def __init__(self, project: Project):
        self.project = project
        self.defaults = merged_package_defaults(project.packageLayout)
        self.allowed_packages = set(merged_allowed_packages(project.packageLayout))
        self._swcs = {swc.name: swc for swc in project.swcs}
        self._subcompositions = {item.name: item for item in project.subcompositions}
        self._interfaces = {item.name: item for item in project.interfaces}
        self._application_types = {item.name: item for item in project.applicationDataTypes}
        self._implementation_types = {item.name: item for item in project.implementationDataTypes}
        self._base_types = {item.name: item for item in project.baseTypes}
        self._units = {item.name: item for item in project.units}
        self._compu_methods = {item.name: item for item in project.compuMethods}
        self._mode_groups = {item.name: item for item in project.modeDeclarationGroups}

    def package_for_category(self, category: str) -> str:
        return self.defaults[category]

    def package_for_element(self, category: str, explicit_package: str | None) -> str:
        return explicit_package or self.package_for_category(category)

    def swc_package(self, swc_name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_SWC, self._swcs[swc_name].package)

    def composition_package(self, composition_name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_COMPOSITION, self._subcompositions[composition_name].package)

    def interface_package(self, interface_name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_INTERFACE, self._interfaces[interface_name].package)

    def application_type_package(self, type_name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_APPLICATION_DATA_TYPE, self._application_types[type_name].package)

    def implementation_type_package(self, type_name: str) -> str:
        return self.package_for_element(
            PACKAGE_CATEGORY_IMPLEMENTATION_DATA_TYPE,
            self._implementation_types[type_name].package,
        )

    def base_type_package(self, type_name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_BASE_TYPE, self._base_types[type_name].package)

    def unit_package(self, unit_name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_UNIT, self._units[unit_name].package)

    def compu_method_package(self, name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_COMPU_METHOD, self._compu_methods[name].package)

    def mode_group_package(self, name: str) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_MODE_DECLARATION_GROUP, self._mode_groups[name].package)

    def system_package(self) -> str:
        return self.package_for_element(PACKAGE_CATEGORY_SYSTEM, self.project.system.package)

    def swc(self, swc_name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.swc_package(swc_name), swc_name)

    def composition(self, composition_name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.composition_package(composition_name), composition_name)

    def interface(self, interface_name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.interface_package(interface_name), interface_name)

    def application_type(self, type_name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.application_type_package(type_name), type_name)

    def implementation_type(self, type_name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.implementation_type_package(type_name), type_name)

    def base_type(self, type_name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.base_type_package(type_name), type_name)

    def unit(self, name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.unit_package(name), name)

    def compu_method(self, name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.compu_method_package(name), name)

    def mode_group(self, name: str) -> str:
        return join_arxml_path(self.project.rootPackage, self.mode_group_package(name), name)

    def mode_declaration(self, group_name: str, mode_name: str) -> str:
        return join_arxml_path(self.mode_group(group_name), mode_name)

    def system(self, system_name: str | None = None) -> str:
        target_name = system_name or self.project.system.name
        return join_arxml_path(self.project.rootPackage, self.system_package(), target_name)

    def system_composition(self, composition_name: str | None = None) -> str:
        target_name = composition_name or self.project.system.composition.name
        return join_arxml_path(self.project.rootPackage, self.system_package(), target_name)

    def swc_port(self, swc_name: str, port_name: str) -> str:
        return join_arxml_path(self.swc(swc_name), port_name)

    def composition_port(self, composition_name: str, port_name: str) -> str:
        return join_arxml_path(self.composition(composition_name), port_name)

    def runnable(self, swc_name: str, runnable_name: str) -> str:
        return join_arxml_path(self.swc(swc_name), f"IB_{swc_name}", runnable_name)

    def component_prototype(self, owner_path: str, prototype_name: str) -> str:
        return join_arxml_path(owner_path, prototype_name)

    def interface_data_element(self, interface_name: str, element_name: str) -> str:
        return join_arxml_path(self.interface(interface_name), element_name)

    def interface_operation(self, interface_name: str, operation_name: str) -> str:
        return join_arxml_path(self.interface(interface_name), operation_name)

    def interface_possible_error(self, interface_name: str, error_name: str) -> str:
        return join_arxml_path(self.interface(interface_name), error_name)

    def interface_mode_group_prototype(self, interface_name: str) -> str:
        return join_arxml_path(self.interface(interface_name), f"{interface_name}_ModeGroup")

    def data_constraint_package(self) -> str:
        return self.package_for_category(PACKAGE_CATEGORY_DATA_CONSTRAINT)

    def data_constraint(self, application_type_name: str) -> str:
        return join_arxml_path(
            self.project.rootPackage,
            self.data_constraint_package(),
            f"DC_{application_type_name}",
        )

    def type_ref_target(self, type_name: str) -> TypeRefTarget | None:
        if type_name in self._base_types:
            package = self.base_type_package(type_name)
            return TypeRefTarget(ref=self.base_type(type_name), dest="SW-BASE-TYPE", package=package)
        if type_name in self._implementation_types:
            package = self.implementation_type_package(type_name)
            return TypeRefTarget(ref=self.implementation_type(type_name), dest="IMPLEMENTATION-DATA-TYPE", package=package)
        if type_name in self._application_types:
            package = self.application_type_package(type_name)
            return TypeRefTarget(
                ref=self.application_type(type_name),
                dest="APPLICATION-PRIMITIVE-DATA-TYPE",
                package=package,
            )
        return None

    def component_type_dest(self, type_name: str) -> str:
        swc = self._swcs.get(type_name)
        if swc is not None:
            return swc.component_type_dest
        if type_name in self._subcompositions:
            return "COMPOSITION-SW-COMPONENT-TYPE"
        raise KeyError(type_name)

    def component_type_ref(self, type_name: str) -> str:
        if type_name in self._swcs:
            return self.swc(type_name)
        if type_name in self._subcompositions:
            return self.composition(type_name)
        raise KeyError(type_name)


@dataclass
class _MutablePackageNode:
    name: str
    path: str
    base_types: list[BaseType] = field(default_factory=list)
    implementation_data_types: list[Any] = field(default_factory=list)
    application_data_types: list[ApplicationDataType] = field(default_factory=list)
    data_constraints: list[ApplicationDataType] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)
    compu_methods: list[CompuMethod] = field(default_factory=list)
    mode_declaration_groups: list[ModeDeclarationGroup] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    swcs: list[Swc] = field(default_factory=list)
    subcompositions: list[SubcompositionType] = field(default_factory=list)
    systems: list[System] = field(default_factory=list)
    children: dict[str, "_MutablePackageNode"] = field(default_factory=dict)

    def freeze(self) -> PackageNode:
        return PackageNode(
            name=self.name,
            path=self.path,
            base_types=tuple(sorted(self.base_types, key=lambda item: item.name)),
            implementation_data_types=tuple(sorted(self.implementation_data_types, key=lambda item: item.name)),
            application_data_types=tuple(sorted(self.application_data_types, key=lambda item: item.name)),
            data_constraints=tuple(sorted(self.data_constraints, key=lambda item: item.name)),
            units=tuple(sorted(self.units, key=lambda item: item.name)),
            compu_methods=tuple(sorted(self.compu_methods, key=lambda item: item.name)),
            mode_declaration_groups=tuple(sorted(self.mode_declaration_groups, key=lambda item: item.name)),
            interfaces=tuple(sorted(self.interfaces, key=lambda item: item.name)),
            swcs=tuple(sorted(self.swcs, key=lambda item: item.name)),
            subcompositions=tuple(sorted(self.subcompositions, key=lambda item: item.name)),
            systems=tuple(sorted(self.systems, key=lambda item: item.name)),
            children=tuple(self.children[name].freeze() for name in sorted(self.children)),
        )


def build_package_tree(
    resolver: ArxmlPathResolver,
    *,
    base_types: Sequence[BaseType] = (),
    implementation_data_types: Sequence[Any] = (),
    application_data_types: Sequence[ApplicationDataType] = (),
    units: Sequence[Unit] = (),
    compu_methods: Sequence[CompuMethod] = (),
    mode_declaration_groups: Sequence[ModeDeclarationGroup] = (),
    interfaces: Sequence[Interface] = (),
    swcs: Sequence[Swc] = (),
    subcompositions: Sequence[SubcompositionType] = (),
    systems: Sequence[System] = (),
) -> tuple[PackageNode, ...]:
    root = _MutablePackageNode(name="", path="")

    def ensure_node(package_path: str) -> _MutablePackageNode:
        cursor = root
        current_path = ""
        for segment in package_path.split("/"):
            current_path = segment if not current_path else f"{current_path}/{segment}"
            cursor = cursor.children.setdefault(segment, _MutablePackageNode(name=segment, path=current_path))
        return cursor

    def append(package_path: str, attr: str, item: Any) -> None:
        ensure_node(package_path)
        for parent in package_path_parents(package_path):
            ensure_node(parent)
        getattr(ensure_node(package_path), attr).append(item)

    for item in base_types:
        append(resolver.base_type_package(item.name), "base_types", item)
    for item in implementation_data_types:
        append(resolver.implementation_type_package(item.name), "implementation_data_types", item)
    for item in application_data_types:
        append(resolver.application_type_package(item.name), "application_data_types", item)
        if item.constraint is not None:
            append(resolver.data_constraint_package(), "data_constraints", item)
    for item in units:
        append(resolver.unit_package(item.name), "units", item)
    for item in compu_methods:
        append(resolver.compu_method_package(item.name), "compu_methods", item)
    for item in mode_declaration_groups:
        append(resolver.mode_group_package(item.name), "mode_declaration_groups", item)
    for item in interfaces:
        append(resolver.interface_package(item.name), "interfaces", item)
    for item in swcs:
        append(resolver.swc_package(item.name), "swcs", item)
    for item in subcompositions:
        append(resolver.composition_package(item.name), "subcompositions", item)
    for item in systems:
        append(resolver.system_package(), "systems", item)

    return tuple(root.children[name].freeze() for name in sorted(root.children))


def iter_package_assignments(project: Project) -> Iterable[tuple[str, str, str | None, str]]:
    for item in project.baseTypes:
        yield PACKAGE_CATEGORY_BASE_TYPE, item.name, item.package, "base type"
    for item in project.implementationDataTypes:
        yield PACKAGE_CATEGORY_IMPLEMENTATION_DATA_TYPE, item.name, item.package, "implementation data type"
    for item in project.applicationDataTypes:
        yield PACKAGE_CATEGORY_APPLICATION_DATA_TYPE, item.name, item.package, "application data type"
    for item in project.units:
        yield PACKAGE_CATEGORY_UNIT, item.name, item.package, "unit"
    for item in project.compuMethods:
        yield PACKAGE_CATEGORY_COMPU_METHOD, item.name, item.package, "compu method"
    for item in project.modeDeclarationGroups:
        yield PACKAGE_CATEGORY_MODE_DECLARATION_GROUP, item.name, item.package, "mode declaration group"
    for item in project.interfaces:
        yield PACKAGE_CATEGORY_INTERFACE, item.name, item.package, "interface"
    for item in project.swcs:
        yield PACKAGE_CATEGORY_SWC, item.name, item.package, "SWC"
    for item in project.subcompositions:
        yield PACKAGE_CATEGORY_COMPOSITION, item.name, item.package, "subcomposition"
    yield PACKAGE_CATEGORY_SYSTEM, project.system.name, project.system.package, "system"


def package_namespace_groups(project: Project) -> Mapping[str, Sequence[tuple[str, str]]]:
    return {
        "datatype": (
            [(PACKAGE_CATEGORY_BASE_TYPE, item.name) for item in project.baseTypes]
            + [(PACKAGE_CATEGORY_IMPLEMENTATION_DATA_TYPE, item.name) for item in project.implementationDataTypes]
            + [(PACKAGE_CATEGORY_APPLICATION_DATA_TYPE, item.name) for item in project.applicationDataTypes]
        ),
        "interface": [(PACKAGE_CATEGORY_INTERFACE, item.name) for item in project.interfaces],
        "component": (
            [(PACKAGE_CATEGORY_SWC, item.name) for item in project.swcs]
            + [(PACKAGE_CATEGORY_COMPOSITION, item.name) for item in project.subcompositions]
        ),
        "unit": [(PACKAGE_CATEGORY_UNIT, item.name) for item in project.units],
        "compuMethod": [(PACKAGE_CATEGORY_COMPU_METHOD, item.name) for item in project.compuMethods],
        "modeDeclarationGroup": [(PACKAGE_CATEGORY_MODE_DECLARATION_GROUP, item.name) for item in project.modeDeclarationGroups],
        "system": [(PACKAGE_CATEGORY_SYSTEM, project.system.name)],
    }
