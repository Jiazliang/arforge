# Validation

ARForge validates every project in two stages before allowing export. Both stages must pass for export to proceed.

## Stage 1 - Schema validation

Schema validation checks the structure of each YAML file against a JSON Schema. It catches missing required fields, wrong value types, and unsupported keys. Schema errors are reported immediately during loading, before semantic validation runs.

Schemas exist for every input category: aggregator manifests, base types, implementation types, application types, units, compu methods, mode declaration groups, interfaces, SWCs, subcompositions, system files, and validation profiles.

## Stage 2 - Semantic validation

Semantic validation checks the meaning of the model - cross-file references, type graph consistency, port compatibility, runnable access correctness, connectivity, and timing relationships. These are rules that JSON Schema cannot express.

Each semantic rule is implemented as a named `ValidationCase` with a stable `CORE-XXX` identifier. Rules are organized by domain under `arforge/validation/cases/`. They run in deterministic order and findings are sorted deterministically by severity, code, and message - so CI output is stable across runs.

Project-specific validation can be added through validation profiles without modifying core rule implementations. See [Validation Profiles](./validation-profiles.md).

### Finding structure

Every finding carries three fields:

- **code** - a stable `CORE-XXX-DETAIL` identifier
- **message** - a human-readable description of the problem
- **severity** - `error`, `warning`, or `info`

`arforge validate` exits with a non-zero code only when at least one `error` finding exists. Warnings and infos are reported but do not block export.

### Verbosity

```bash
arforge validate project.yaml        # findings + severity summary
arforge validate project.yaml -v     # adds per-case execution info
arforge validate project.yaml -vv    # adds case descriptions and full detail
```

---

## Validation rules

### CORE-001 - GlobalUniqueness
Checks that all globally named elements are unique across the project. Covers data type names, interface names, SWC names, subcomposition names, unit names, compu method names, system composition instance names, and duplicate component prototype names inside a subcomposition.

### CORE-002 - BaseTypeMetadata
Checks that base type definitions are internally consistent: no duplicate names, required fields present, valid bit length and signedness values.

### CORE-010 - InterfaceSemantics
Checks the internal structure of interface definitions and their type references.

Covers: SR data element type references, CS operation argument types and return types, CS possible error code validity, CS duplicate operation and argument names, mode-switch `modeGroupRef` resolution, struct field type resolution, struct cycles, array element type resolution, array length validity.

### CORE-011 - ApplicationConstraints
Checks that application data type constraints are valid given the backing implementation type. Covers: constraint min/max ordering, constraint values within base type range, constraint applicability (structs and arrays cannot carry constraints).

### CORE-012 - ModeDeclarationGroupStructure
Checks mode declaration group internal consistency: no duplicate group names, no duplicate mode names within a group, no empty mode names, no duplicate mode values, and `EXPLICIT_ORDER` completeness (`onTransitionValue` plus per-mode integer `value`).

### CORE-013 - ModeDeclarationGroupInitialMode
Checks that each `initialMode` references one of the declared modes in the same group.

### CORE-014 - UnusedModeDeclarationGroups
Warns when a mode declaration group is declared but never referenced by any mode-switch interface. An unused group has no effect on the model and likely indicates a leftover definition or a missing interface reference. Severity: **warning**.

### CORE-020 - SwcStructure
Checks SWC-local uniqueness: no duplicate runnable names, no duplicate port names within an SWC.

### CORE-021 - PortInterfaceReferences
Checks that every SWC port references an existing interface by name, and that the port kind matches the interface kind (e.g. a mode-switch port must reference a mode-switch interface).

### CORE-022 - RunnableAccessSemantics
Checks runnable `reads`, `writes`, and `calls` against port and interface semantics.

- `reads` must reference a `requires` port on an SR interface
- `writes` must reference a `provides` port on an SR interface
- `calls` must reference a `requires` port on a CS interface
- data element names must exist in the referenced interface
- operation names must exist in the referenced interface

### CORE-023 - OperationInvokedEvents
Checks `operationInvokedEvents` bindings: port must exist, port must be a `provides` CS port, operation must exist in the interface.

### CORE-024 - RunnableTriggerPolicy
Checks that every runnable has exactly one trigger. A runnable with both `timingEventMs` and `initEvent`, or with no trigger at all, is an error.

### CORE-025 - PortComSpecSemantics
Checks ComSpec on SWC ports against the port kind and call mode.

SR ComSpec rules: `mode` must be `implicit`, `explicit`, or `queued`. Queued ports require `queueLength >= 1`. Non-queued ports must not carry `queueLength`. SR ports must not carry CS fields.

Additional SR ComSpec constraints in the current export model:

- `initValue` is allowed only on `requires` sender-receiver ports
- queued sender-receiver ports must not define `initValue`
- sender-receiver ports using `comSpec` must reference an interface with exactly one data element, because export emits a single receiver `DATA-ELEMENT-REF`

CS ComSpec rules: `callMode` is required. Synchronous ports may carry `timeoutMs`; asynchronous ports must not. CS ports must not carry SR fields.

Mode-switch ports do not support ComSpec.

### CORE-026 - RunnableRaisedErrors
Checks `raisesErrors` declarations: port must be a `provides` CS port, operation must exist, error name must be declared in `possibleErrors` of that operation, operation binding must be unambiguous.

### CORE-027 - DataReceiveEvents
Checks `dataReceiveEvents` bindings: port must exist, must be a `requires` SR port, data element must exist in the interface.

### CORE-028 - ModeSwitchEvents
Checks `modeSwitchEvents` bindings: port must exist, must be a `requires` mode-switch port, the referenced mode must be declared in the resolved `ModeDeclarationGroup`.

### CORE-030 - SystemInstanceTypes
Checks that every component prototype in the top-level system composition references a known atomic SWC type or subcomposition type by name.

### CORE-031 - SubcompositionInstanceTypes
Checks that every component prototype inside a subcomposition resolves to a known atomic SWC type. Nested subcomposition instantiation is intentionally rejected in this first iteration.

### CORE-032 - SubcompositionConnectionSemantics
Checks every connector inside each subcomposition.

- both endpoint instances must exist within the subcomposition
- both endpoint ports must exist on the resolved atomic SWC types
- `from` port must be a `provides` port; `to` port must be a `requires` port
- both ports must reference the same interface
- interface kind must be consistent (SR-to-SR, CS-to-CS, MS-to-MS)
- duplicate port pairs are rejected

### CORE-033 - SubcompositionPortDefinitions
Checks subcomposition boundary port definitions.

- composition port names must be unique within the subcomposition
- `direction` must be `provides` or `requires`
- `interfaceRef` must resolve to an existing senderReceiver, clientServer, or modeSwitch interface
- open composition ports are allowed; this rule validates the port declarations themselves

### CORE-034 - SubcompositionDelegationConnectors
Checks delegation connectors inside each subcomposition.

- `outer` must reference a declared subcomposition composition port
- `inner` instance must exist inside the subcomposition
- `inner` port must exist on the resolved atomic SWC type
- outer and inner ports must have the same direction
- outer and inner ports must reference the same interface
- interface kind must be consistent (`senderReceiver`, `clientServer`, or `modeSwitch`)
- duplicate delegation mappings are rejected
- top-level connectors may only target declared subcomposition boundary ports, so undeclared inner-port bypass is rejected

### CORE-040 - ConnectionSemantics
Checks every connector in the top-level system composition.

- both endpoint instances must exist
- both endpoint ports must exist on those instances
- `from` port must be a `provides` port; `to` port must be a `requires` port
- both ports must reference the same interface
- interface kind must be consistent (SR-to-SR, CS-to-CS, MS-to-MS)
- duplicate port pairs are rejected

### CORE-041 - SenderReceiverConnectivity
Checks SR port connectivity and runnable usage against each other. A `provides` SR port with no outgoing connector produces a warning. A `requires` SR port that a runnable reads from but has no incoming connector produces a warning. Severity: **warning**.

### CORE-042 - SenderReceiverUsage
Warns when connected SR ports are never accessed by any runnable. These are design quality warnings. Severity: **warning**.

### CORE-043 - ClientServerConnectivity
Checks CS port connectivity against runnable behavior. A CS `requires` port that is called by a runnable but has no connector is an error. A CS `provides` port with an `operationInvokedEvent` but no incoming connector is an error. Severity: **error**.

### CORE-044 - ClientServerUsage
Warns when CS ports are connected but never used in runnable `calls` or `operationInvokedEvents`. Also warns when CS ports have no connector at all. Severity: **warning**.

### CORE-045 - SenderReceiverMultiplicity
Detects n:1 SR communication: multiple providers connected to a single sender-receiver `requires` port. AUTOSAR allows this, but it may indicate unclear data ownership or arbitration semantics. Severity: **warning**.

### CORE-046 - ModeSwitchConnectivity
Checks mode-switch port connectivity. A `provides` mode-switch port with no outgoing connector produces a warning. A `requires` mode-switch port with no incoming connector produces a warning. Severity: **warning**.

### CORE-047 - DeclaredPortUsage
Warns when a declared SWC port is never used by any runnable behavior, even before system connectors are considered. This is an SWC-level design quality check - a port that exists in the type definition but is never accessed by any runnable is likely unintentional.

Covers all interface kinds and both port directions: SR provides/requires, CS provides/requires, and mode-switch requires. Mode-switch provides ports are excluded from this check because provider-side mode behavior is not modeled in ARForge at the SWC level. Severity: **warning**.

### CORE-048 - ModeSwitchUsage
Warns when a connected mode-switch `requires` port is never used by any runnable `modeSwitchEvents`. A mode-switch port that is wired in the system composition but never triggers any runnable behavior is likely a design oversight. Severity: **warning**.

### CORE-050 - SRConsumerFasterThanProducer
Warns when a cyclic SR consumer runs at a shorter period than its connected cyclic SR producer. The consumer may read stale data on some cycles.

Example: producer at 10 ms, consumer at 5 ms -> `CORE-050` warning. Severity: **warning**.

### CORE-051 - SRProducerFasterThanConsumer
Warns when a cyclic SR producer runs at a shorter period than its connected cyclic SR consumer. The producer may overwrite intermediate values before the consumer reads them.

Example: producer at 5 ms, consumer at 10 ms -> `CORE-051` warning. Equal periods produce no finding. Severity: **warning**.

---

## Tests and fixtures

The `tests/` directory contains pytest coverage for all validation behavior. `examples/invalid/` contains a corpus of deliberately broken model fixtures - one per finding code - used to verify that each rule fires exactly when expected and not otherwise. See `examples/invalid/README.md` for the fixture naming convention and contribution guidance.

Every validation rule has explicit test cases for both valid and invalid inputs. This corpus is also useful as a reference for understanding exactly what each rule checks.

Checker-oriented `ModeDeclarationGroup` `EXPLICIT_ORDER` completeness is validated and exported consistently: the model requires `onTransitionValue` plus per-mode integer `value`, and both monolithic and split ARXML emit the same structure.
