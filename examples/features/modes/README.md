# Modes Example

This project focuses on mode-switch modeling.

It highlights:

- a `ModeDeclarationGroup`
- a mode-switch interface that references that group
- a provider SWC that publishes the current mode
- a user SWC that reacts through `modeSwitchEvents`
- a runnable constrained through `modeConditions`
- a small system composition that wires the provider to the user

Semantics used in this example:

- `modeSwitchEvents` means the runnable is triggered by a mode transition.
- `modeConditions` means the runnable is only intended to be active or valid in the listed modes.
- multiple modes on the same mode-switch port mean OR
- mode conditions across different mode-switch ports mean AND

Current export behavior:

- `modeSwitchEvents` are exported to ARXML.
- runnable `modeConditions` are currently modeled and validated by ARForge, but are not emitted as AUTOSAR mode-dependency XML yet.

Entry point: `examples/features/modes/autosar.project.yaml`
