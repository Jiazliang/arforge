"""Small sample naming-policy rules used by the validation profile examples."""

from __future__ import annotations

import re

from arforge.semantic_validation import Finding, validation_rule


_PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_INTERFACE_RE = re.compile(r"^If_[A-Z][A-Za-z0-9]*$")
_RUNNABLE_RE = re.compile(r"^Runnable_[A-Z][A-Za-z0-9]*$")
_INSTANCE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*_[0-9]+$")


def _warning(code: str, message: str, location: str) -> Finding:
    return Finding(code=code, severity="warning", message=message, location=location)


@validation_rule(
    code="PRJ-101",
    name="SwcNamingConvention",
    description="Checks that SWC type names use PascalCase.",
    tags=("sample", "naming", "swc"),
    default_severity="warning",
)
def rule_check_swc_names(context):
    findings: list[Finding] = []
    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        if _PASCAL_CASE_RE.match(swc.name):
            continue
        findings.append(
            _warning(
                "PRJ-101-SWC-NAME",
                f"SWC '{swc.name}' should use PascalCase, for example 'SpeedSensor'.",
                f"swc:{swc.name}",
            )
        )
    return findings


@validation_rule(
    code="PRJ-102",
    name="PortPrefixConvention",
    description="Checks that provides ports start with Pp_ and requires ports start with Rp_.",
    tags=("sample", "naming", "ports"),
    default_severity="warning",
)
def rule_check_port_prefixes(context):
    findings: list[Finding] = []
    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        for port in sorted(swc.ports, key=lambda item: item.name):
            expected_prefix = "Pp_" if port.direction == "provides" else "Rp_"
            if port.name.startswith(expected_prefix):
                continue
            findings.append(
                _warning(
                    "PRJ-102-PORT-PREFIX",
                    f"Port '{swc.name}.{port.name}' should start with '{expected_prefix}'.",
                    f"swc:{swc.name}.port:{port.name}",
                )
            )
    return findings


@validation_rule(
    code="PRJ-103",
    name="RunnableNamingConvention",
    description="Checks that runnable names use the Runnable_ prefix with PascalCase suffixes.",
    tags=("sample", "naming", "runnables"),
    default_severity="warning",
)
def rule_check_runnable_names(context):
    findings: list[Finding] = []
    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        for runnable in sorted(swc.runnables, key=lambda item: item.name):
            if _RUNNABLE_RE.match(runnable.name):
                continue
            findings.append(
                _warning(
                    "PRJ-103-RUNNABLE-NAME",
                    (
                        f"Runnable '{swc.name}.{runnable.name}' should use the "
                        "form 'Runnable_DoThing'."
                    ),
                    f"swc:{swc.name}.runnable:{runnable.name}",
                )
            )
    return findings


@validation_rule(
    code="PRJ-104",
    name="InterfaceNamingConvention",
    description="Checks that interface names start with If_.",
    tags=("sample", "naming", "interfaces"),
    default_severity="warning",
)
def rule_check_interface_names(context):
    findings: list[Finding] = []
    for interface in sorted(context.project.interfaces, key=lambda item: item.name):
        if _INTERFACE_RE.match(interface.name):
            continue
        findings.append(
            _warning(
                "PRJ-104-INTERFACE-NAME",
                f"Interface '{interface.name}' should start with 'If_'.",
                f"interface:{interface.name}",
            )
        )
    return findings


@validation_rule(
    code="PRJ-105",
    name="InstanceNamingConvention",
    description="Checks that top-level component instances use a <TypeLikeName>_<number> suffix.",
    tags=("sample", "naming", "system"),
    default_severity="warning",
)
def rule_check_instance_names(context):
    findings: list[Finding] = []
    for instance in sorted(context.project.system.composition.components, key=lambda item: item.name):
        if _INSTANCE_RE.match(instance.name):
            continue
        findings.append(
            _warning(
                "PRJ-105-INSTANCE-NAME",
                (
                    f"System instance '{instance.name}' should use a numeric suffix, "
                    "for example 'SpeedSensor_0'."
                ),
                f"system.component:{instance.name}",
            )
        )
    return findings
