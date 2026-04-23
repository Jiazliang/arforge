# Examples

This directory contains user-facing ARForge reference material plus the validation fixture corpus.

Folders:

- `minimal/` contains the clean starter project. It keeps the model intentionally small so first-time users can read it end to end.
- `features/` contains focused examples for specific capabilities, including sender-receiver, client-server, modes, subcomposition, and validation profiles.
- `invalid/` contains intentionally broken models used for validation testing. These are useful when working on validation behavior, but they are not good starting points for new users.

Practical guidance:

- begin with `examples/minimal/autosar.project.yaml`
- explore `examples/features/README.md` when you want a targeted capability example
- ignore `examples/invalid/` unless you are testing or developing validation rules
