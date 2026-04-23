"""Sample stricter project-policy rules for validation profile onboarding."""

from __future__ import annotations

from arforge.semantic_validation import Finding, validation_rule


def _error(code: str, message: str, location: str) -> Finding:
    return Finding(code=code, severity="error", message=message, location=location)


@validation_rule(
    code="PRJ-201",
    name="StrictUnconnectedPorts",
    description="Treats unconnected instantiated ports as project-policy errors.",
    tags=("sample", "hygiene", "connectivity"),
    default_severity="error",
)
def rule_error_on_unconnected_ports(context):
    findings: list[Finding] = []

    for instance in sorted(context.project.system.composition.components, key=lambda item: item.name):
        swc = context.find_instance_swc(instance.name)
        if swc is None:
            continue

        for port in sorted(swc.ports, key=lambda item: item.name):
            connectivity = context.find_instance_port_connectivity(instance.name, port.name)
            if connectivity is None:
                continue

            if port.direction == "provides" and not connectivity.outgoing_connectors:
                findings.append(
                    _error(
                        "PRJ-201-PORT-UNCONNECTED",
                        f"Port '{instance.name}.{port.name}' is unconnected; strict hygiene requires every provides port to be wired.",
                        f"system.component:{instance.name}.port:{port.name}",
                    )
                )
            if port.direction == "requires" and not connectivity.incoming_connectors:
                findings.append(
                    _error(
                        "PRJ-201-PORT-UNCONNECTED",
                        f"Port '{instance.name}.{port.name}' is unconnected; strict hygiene requires every requires port to be wired.",
                        f"system.component:{instance.name}.port:{port.name}",
                    )
                )

    return findings


@validation_rule(
    code="PRJ-202",
    name="StrictUnusedPorts",
    description="Treats declared or connected-but-unused ports as project-policy errors.",
    tags=("sample", "hygiene", "usage"),
    default_severity="error",
)
def rule_error_on_unused_ports(context):
    findings: list[Finding] = []

    for swc in sorted(context.project.swcs, key=lambda item: item.name):
        mode_switch_analysis = {
            analysis.port.name: analysis
            for analysis in context.iter_mode_switch_requires_port_analysis(swc.name)
        }
        connected_instances = tuple(sorted(context.instances_by_swc_name.get(swc.name, []), key=lambda item: item.name))

        for declared_usage in context.iter_declared_port_usage(swc.name):
            port = declared_usage.port
            usage = declared_usage.usage

            if port.interfaceType == "senderReceiver":
                if port.direction == "provides" and not usage.writes:
                    findings.append(
                        _error(
                            "PRJ-202-PORT-UNUSED",
                            f"Port '{swc.name}.{port.name}' is declared but no runnable writes to it.",
                            f"swc:{swc.name}.port:{port.name}",
                        )
                    )
                if port.direction == "requires" and not usage.reads and not usage.data_receive_events:
                    findings.append(
                        _error(
                            "PRJ-202-PORT-UNUSED",
                            f"Port '{swc.name}.{port.name}' is declared but no runnable reads or dataReceiveEvents use it.",
                            f"swc:{swc.name}.port:{port.name}",
                        )
                    )

            if port.interfaceType == "clientServer":
                if port.direction == "provides" and not usage.operation_invoked_events:
                    findings.append(
                        _error(
                            "PRJ-202-PORT-UNUSED",
                            f"Port '{swc.name}.{port.name}' is declared but no runnable operationInvokedEvent binds it.",
                            f"swc:{swc.name}.port:{port.name}",
                        )
                    )
                if port.direction == "requires" and not usage.calls:
                    findings.append(
                        _error(
                            "PRJ-202-PORT-UNUSED",
                            f"Port '{swc.name}.{port.name}' is declared but no runnable call uses it.",
                            f"swc:{swc.name}.port:{port.name}",
                        )
                    )

            if port.interfaceType == "modeSwitch" and port.direction == "requires":
                analysis = mode_switch_analysis.get(port.name)
                if analysis is None or analysis.usage.mode_switch_events:
                    continue
                findings.append(
                    _error(
                        "PRJ-202-PORT-UNUSED",
                        f"Port '{swc.name}.{port.name}' is declared but no runnable modeSwitchEvents use it.",
                        f"swc:{swc.name}.port:{port.name}",
                    )
                )

            for instance in connected_instances:
                connectivity = context.find_instance_port_connectivity(instance.name, port.name)
                if connectivity is None or not connectivity.is_connected:
                    continue

                if port.interfaceType == "senderReceiver":
                    if port.direction == "provides" and not usage.writes:
                        findings.append(
                            _error(
                                "PRJ-202-CONNECTED-PORT-UNUSED",
                                f"Connected port '{instance.name}.{port.name}' is wired but no runnable writes to it.",
                                f"system.component:{instance.name}.port:{port.name}",
                            )
                        )
                    if port.direction == "requires" and not usage.reads and not usage.data_receive_events:
                        findings.append(
                            _error(
                                "PRJ-202-CONNECTED-PORT-UNUSED",
                                f"Connected port '{instance.name}.{port.name}' is wired but no runnable reads or dataReceiveEvents use it.",
                                f"system.component:{instance.name}.port:{port.name}",
                            )
                        )

                if port.interfaceType == "clientServer":
                    if port.direction == "provides" and not usage.operation_invoked_events:
                        findings.append(
                            _error(
                                "PRJ-202-CONNECTED-PORT-UNUSED",
                                f"Connected port '{instance.name}.{port.name}' is wired but no runnable operationInvokedEvent uses it.",
                                f"system.component:{instance.name}.port:{port.name}",
                            )
                        )
                    if port.direction == "requires" and not usage.calls:
                        findings.append(
                            _error(
                                "PRJ-202-CONNECTED-PORT-UNUSED",
                                f"Connected port '{instance.name}.{port.name}' is wired but no runnable call uses it.",
                                f"system.component:{instance.name}.port:{port.name}",
                            )
                        )

                if port.interfaceType == "modeSwitch" and port.direction == "requires":
                    analysis = mode_switch_analysis.get(port.name)
                    if analysis is None or analysis.usage.mode_switch_events:
                        continue
                    findings.append(
                        _error(
                            "PRJ-202-CONNECTED-PORT-UNUSED",
                            f"Connected port '{instance.name}.{port.name}' is wired but no runnable modeSwitchEvents use it.",
                            f"system.component:{instance.name}.port:{port.name}",
                        )
                    )

    return findings


@validation_rule(
    code="PRJ-203",
    name="CompositionHygiene",
    description="Checks a few small project-level composition hygiene conventions.",
    tags=("sample", "hygiene", "composition"),
    default_severity="error",
)
def rule_require_composition_hygiene(context):
    findings: list[Finding] = []

    composition = context.project.system.composition
    if not composition.name.startswith("Composition_"):
        findings.append(
            _error(
                "PRJ-203-COMPOSITION-NAME",
                (
                    f"Top-level composition '{composition.name}' should start with 'Composition_' "
                    "to make generated artifacts easier to scan."
                ),
                f"system.composition:{composition.name}",
            )
        )

    instance_names = [instance.name for instance in composition.components]
    if len(set(instance_names)) != len(instance_names):
        findings.append(
            _error(
                "PRJ-203-DUPLICATE-INSTANCE-NAME",
                "Top-level composition contains duplicate instance names.",
                f"system.composition:{composition.name}",
            )
        )

    return findings
