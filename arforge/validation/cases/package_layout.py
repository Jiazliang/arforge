"""Package-layout semantic validation cases.

This module contains export-layout validation rules that verify external
package layout defaults, explicit package assignments, and resolved ARXML path
uniqueness across packageable model elements.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List

from ...arxml_paths import (
    ALL_PACKAGE_CATEGORIES,
    SUPPORTED_PACKAGE_CATEGORIES,
    iter_package_assignments,
    package_namespace_groups,
    validate_package_path_syntax,
)
from ...semantic_validation import Finding, ValidationCase, ValidationContext


class PackageLayoutCase(ValidationCase):
    case_id = "CORE-005"
    name = "PackageLayout"
    description = "Checks external package layout defaults, allowed packages, syntax, and resolved ARXML path uniqueness."
    tags = ("core", "export", "layout")

    def run(self, ctx: ValidationContext) -> List[Finding]:
        findings: List[Finding] = []
        layout = ctx.project.packageLayout
        defaults = ctx.path_resolver.defaults
        allowed_packages = set(ctx.path_resolver.allowed_packages)

        for package_path in sorted(layout.allowedPackages):
            for error in validate_package_path_syntax(package_path):
                findings.append(
                    self.finding(
                        f"Package layout allowedPackages entry '{package_path}' {error}.",
                        code="CORE-005-ALLOWED-PACKAGE-SYNTAX",
                    )
                )

        for category in SUPPORTED_PACKAGE_CATEGORIES:
            if category not in defaults:
                findings.append(
                    self.finding(
                        f"Package layout is missing a default package for category '{category}'.",
                        code="CORE-005-MISSING-DEFAULT",
                    )
                )
                continue
            default_package = defaults[category]
            for error in validate_package_path_syntax(default_package):
                findings.append(
                    self.finding(
                        f"Package layout default '{category}: {default_package}' {error}.",
                        code="CORE-005-DEFAULT-SYNTAX",
                    )
                )
            if default_package not in allowed_packages:
                findings.append(
                    self.finding(
                        f"Package layout default '{category}: {default_package}' is not listed in allowedPackages.",
                        code="CORE-005-DEFAULT-NOT-ALLOWED",
                    )
                )

        for category, name, explicit_package, label in iter_package_assignments(ctx.project):
            if explicit_package is None:
                continue
            for error in validate_package_path_syntax(explicit_package):
                findings.append(
                    self.finding(
                        f"{label.capitalize()} '{name}' package '{explicit_package}' {error}.",
                        code="CORE-005-EXPLICIT-PACKAGE-SYNTAX",
                    )
                )
            if explicit_package not in allowed_packages:
                findings.append(
                    self.finding(
                        f"{label.capitalize()} '{name}' package '{explicit_package}' is not listed in allowedPackages.",
                        code="CORE-005-EXPLICIT-PACKAGE-NOT-ALLOWED",
                    )
                )
            if category not in ALL_PACKAGE_CATEGORIES:
                findings.append(
                    self.finding(
                        f"Unsupported package category '{category}' on element '{name}'.",
                        code="CORE-005-UNSUPPORTED-CATEGORY",
                    )
                )

        namespace_paths: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for namespace, members in package_namespace_groups(ctx.project).items():
            for category, name in members:
                if category == "baseType":
                    resolved = ctx.path_resolver.base_type(name)
                elif category == "implementationDataType":
                    resolved = ctx.path_resolver.implementation_type(name)
                elif category == "applicationDataType":
                    resolved = ctx.path_resolver.application_type(name)
                elif category == "interface":
                    resolved = ctx.path_resolver.interface(name)
                elif category == "swc":
                    resolved = ctx.path_resolver.swc(name)
                elif category == "composition":
                    resolved = ctx.path_resolver.composition(name)
                elif category == "unit":
                    resolved = ctx.path_resolver.unit(name)
                elif category == "compuMethod":
                    resolved = ctx.path_resolver.compu_method(name)
                elif category == "modeDeclarationGroup":
                    resolved = ctx.path_resolver.mode_group(name)
                elif category == "system":
                    resolved = ctx.path_resolver.system(name)
                else:
                    continue
                namespace_paths[namespace][resolved].append(name)

        for namespace in sorted(namespace_paths):
            for resolved_path, names in sorted(namespace_paths[namespace].items()):
                if len(names) > 1:
                    findings.append(
                        self.finding(
                            f"Package layout resolves multiple {namespace} elements to the same ARXML path '{resolved_path}': {', '.join(sorted(names))}.",
                            code="CORE-005-DUPLICATE-ARXML-PATH",
                        )
                    )

        return findings
