from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="MY-001",
    name="SwcPascalCaseNames",
    description="Checks that SWC type names start with an uppercase letter.",
    tags=("project", "naming", "swc"),
    default_severity="warning",
)
def rule_check_swc_naming(context):
    findings: list[Finding] = []
    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        if not swc.name or not swc.name[0].isupper():
            findings.append(
                Finding(
                    code="MY-001-SWC-NAME",
                    severity="warning",
                    message=f"SWC '{swc.name}' must start with an uppercase letter.",
                    location=f"swc:{swc.name}",
                )
            )
    return findings


@validation_rule(
    code="MY-002",
    name="InstanceNumericSuffix",
    description="Checks that top-level instance names include a numeric suffix after an underscore.",
    tags=("project", "naming", "system"),
    default_severity="warning",
)
def rule_require_instance_suffix(context):
    findings: list[Finding] = []
    for instance in sorted(context.project.system.composition.components, key=lambda item: item.name):
        head, separator, tail = instance.name.rpartition("_")
        if not head or separator != "_" or not tail.isdigit():
            findings.append(
                Finding(
                    code="MY-002-INSTANCE-SUFFIX",
                    severity="warning",
                    message=(
                        f"System instance '{instance.name}' should end with an underscore and numeric suffix, "
                        "for example 'SpeedSensor_0'."
                    ),
                    location=f"system.component:{instance.name}",
                )
            )
    return findings
