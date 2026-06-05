# Forge Framework

Forge is a slice-first architecture and delivery framework. It keeps C4 as
the structural backbone, keeps C1/C2 architecture central, and keeps C3 schema
beside the implementation that owns it.

Core rule:

```text
C1 and C2 are authored centrally.
C3 is authored in code.
Forge extracts, validates, and renders the merged model.
```

## Process

### 1. Define System Intent

Author: `forge/system.yaml`

Elicit:

- system purpose
- boundary
- actors
- external dependencies
- global security posture
- business actions and outcomes

Do not define runtime flows here. Business actions describe intent; container
flows describe execution.

### 2. Define Runtime Containers

Author: `forge/containers.yaml`

Elicit:

- real runtime containers
- source roots for code-owned annotations
- environment deployment entries
- container-level flows as ordered runtime steps

Container relationships are not authored separately. They are derived from
control moving between steps that run in different containers.

### 3. Define Business State

Author: `forge/entities.yaml`

Elicit:

- important entities, records, and lifecycle objects
- canonical data shape references
- logical ownership
- persisted location
- lifecycle states and transitions where needed
- entity-level security notes

Keep these separate:

```text
entity != data shape != logical owner != physical store
```

### 4. Record Non-Trivial Decisions

Author: `forge/decisions.yaml`

Record decisions when architecture, security posture, source-root layout,
operation contracts, implementation direction, test strategy, or accepted risk
would otherwise be hidden in chat.

Keep records small, structured, and crawlable. A decision should explain what
was chosen, why, which Forge ids it affects, what alternatives were considered,
and what consequences follow.

Do not use the decision log as a scratchpad. Record decisions that future
builders or reviewers need in order to avoid rediscovering the same trade-off.

### 5. Build One Slice

Pick one thin end-to-end slice. Implement it while writing the C3 annotations in
the same code changes.

Author in code:

- `@forge:component`
- `@forge:type`
- `@forge:persistence`
- `@forge:operation`

Embedded C3 is not an after-the-fact documentation pass. If architecture-
significant code is introduced without its relevant annotation, the build slice
is incomplete unless that code is intentionally outside the Forge model.

### 6. Extract, Validate, Render

Forge extracts C3 annotations, validates the merged model, and renders context
and audit views. Fix broken references, unreadable flows, and implementation
drift before calling the build slice complete.

## CLI Use

### `forge list`

Use `forge list` to discover the model:

- systems
- containers
- business actions
- container flows
- entities
- extracted components
- extracted data shapes
- extracted operations

`list` should answer "what exists?" without dumping full context.

### `forge context`

Use `forge context` to fetch the narrow context needed for the active task.

Typical scopes:

```text
forge context --system
forge context --container <container_id>
forge context --flow <container_flow_id>
forge context --entity <entity_id>
forge context --component <component_id>
```

`context` should answer "what does this task need?" It should prefer scoped
output over broad dumps.

### `forge audit`

Use `forge audit` when a human needs to inspect the architecture.

The audit should render:

- C1 system overview
- C2 container diagram
- deployment views by environment
- runtime-container diagrams for each flow
- entity and persistence view
- extracted C3 component views
- validation findings

Diagram rule:

```text
Use runtime containers as diagram nodes.
Use arrows to show control moving between containers.
Render payloads, branches, and logic in tables outside the diagram.
Treat branches as control-flow choices between runtime steps, not as local
operation steps.
```

## Flow Rules

Forge has two flow layers:

- container flows in `forge/containers.yaml`
- component flows extracted from `@forge:operation`

Step rules:

- a container-flow step belongs to exactly one runtime container
- multiple container-flow steps may share the same `id`; same-id steps are
  concurrent runtime-component work in the same control-flow phase
- a linear step has `next`
- a branching step has `branches`
- a terminal step has neither
- a step must not have both `next` and `branches`
- next and branch targets may point forward, backward, or to the same step
- loops are represented by condition plus target; no loop field is required
- branches describe alternative control-flow targets from the current runtime
  step; they do not imply concurrency or hidden component operations
- inter-container calls are inferred when control moves between steps with
  different `container` values; they are not modeled as `from`/`to` on a step
- adjacent runtime steps with the same `container` should be merged into one
  step; use that step's logic, branches, and component operations to describe
  what happens inside the container
- concurrent component operation work is represented by multiple operations
  sharing the same `local_flow:local_step` suffix inside the same runtime step

For `@forge:operation`, `input`, `returns`, and `logic` describe the operation's
code contract. `participates_in` describes where the operation appears in one or
more container flow/component operation sequences. In those entries, `container_flow` uses
`flow_id:step_number` so the runtime step is part of the flow reference itself.
`local_flow` uses `local_flow_id:step_number` so the component operation step is
explicit as well. A component operation sequence is rendered inside the runtime
step it belongs to; it is the ordered set of operations performed by one
component while handling that control step. `passes` is the conceptual handoff
to the next component operation step. `flow_logic` may add per-flow context, but must not change the
operation's input, return type, or core logic.

## Interfaces

Interfaces are modeled as components with `role: interface`.

Use interface components for:

- screens
- routers
- workers
- schedulers
- event boundaries
- CLIs
- file boundaries
- meaningful nested surfaces

An interface is not an operation:

```text
screen/router/worker = interface component
submit/click/handle/process = operation
```

Nested interface components, such as cards or panels, should use
`parent_component`. Only model a nested surface when it owns meaningful state,
input, branching, data shaping, or component operation behavior.

## LLM Authoring And Implementation Conventions

These conventions reduce common LLM coding and schema-authoring mistakes. They
bias toward caution over speed; use judgment for trivial tasks.

### Think Before Coding

- State assumptions explicitly.
- If multiple interpretations exist, present them instead of choosing silently.
- If a simpler approach exists, say so.
- Push back when a requested shape adds avoidable complexity.
- If something is unclear, stop, name the ambiguity, and ask.

### Simplicity First

- Add no features beyond what was asked.
- Add no abstractions for single-use code.
- Add no flexibility that was not requested.
- Keep schema and code as small as the task allows.
- If a solution is much longer than it needs to be, rewrite it smaller.

### Surgical Changes

- Touch only what the task requires.
- Do not refactor unrelated code or schema.
- Match existing style.
- Remove only orphans introduced by the current change.
- Mention unrelated dead code or stale schema; do not delete it unless asked.

The test: every changed line should trace to the request, a schema rule, or a
validation finding.

### Goal-Driven Execution

Turn work into verifiable goals:

- "Add validation" means add checks or tests for invalid inputs.
- "Fix the bug" means reproduce it, then make the reproduction pass.
- "Refactor X" means preserve behavior and prove relevant checks still pass.

For multi-step work, state:

```text
1. [Step] -> verify: [check]
2. [Step] -> verify: [check]
3. [Step] -> verify: [check]
```

## Completion Criteria

A Forge build slice is healthy when:

- system intent and runtime boundaries are clear
- container flows have inputs, outputs, and dotted-list logic
- referenced data shapes exist
- entity ownership and persistence are explicit
- C3 annotations were written with the implementation
- component flows can be extracted
- diagrams are readable
- validation has no broken references
- tests prove the slice end to end
