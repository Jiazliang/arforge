# Modes Example

This project focuses on mode-switch modeling.

It highlights:

- a `ModeDeclarationGroup`
- a mode-switch interface that references that group
- a provider SWC that publishes the current mode
- a user SWC that reacts through `modeSwitchEvents`
- a small system composition that wires the provider to the user

Entry point: `examples/features/modes/autosar.project.yaml`
