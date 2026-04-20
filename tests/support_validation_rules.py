from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


@validation_rule(
    code="MY-001",
    name="ProjectNameRule",
    description="Emits a deterministic project-level finding for profile tests.",
    tags=("tests", "profile"),
    default_severity="info",
)
def rule_project_name(context):
    return [
        Finding(
            code="MY-001-PROJECT",
            severity="info",
            message=f"Profile rule saw system '{context.project.system.name}'.",
            location=f"system:{context.project.system.name}",
        )
    ]


@validation_rule(
    code="MY-002",
    name="ComponentCountRule",
    description="Emits a deterministic component-count finding for profile tests.",
    tags=("tests", "profile"),
    default_severity="warning",
)
def rule_component_count(context):
    count = len(context.project.system.composition.components)
    return [
        Finding(
            code="MY-002-COMPONENT-COUNT",
            severity="warning",
            message=f"System defines {count} top-level component prototypes.",
            location=f"system:{context.project.system.name}",
        )
    ]
