"""Model diff rendering for high-level ARForge project structure.

This module compares two loaded ARForge project models, normalizes the
review-relevant structural entities, and renders a deterministic Markdown
summary through the shared Jinja2 templating approach used elsewhere.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .exporter import _sort_project_for_export
from .model import ComponentPrototype, Connection, DelegationConnector, Port, Project, SubcompositionType


MODEL_DIFF_TEMPLATE = "reports/model_diff.md.j2"


def _env(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def _connector_label(connector: Connection) -> str:
    return f"{connector.from_instance}.{connector.from_port} -> {connector.to_instance}.{connector.to_port}"


def _delegation_label(connector: DelegationConnector) -> str:
    return f"{connector.inner_instance}.{connector.inner_port} => {connector.outer_port}"


def _port_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (item["owner"], item["name"])


def _interface_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (item["kind"], item["name"])


def _prototype_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (item["scope"], item["name"])


def _connector_sort_key(item: dict[str, Any]) -> str:
    return item["label"]


def _changed_sort_key(item: dict[str, Any]) -> tuple[str, ...]:
    if "owner" in item:
        return (item["owner"], item["name"])
    if "scope" in item:
        return (item["scope"], item["name"])
    return (item["name"],)


def _change_rows(changes: dict[str, tuple[Any, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "field": field,
            "before": before,
            "after": after,
        }
        for field, (before, after) in sorted(changes.items())
    ]


def _normalize_port(owner: str, port: Port) -> dict[str, Any]:
    return {
        "owner": owner,
        "name": port.name,
        "direction": port.direction,
        "interface_ref": port.interfaceRef,
        "kind": port.interfaceType,
        "label": f"{owner}.{port.name}",
    }


def _normalize_prototype(scope: str, prototype: ComponentPrototype) -> dict[str, Any]:
    return {
        "scope": scope,
        "name": prototype.name,
        "type_ref": prototype.typeRef,
        "label": f"{scope}: {prototype.name}",
    }


def _normalize_connector(scope: str, connector: Connection) -> dict[str, Any]:
    return {
        "scope": scope,
        "label": f"{scope}: {_connector_label(connector)}",
    }


def _normalize_delegation(scope: str, connector: DelegationConnector) -> dict[str, Any]:
    return {
        "scope": scope,
        "label": f"{scope}: {_delegation_label(connector)}",
    }


def _normalize_subcomposition(subcomposition: SubcompositionType) -> dict[str, Any]:
    return {
        "name": subcomposition.name,
        "component_names": sorted(component.name for component in subcomposition.components),
        "port_names": sorted(port.name for port in subcomposition.ports),
        "delegation_labels": sorted(_delegation_label(connector) for connector in subcomposition.delegationConnectors),
    }


def _added_removed(
    old_map: dict[str, dict[str, Any]],
    new_map: dict[str, dict[str, Any]],
    *,
    sort_key,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    added = [new_map[key] for key in sorted(set(new_map) - set(old_map))]
    removed = [old_map[key] for key in sorted(set(old_map) - set(new_map))]
    return sorted(added, key=sort_key), sorted(removed, key=sort_key)


def _port_changes(old_map: dict[str, dict[str, Any]], new_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for key in sorted(set(old_map) & set(new_map)):
        old_item = old_map[key]
        new_item = new_map[key]
        changes: dict[str, tuple[Any, Any]] = {}
        if old_item["direction"] != new_item["direction"]:
            changes["direction"] = (old_item["direction"], new_item["direction"])
        if old_item["interface_ref"] != new_item["interface_ref"]:
            changes["interfaceRef"] = (old_item["interface_ref"], new_item["interface_ref"])
        if old_item["kind"] != new_item["kind"]:
            changes["kind"] = (old_item["kind"], new_item["kind"])
        if changes:
            changed.append(
                {
                    "owner": old_item["owner"],
                    "name": old_item["name"],
                    "label": old_item["label"],
                    "changes": _change_rows(changes),
                }
            )
    return sorted(changed, key=_changed_sort_key)


def _prototype_changes(old_map: dict[str, dict[str, Any]], new_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for key in sorted(set(old_map) & set(new_map)):
        old_item = old_map[key]
        new_item = new_map[key]
        if old_item["type_ref"] != new_item["type_ref"]:
            changed.append(
                {
                    "scope": old_item["scope"],
                    "name": old_item["name"],
                    "label": old_item["label"],
                    "changes": _change_rows({"typeRef": (old_item["type_ref"], new_item["type_ref"])}),
                }
            )
    return sorted(changed, key=_changed_sort_key)


def _interface_changes(old_map: dict[str, dict[str, Any]], new_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for name in sorted(set(old_map) & set(new_map)):
        old_item = old_map[name]
        new_item = new_map[name]
        if old_item["kind"] != new_item["kind"]:
            changed.append(
                {
                    "name": name,
                    "changes": _change_rows({"kind": (old_item["kind"], new_item["kind"])}),
                }
            )
    return changed


def _subcomposition_changes(old_map: dict[str, dict[str, Any]], new_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for name in sorted(set(old_map) & set(new_map)):
        old_item = old_map[name]
        new_item = new_map[name]
        changes: dict[str, tuple[Any, Any]] = {}
        if old_item["component_names"] != new_item["component_names"]:
            changes["contained prototypes"] = (
                ", ".join(old_item["component_names"]) or "(none)",
                ", ".join(new_item["component_names"]) or "(none)",
            )
        if old_item["port_names"] != new_item["port_names"]:
            changes["composition ports"] = (
                ", ".join(old_item["port_names"]) or "(none)",
                ", ".join(new_item["port_names"]) or "(none)",
            )
        if old_item["delegation_labels"] != new_item["delegation_labels"]:
            changes["delegation connectors"] = (
                ", ".join(old_item["delegation_labels"]) or "(none)",
                ", ".join(new_item["delegation_labels"]) or "(none)",
            )
        if changes:
            changed.append(
                {
                    "name": name,
                    "changes": _change_rows(changes),
                }
            )
    return changed


def build_model_diff_context(
    old_project: Project,
    new_project: Project,
    *,
    old_project_path: str | Path | None = None,
    new_project_path: str | Path | None = None,
) -> dict[str, Any]:
    old_project = _sort_project_for_export(old_project)
    new_project = _sort_project_for_export(new_project)

    old_swcs = {swc.name: {"name": swc.name} for swc in old_project.swcs}
    new_swcs = {swc.name: {"name": swc.name} for swc in new_project.swcs}
    swc_added, swc_removed = _added_removed(old_swcs, new_swcs, sort_key=lambda item: item["name"])

    old_interfaces_by_name = {interface.name: {"name": interface.name, "kind": interface.type} for interface in old_project.interfaces}
    new_interfaces_by_name = {interface.name: {"name": interface.name, "kind": interface.type} for interface in new_project.interfaces}
    interface_changed = _interface_changes(old_interfaces_by_name, new_interfaces_by_name)

    old_interfaces_full = {
        f"{interface.type}:{interface.name}": {"name": interface.name, "kind": interface.type}
        for interface in old_project.interfaces
    }
    new_interfaces_full = {
        f"{interface.type}:{interface.name}": {"name": interface.name, "kind": interface.type}
        for interface in new_project.interfaces
    }
    interface_added, interface_removed = _added_removed(old_interfaces_full, new_interfaces_full, sort_key=_interface_sort_key)

    old_ports = {
        f"{swc.name}:{port.name}": _normalize_port(swc.name, port)
        for swc in old_project.swcs
        for port in swc.ports
    }
    old_ports.update(
        {
            f"{subcomposition.name}:{port.name}": _normalize_port(subcomposition.name, port)
            for subcomposition in old_project.subcompositions
            for port in subcomposition.ports
        }
    )
    new_ports = {
        f"{swc.name}:{port.name}": _normalize_port(swc.name, port)
        for swc in new_project.swcs
        for port in swc.ports
    }
    new_ports.update(
        {
            f"{subcomposition.name}:{port.name}": _normalize_port(subcomposition.name, port)
            for subcomposition in new_project.subcompositions
            for port in subcomposition.ports
        }
    )
    port_added, port_removed = _added_removed(old_ports, new_ports, sort_key=_port_sort_key)
    port_changed = _port_changes(old_ports, new_ports)

    old_prototypes = {
        f"system:{prototype.name}": _normalize_prototype("system", prototype)
        for prototype in old_project.system.composition.components
    }
    for subcomposition in old_project.subcompositions:
        old_prototypes.update(
            {
                f"{subcomposition.name}:{prototype.name}": _normalize_prototype(subcomposition.name, prototype)
                for prototype in subcomposition.components
            }
        )
    new_prototypes = {
        f"system:{prototype.name}": _normalize_prototype("system", prototype)
        for prototype in new_project.system.composition.components
    }
    for subcomposition in new_project.subcompositions:
        new_prototypes.update(
            {
                f"{subcomposition.name}:{prototype.name}": _normalize_prototype(subcomposition.name, prototype)
                for prototype in subcomposition.components
            }
        )
    prototype_added, prototype_removed = _added_removed(old_prototypes, new_prototypes, sort_key=_prototype_sort_key)
    prototype_changed = _prototype_changes(old_prototypes, new_prototypes)

    old_connectors = {
        f"system:{_connector_label(connector)}": _normalize_connector("system", connector)
        for connector in old_project.system.composition.connectors
    }
    for subcomposition in old_project.subcompositions:
        old_connectors.update(
            {
                f"{subcomposition.name}:{_connector_label(connector)}": _normalize_connector(subcomposition.name, connector)
                for connector in subcomposition.connectors
            }
        )
        old_connectors.update(
            {
                f"{subcomposition.name}:delegation:{_delegation_label(connector)}": _normalize_delegation(subcomposition.name, connector)
                for connector in subcomposition.delegationConnectors
            }
        )
    new_connectors = {
        f"system:{_connector_label(connector)}": _normalize_connector("system", connector)
        for connector in new_project.system.composition.connectors
    }
    for subcomposition in new_project.subcompositions:
        new_connectors.update(
            {
                f"{subcomposition.name}:{_connector_label(connector)}": _normalize_connector(subcomposition.name, connector)
                for connector in subcomposition.connectors
            }
        )
        new_connectors.update(
            {
                f"{subcomposition.name}:delegation:{_delegation_label(connector)}": _normalize_delegation(subcomposition.name, connector)
                for connector in subcomposition.delegationConnectors
            }
        )
    connector_added, connector_removed = _added_removed(old_connectors, new_connectors, sort_key=_connector_sort_key)

    old_subcompositions = {subcomposition.name: _normalize_subcomposition(subcomposition) for subcomposition in old_project.subcompositions}
    new_subcompositions = {subcomposition.name: _normalize_subcomposition(subcomposition) for subcomposition in new_project.subcompositions}
    subcomposition_added, subcomposition_removed = _added_removed(
        old_subcompositions,
        new_subcompositions,
        sort_key=lambda item: item["name"],
    )
    subcomposition_changed = _subcomposition_changes(old_subcompositions, new_subcompositions)

    counts = {
        "swcs_added": len(swc_added),
        "swcs_removed": len(swc_removed),
        "interfaces_added": len(interface_added),
        "interfaces_removed": len(interface_removed),
        "interfaces_changed": len(interface_changed),
        "ports_added": len(port_added),
        "ports_removed": len(port_removed),
        "ports_changed": len(port_changed),
        "prototypes_added": len(prototype_added),
        "prototypes_removed": len(prototype_removed),
        "prototypes_changed": len(prototype_changed),
        "connectors_added": len(connector_added),
        "connectors_removed": len(connector_removed),
        "subcompositions_added": len(subcomposition_added),
        "subcompositions_removed": len(subcomposition_removed),
        "subcompositions_changed": len(subcomposition_changed),
    }
    total_changes = sum(counts.values())

    return {
        "report": {
            "old_project_path": str(old_project_path) if old_project_path is not None else None,
            "new_project_path": str(new_project_path) if new_project_path is not None else None,
            "old_system_name": old_project.system.name,
            "new_system_name": new_project.system.name,
        },
        "summary": {
            "counts": counts,
            "total_changes": total_changes,
            "has_changes": total_changes > 0,
        },
        "swcs": {
            "added": swc_added,
            "removed": swc_removed,
        },
        "interfaces": {
            "added": interface_added,
            "removed": interface_removed,
            "changed": interface_changed,
        },
        "ports": {
            "added": port_added,
            "removed": port_removed,
            "changed": port_changed,
        },
        "component_prototypes": {
            "added": prototype_added,
            "removed": prototype_removed,
            "changed": prototype_changed,
        },
        "connectors": {
            "added": connector_added,
            "removed": connector_removed,
        },
        "subcompositions": {
            "added": subcomposition_added,
            "removed": subcomposition_removed,
            "changed": subcomposition_changed,
        },
        "notes": [
            "This diff summarizes high-level structure only. It does not perform semantic validation; use `arforge validate` separately.",
            "Connectors whose endpoints change are reported as removed and added.",
            "SWC rename inference is intentionally conservative in the first version. Uncertain cases appear as removed and added.",
        ],
    }


def render_model_diff(
    old_project: Project,
    new_project: Project,
    *,
    template_dir: Path,
    old_project_path: str | Path | None = None,
    new_project_path: str | Path | None = None,
    template_name: str = MODEL_DIFF_TEMPLATE,
) -> str:
    context = build_model_diff_context(
        old_project,
        new_project,
        old_project_path=old_project_path,
        new_project_path=new_project_path,
    )
    env = _env(template_dir)
    template = env.get_template(template_name)
    rendered = template.render(**context)
    rendered = re.sub(r"\n{3,}", "\n\n", rendered)
    return rendered.rstrip() + "\n"


def write_model_diff(
    old_project: Project,
    new_project: Project,
    *,
    template_dir: Path,
    out: Path,
    old_project_path: str | Path | None = None,
    new_project_path: str | Path | None = None,
    template_name: str = MODEL_DIFF_TEMPLATE,
) -> Path:
    rendered = render_model_diff(
        old_project,
        new_project,
        template_dir=template_dir,
        old_project_path=old_project_path,
        new_project_path=new_project_path,
        template_name=template_name,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    return out
