# L3 Authoring Guide

L3 is where value-add logic lives. Every atom should read like it contains only what makes that atom unique. Frame concerns are inherited from L1 and L2.

---

## Choosing a Kind

Four kinds. Pick the one that matches the atom's fundamental nature.

**`PROCEDURAL`**
- **Use when**: the atom executes steps and returns a value.
- **Covers**: functions, handlers, CLI commands, API logic, event processors, pipeline stages, protocol handlers, solvers, utilities, calculations, validations.
- **Mental model**: call it, it does work, it returns a result or error.
- **This is the default.** If you're unsure, it's PROCEDURAL.

**`DECLARATIVE`**
- **Use when**: the atom describes desired state rather than steps to execute.
- **Covers**: database schemas, Terraform resources, infrastructure-as-code, config files, CSS definitions, migration scripts.
- **Mental model**: "make reality match this declaration." Idempotent by nature.
- **Key difference from PROCEDURAL**: no `logic` block, no `output`. The implementation reconciles current state with desired state.

**`COMPONENT`**
- **Use when**: the atom renders UI and holds local state.
- **Covers**: React/Vue/Svelte components, screens, forms, widgets, CLI TUI elements.
- **Mental model**: receives props from parent, manages local state, renders children, emits events upward.
- **Key difference from PROCEDURAL**: components compose other components, have a render tree, and don't "return" — they render continuously.

**`MODEL`**
- **Use when**: the atom is probabilistic.
- **Covers**: ML classifiers, prediction models, heuristic matchers, fuzzy matchers, recommendation engines.
- **Mental model**: not deterministic. Has acceptable bounds (precision, recall, latency) instead of exact outputs. Requires training data, drift monitoring, and a deterministic fallback.
- **Key difference from PROCEDURAL**: no `logic` block, no deterministic `failure_modes`. Correctness is defined by bounds, not by exact input→output mapping.

---

## Patterns for Previously-Separate Kinds

Some atom types that were previously separate kinds are now expressed as PROCEDURAL atoms with specific patterns.

### Event Processors (was REACTIVE)

An atom that processes stream events is a PROCEDURAL atom whose input is the event payload. Stream configuration (source, sink, ordering, backpressure) is declared on the L2 interface entry point that triggers the atom, not on the atom itself.

```yaml
# The atom: just processes one event
atom:
  kind: PROCEDURAL
  spec:
    input: reg.ord.OrderEvent
    output:
      success: reg.pay.PaymentRequest
      errors: [PAY.VAL.010]
    side_effects: [EMITS_EVENT]
    logic:
      - WHEN input.type == "order.placed" THEN EMIT payment.required WITH { order_id: input.id, amount: input.total }
      - WHEN input.type == "order.cancelled" THEN CALL atm.pay.cancel_pending WITH { order_id: input.id }
      - RETURN success
```

```yaml
# The interface (in L2 module): declares the stream binding
interface:
  entry_points:
    - kind: event_consumer
      event: order.*
      invokes: atm.pay.handle_order_event
```

### Pipeline Stages (was PIPELINE)

Each stage is a PROCEDURAL atom. The pipeline is an L4a orchestration wiring the stages together. Type matching between stages is validated at the orchestration level.

### Long-Running Processes (was PROCESS)

The tick logic is a PROCEDURAL atom. The loop, tick schedule, and termination condition are expressed in an L4a orchestration. Persistent state is passed as input and returned as output each tick.

### Protocol Handlers (was PROTOCOL)

A PROCEDURAL atom that takes `(current_state, message_in)` and returns `(new_state, message_out)`. The state machine is expressed in the atom's logic via guarded steps. Transition coverage is enforced through verification assertions.

### Solvers (was SOLVER)

A PROCEDURAL atom whose input includes decision variables and constraints, and whose output is the solution. Objective and solver parameters are part of the input or declared in invariants.

---

## Writing Atom Specs

### Input and Output

Reference L0.4 types wherever possible. If the exact type exists, reference it by ID. If the atom needs a unique shape, define inline fields:

```yaml
input:
  customer_id:
    type:     uuid
    nullable: false
  amount_cents:
    type:        bigint
    nullable:    false
    description: "Charge amount in USD cents."
```

### Side Effects

Getting markers right is critical — they determine which L1 conventions apply. Markers are defined in L0.6 — don't invent new ones in atoms.

- `PURE` — no side effects. Safe to cache, parallelize, retry freely. Mutually exclusive with every other marker, including `READS_CLOCK` (clock reads are observable state and break purity).
- `IDEMPOTENT` — has side effects but repeating with same input produces same result. Exempts from idempotency key requirements.
- `READS_DB` / `WRITES_DB` — database access. `WRITES_DB` triggers audit and idempotency checks.
- `READS_CACHE` / `WRITES_CACHE` — cache access.
- `READS_FS` / `WRITES_FS` — filesystem access. `WRITES_FS` triggers audit.
- `READS_ARTIFACT` — reads an L3 artifact (dataset, weights, config bundle). Required on MODEL atoms that load training data or weights, and on any atom that consumes a declared artifact.
- `EMITS_EVENT` — publishes events. Triggers audit.
- `CALLS_EXTERNAL` — third-party service call. Triggers audit and idempotency checks. Atoms with this marker must also list the corresponding L0.7 schema ID in their module's `access_permissions.external_schemas`.
- `READS_CLOCK` — reads current time. Output depends on when called.

An atom can have multiple markers: `[WRITES_DB, EMITS_EVENT, CALLS_EXTERNAL]`.

### Logic (PROCEDURAL only)

Write as guarded steps. Every step must be explicit.

**Bad**: `"Validate the charge request."`

**Good**: `"WHEN input.amount_cents <= 0 THEN RETURN PAY.VAL.001"`

Every condition references typed fields. Every action uses defined forms. Every path terminates.

### References inside logic

- **Constants**: `const.MAX_CHARGE_CENTS` — must resolve to an L0.5 entry.
- **External services**: `external.stripe.charge` — `stripe` must exist in L0.7 and in the module's `access_permissions.external_schemas`.
- **Other atoms**: `CALL atm.usr.fetch_customer` — must resolve; cross-module calls must be whitelisted.

### Failure Modes

Map specific triggers to error codes. Recovery comes from L1 convention based on error category — not specified here.

```yaml
failure_modes:
  - trigger: "input.amount_cents <= 0"
    error:   PAY.VAL.001
  - trigger: "Stripe API timeout"
    error:   PAY.NET.001
```

### Verification

Meet L1 floors, then add atom-specific content.

**`property_assertions`** — universal truths. "Output amount never exceeds input amount."

**`example_cases`** — concrete pairs. Happy path, common failure, edge case.

**`edge_cases`** — boundary descriptions. "Amount is exactly MAX_CHARGE_CENTS." "Stripe returns 503."

MODEL atoms additionally require `bounds_verification` describing how acceptable_bounds are tested.

### Convention Overrides vs Policy Overrides

Two distinct override mechanisms. Don't confuse them.

- `convention_overrides` — adjusts L1 conventions (retry count, log level, idempotency TTL). Uses field/value/justification. Field path must be listed in L1 `overrides.allowed_fields`.
- `policy_overrides` — opts out of a specific L2 policy applied to the module. Uses policy/action/justification. Only legal if the policy's `opt_out.allowed` is `true`.

Example — atom that retries NET errors 5 times instead of the project default 3:

```yaml
convention_overrides:
  - field:         "failure.defaults.NET.retries"
    value:         5
    justification: "Payment processor SLA tolerates up to 30s; 3 retries only cover ~15s."
```

---

## Writing Artifact Specs

**`format`** — what kind of data: `parquet`, `json`, `csv`, `binary`, `weights`.

**`schema`** — shape of content. L0.4 type reference for structured data, null for opaque blobs.

**`provenance`** — how created. Atom ID if system-generated, `"external"` if third-party, `"manual"` if hand-created.

**`consumers`** — which atoms depend on it. Critical for impact analysis.

---

## Common Authoring Mistakes

1. **Wrong kind.** If it describes desired state, it's DECLARATIVE, not PROCEDURAL. If it renders UI, it's COMPONENT. If it's probabilistic, it's MODEL.
2. **Missing side-effect markers.** No `WRITES_DB` means no audit, no idempotency check.
3. **Vague logic steps.** "Process the data" is not a step. Reference typed fields, use defined actions.
4. **Failure modes with wrong module prefix.** `atm.pay.*` atoms return `PAY.*` errors only.
5. **COMPONENT composing non-COMPONENT.** A button cannot contain a database migration.
6. **MODEL without fallback.** Every model needs a deterministic path for low confidence.
7. **Orphan atoms.** Not listed in any module's `owned_atoms` = validation failure.
8. **Trying to use a fifth kind.** If it doesn't fit four kinds, decompose it. A game loop is a PROCEDURAL tick atom + an L4a orchestration. A protocol is a PROCEDURAL handler with state passed in.
9. **External service call without `access_permissions.external_schemas` entry.** L2 and L3 both have to agree: the module must list the schema, the atom must use `external.<schema_id>` in logic.
10. **Confusing `convention_overrides` with `policy_overrides`.** One targets L1 conventions, the other targets L2 policies. Not interchangeable.
