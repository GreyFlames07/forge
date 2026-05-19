# L4 — Flows Schema

**Purpose**: Compose atoms into multi-step operations. Two sibling constructs: Orchestrations (internal) and Journeys (external-facing).

**Scope**: Per-flow, per-journey.

**File format**: YAML. Orchestrations at `L4_flows/<FLOW_ID>.yaml`. Journeys at `L4_journeys/<JOURNEY_ID>.yaml`.

---

## L4a — Orchestration Spec

Internal coordination of atoms. Handles sequencing, data passing, error branching, transactions, and compensation.

### Top-level structure

```yaml
orchestration:
  id:          <flow_id>
  description: <string>

  trigger:               { ... }
  transaction_boundary:  saga | acid | none
  sequence:              [...]
  state_transitions:     [...]
  verification_criteria: [...]
  changelog:             [...]
```

All sections mandatory.

---

### L4a.1 — Identity

```yaml
orchestration:
  id:          <flow_id>
  description: <string>
```

| Field | Description |
|---|---|
| `id` | Unique orchestration identifier. Must match `naming_ledger.flow_id`. |
| `description` | What this orchestration accomplishes end-to-end. Should describe the complete operation, not just list the steps. |

---

### L4a.2 — Trigger

What initiates the orchestration. Orchestrations are triggered internally — by events, by other flows, by schedules, or by direct invocation from an interface entry point.

```yaml
trigger:
  kind:         event | invocation | scheduled | manual
  event:        <event_name>
  payload_type: <type_id>
  schedule:     <cron_expression>
```

| Field | Description |
|---|---|
| `kind` | How this orchestration is initiated. `event` = triggered by an event on the bus. `invocation` = called directly by an interface entry point or another flow. `scheduled` = runs on a cron schedule. `manual` = triggered by operator action. |
| `event` | Required when `kind: event`. The event name that triggers this flow. Must match `naming_ledger.event_name`. |
| `payload_type` | Required when `kind: event` or `kind: invocation`. The L0.4 type of the data passed to the flow on initiation. |
| `schedule` | Required when `kind: scheduled`. Cron expression defining the schedule. |

---

### L4a.3 — Transaction Boundary

```yaml
transaction_boundary: saga | acid | none
```

| Field | Description |
|---|---|
| `transaction_boundary` | The consistency model for the flow. `acid` = all steps in a single database transaction; trivial rollback on failure. `saga` = no global transaction; each step may have a compensation atom; failure triggers reverse-order compensation of completed steps. `none` = no rollback; failures are reported but completed steps are not reversed. |

---

### L4a.4 — Sequence

The ordered list of steps. Each step invokes an atom or nested orchestration.

```yaml
sequence:
  - step:   <string>
    invoke: <atom_id | flow_id>
    with:   <binding_map>
    on_error:
      <error_code | pattern>: <error_action>
    compensation: <atom_id | null>
```

| Field | Description |
|---|---|
| `step` | Unique label within this orchestration. Used for referencing in `on_error` GOTO actions and in verification criteria. |
| `invoke` | The atom or nested orchestration to execute. Must resolve to a real entity. |
| `with` | Argument bindings. Pseudo-formal expressions that may reference `trigger.*` (the flow's trigger payload) or `<prior_step_label>.output.*` (output of a previous step). |
| `on_error` | Map of error code or pattern to action. Patterns use `*` for wildcard: `PAY.NET.*` matches all PAY networking errors. Actions described below. |
| `compensation` | Atom called if a later step fails (saga only). Set to `null` explicitly for steps that need no compensation (pure reads, non-mutating validations). Required to be non-null for side-effecting steps when `transaction_boundary: saga`. |

**Error actions:**

- `HALT` — stop the flow, report the error.
- `HALT_AND_EMIT <event_name>` — stop the flow, emit an event.
- `RETRY(max=<n>)` — retry this step up to n times.
- `GOTO step=<step_label>` — jump to a different step (typically a compensation or cleanup step).
- `CONTINUE` — ignore the error and proceed to the next step.
- `COMPENSATE_AND_HALT` — trigger reverse-order compensation of all completed steps, then halt.

**Reference forms inside `with` bindings:**

- `trigger.<field>` — field from the orchestration's trigger payload.
- `<step_label>.output.<field>` — field from a prior step's success output.

---

### L4a.5 — State Transitions

How observable state changes over the course of the orchestration.

```yaml
state_transitions:
  - on:     <string>
    change: <expression>
    emit:   <event_name>
```

| Field | Description |
|---|---|
| `on` | The outcome that triggers this state change. Pseudo-formal description of what happened (e.g., "all steps succeed", "charge fails after retry", "fulfill fails"). |
| `change` | What state changes. Pseudo-formal mutation (e.g., `order.status = FULFILLED`, `order.status = PAYMENT_FAILED`). |
| `emit` | Optional event emitted when this transition fires. Must match `naming_ledger.event_name`. |

---

### L4a.6 — Verification Criteria

The definition of done. What must be observably true after the flow completes, for each possible outcome.

```yaml
verification_criteria:
  - scenario: <string>
    asserts:  [<expression>, ...]
```

| Field | Description |
|---|---|
| `scenario` | Human description of the outcome being verified (e.g., "successful payment", "charge declined", "fulfillment failure with compensation"). |
| `asserts` | List of pseudo-formal rules that must hold after this scenario completes. Typically reference database state, emitted events, and downstream effects. |

---

### L4a.7 — Changelog

Standard changelog.

---

## L4b — Journey Spec

External-facing paths. A user, client, or external caller starts at an entry point, transitions between observable states via actions, and reaches a terminal state.

### Top-level structure

```yaml
journey:
  id:          <journey_id>
  description: <string>

  surface:               <surface_kind>
  entry_point:           { ... }
  states:                [...]
  exit_states:           [...]
  handlers:              { ... }
  transitions:           [...]
  verification_criteria: [...]
  changelog:             [...]
```

All sections mandatory.

---

### L4b.1 — Identity

```yaml
journey:
  id:          <journey_id>
  description: <string>
```

| Field | Description |
|---|---|
| `id` | Unique journey identifier. Must match `naming_ledger.journey_id`. |
| `description` | The complete user-facing path this journey represents. Should describe what the user is trying to accomplish, not just the technical steps. |

---

### L4b.2 — Surface

```yaml
surface: web_ui | mobile_ui | api | cli | conversation | email_sequence
```

| Field | Description |
|---|---|
| `surface` | The medium through which the journey occurs. Determines what kind of handlers and transitions are valid. |

---

### L4b.3 — Entry Point

```yaml
entry_point:
  from:           <string>
  initial_state:  <state_name>
  preconditions:  [<expression>, ...]
```

| Field | Description |
|---|---|
| `from` | Where the journey begins: a URL path, CLI command, API endpoint, conversation trigger, etc. Must match the L2 interface entry point that invokes this journey. |
| `initial_state` | The first state the journey enters. Must be in `states`. |
| `preconditions` | Optional. Conditions that must be true for the journey to start (e.g., "user is not already logged in"). |

---

### L4b.4 — States

```yaml
states:      [<state_name>, ...]
exit_states: [<state_name>, ...]
```

| Field | Description |
|---|---|
| `states` | All possible states the journey can be in. Each state has a handler (defined in `handlers`). |
| `exit_states` | Terminal states. Subset of `states`. At least one required. The journey is complete when it reaches an exit state. |

---

### L4b.5 — Handlers

What happens in each state. Binds states to atoms.

```yaml
handlers:
  <state_name>:
    atom:     <atom_id>
    on_enter: <action_expression | null>
    on_exit:  <action_expression | null>
```

| Field | Description |
|---|---|
| `handlers.<state_name>.atom` | The atom active in this state. For UI surfaces, this should be a COMPONENT atom (the screen). For API/CLI surfaces, this should be a PROCEDURAL atom (the handler). |
| `handlers.<state_name>.on_enter` | Optional. Action executed when entering this state (e.g., "load user data", "start timer"). Set `null` when unused. |
| `handlers.<state_name>.on_exit` | Optional. Action executed when leaving this state (e.g., "save draft", "clear temporary state"). Set `null` when unused. |

---

### L4b.6 — Transitions

Rules for moving between states.

```yaml
transitions:
  - from:   <state_name>
    on:     <event_name | action_name | "auto">
    invoke: <atom_id | flow_id | null>
    with:   <binding_map>
    to:     <state_name>
    on_error:
      <error_code | pattern>: <transition_action>
    guards: [<expression>, ...]
```

| Field | Description |
|---|---|
| `from` | The state the journey is currently in. |
| `on` | What triggers the transition. An event name, a user action name, or `"auto"` (transition immediately on entering `from`). |
| `invoke` | Optional atom or orchestration to execute during the transition. Set `null` for pure state transitions (common with `"auto"`). |
| `with` | Argument bindings for the invocation. May reference journey state or handler output. |
| `to` | The state to transition to on success. Must be in `states`. |
| `on_error` | Map of error codes/patterns to transition actions. Empty map `{}` when `invoke` is null. |
| `guards` | Optional. Pseudo-formal conditions that must all be true for this transition to fire. If guards fail, the transition does not occur and the journey stays in `from`. |

**Transition actions (on_error):**

- `STAY` — remain in current state, show error to user.
- `GOTO state=<state_name>` — transition to a different state than `to`.
- `ABORT` — end the journey abnormally.

**Reference forms inside `with` bindings:**

- `trigger.<field>` — field from the journey's initiating payload (if any).
- `handler.<field>` — field from the current state's handler atom (typically a COMPONENT's `local_state` or input).
- `previous_state.<field>` — field captured from the prior state's handler output.
- `event.<field>` — field from the event that triggered the transition.

---

### L4b.7 — Verification Criteria

```yaml
verification_criteria:
  - scenario: <string>
    path:     [<state_name>, ...]
    asserts:  [<expression>, ...]
```

| Field | Description |
|---|---|
| `scenario` | Human description of the user path being verified. |
| `path` | The sequence of states traversed in this scenario. |
| `asserts` | Rules that must hold after this scenario completes. Typically reference database state, UI state, and emitted events. |

---

### L4b.8 — Changelog

Standard changelog.

---

## Validation Rules

### Orchestration validation

1. `orchestration.id` matches `naming_ledger.flow_id`.
2. `trigger.event` (when present) matches `naming_ledger.event_name`.
3. `trigger.payload_type` (when present) resolves to an existing key in L0.4 `types`.
4. Every `sequence[].invoke` resolves to a real atom or orchestration.
5. Every `sequence[].with` binding references valid fields from `trigger` or prior step outputs.
6. Every error code or pattern in `on_error` references valid codes from L0.3 `errors` or is a valid wildcard pattern.
7. Every `compensation` atom (when non-null) resolves to a real atom.
8. If `transaction_boundary: saga`, every step with side effects has a non-null `compensation`.
9. Every step label is unique within the orchestration.
10. Every event in `state_transitions[].emit` matches `naming_ledger.event_name`.
11. Step invocation I/O types are compatible: the invoked atom's input type is compatible with the `with` bindings.
12. Any `GOTO step=<label>` action targets a step that exists in this orchestration.
13. `trigger.schedule` (when present) is a syntactically valid cron expression.
14. If `transaction_boundary: acid`, every invoked atom belongs to modules that share persistence (either a single module, or modules in the same `shared_with` cluster). Acid across independently-owned module databases is not representable.
15. Changelog has at least one entry.

### Journey validation

1. `journey.id` matches `naming_ledger.journey_id`.
2. `surface` is one of the recognized values.
3. Every state in `states` has an entry in `handlers`.
4. Every `handlers.<state>.atom` resolves to a real atom.
5. For `surface: web_ui` or `surface: mobile_ui`, handler atoms should be COMPONENT. For `surface: api`, `cli`, `conversation`, `email_sequence`, handler atoms should be PROCEDURAL. (Warning, not hard failure — some mixed cases are valid.)
6. Every `transitions[].from` and `transitions[].to` are in `states`.
7. Every `transitions[].invoke` (when non-null) resolves to a real atom or orchestration.
8. Every error code in `transitions[].on_error` resolves in L0.3 `errors` or is a valid wildcard.
9. At least one `exit_state` is reachable from `entry_point.initial_state` via declared transitions.
10. `exit_states` is a subset of `states` and is non-empty.
11. Every event in `transitions[].on` matches `naming_ledger.event_name` or is a recognized action name or `"auto"`.
12. `entry_point.from` is consistent with an L2 interface entry point that invokes this journey.
13. Any `GOTO state=<name>` in `transitions[].on_error` targets a state in `states`.
14. Changelog has at least one entry.
