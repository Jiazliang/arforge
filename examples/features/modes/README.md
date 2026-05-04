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
- runnable `modeConditions` are exported as AUTOSAR event-level `DISABLED-MODE-IREFS` on supported runnable event types by disabling the complement of the allowed modes.
- `modeConditions` are not supported on `initEvent` runnables.

Entry point: `examples/features/modes/autosar.project.yaml`
