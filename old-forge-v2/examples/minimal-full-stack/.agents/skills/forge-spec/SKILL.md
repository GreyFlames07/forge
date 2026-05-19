---
name: forge-spec
description: >
  Forge V2 specification skill. Use when discovery is complete and the user wants to define the
  canonical operations, contracts, stores, flows, and verification needed to make the next runnable
  slices buildable without drift. Drives a targeted interview, gathers enough detail before writing,
  then drafts V2 schema files in one pass per scope.
---

# forge-spec

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/spec/FRAMEWORK.md`
- `forge/workbench/discovery.md`
- relevant files under `forge/system.yaml`, `forge/verticals/`, `forge/units/`, and `forge/bootstrap.yaml`

## Purpose

Fully elicit canonical system truth for a defined scope before implementation begins.

This stage owns:

- `types`
- `operations`
- `surfaces`
- `stores`
- `flows`
- `verification`

The unit of work is usually one vertical at a time, with bootstrap-relevant operations first.

## Output Artifacts

| File | Contents |
|------|----------|
| `forge/types/*.yaml` | Canonical data, payload, event, projection, artifact, and scalar types |
| `forge/operations/*.yaml` | Canonical business actions |
| `forge/surfaces/*.yaml` | Reachability bindings for operations |
| `forge/stores/*.yaml` | Persistence backbones and environment mappings |
| `forge/flows/*.yaml` | End-to-end business journeys |
| `forge/verification/startup/*.yaml` | Startup checks |
| `forge/verification/surfaces/*.yaml` | Surface checks |
| `forge/verification/flows/*.yaml` | Flow checks |
| `forge/verification/promotion_gates.yaml` | Promotion requirements |

## Elicitation Standard

### Non-negotiables

1. Ask enough questions to understand the scope before writing files.
2. Ask bootstrap-relevant questions first.
3. Ask only what cannot be safely inferred from discovery notes and existing schema.
4. Critical operations are always explicit. Never infer them from surfaces or flows.
5. Public and cross-unit contracts must use named canonical types.
6. Keep field contracts readable using `fields[].spec`, not bloated structural subkeys.

## Scope Selection

Before interviewing:

1. Identify the target vertical or bootstrap scope.
2. Read the relevant `vertical` file.
3. Read the related `unit` files.
4. Read `forge/bootstrap.yaml`.

Announce the scope in one line before asking questions.

## Interview Phases

### Phase 1 — Operation Map

Ask all questions in this phase before writing.

Establish:

- the operations that make bootstrap work
- the next operations that expand value
- which unit owns each operation
- which operations are public, cross-unit, or internal

Questions:

- What are the concrete actions the system must support in this scope?
- Which of these actions are part of the bootstrap path?
- Which unit owns each action?
- What inputs go in, what outputs come out, and what can fail?
- Which operations emit or consume events?
- Which additional canonical types does each operation materially reference without directly accepting or returning them?

Every meaningful action should become an `operations/*.yaml` file.

### Phase 2 — Contracts and Canonical Data

Establish:

- the types operations rely on
- lifecycle semantics
- state transitions
- error contracts
- data classification

Questions:

- What canonical records or payloads do these operations touch?
- For each type: what fields matter, and how would you describe each field contract in plain language?
- Which types have lifecycle states? What transitions are valid, and which operation causes each transition?
- Which errors are business-significant enough to name explicitly?
- Which data is sensitive or restricted?

### Phase 3 — Reachability

Establish:

- how operations are exposed
- transport bindings
- auth requirements
- delivery semantics

Questions:

- How does each operation become reachable? HTTP, CLI, queue, cron, internal call, or UI route?
- Which unit exposes it?
- What auth context is required?
- Which behaviors matter for delivery: idempotency, retries, scheduling, event topics?

Each public or cross-unit operation should have a corresponding surface unless it is purely internal.

### Phase 4 — Persistence

Establish:

- what stores exist
- what each type needs from storage
- environment-specific mappings

Questions:

- Which types are canonical versus derived?
- Where do they persist?
- Do any types split metadata and payload storage?
- What read/write patterns matter?
- What dev/test/prod backing is expected for each store?

### Phase 5 — Flows and Verification

Establish:

- the first meaningful end-to-end flows
- startup checks
- bootstrap checks
- operator checks when automation is weak

Questions:

- What business journey does the bootstrap slice actually perform end to end?
- What adjacent flows matter next?
- What checks prove startup works?
- What checks prove bootstrap still works?
- What requires an operator to confirm instead of a machine?

## Assembly Rules

### Draft in one pass per scope

Once the scope is understood:

1. Draft operations first.
2. Draft types those operations require.
3. Draft surfaces and stores.
4. Draft flows from the operations and surfaces.
5. Draft verification items tied to bootstrap and declared flows.

### Type authoring rules

- `kind` stays explicit.
- Use `fields[].spec` for readable field contracts.
- Use `scalar.constraint` for scalar-only constraints.
- Use `lifecycle.transitions` whenever states matter.
- Use named event types for cross-unit events.

### Operation authoring rules

- each operation has one owner unit
- each public or cross-unit operation has named input, output, and error contracts, and may declare additional `referenced_types`
- when an operation accepts or returns multiple canonical types, declare them explicitly as multiple `inputs` or `outputs` rather than collapsing them into one vague payload
- reads and writes must be explicit
- use `emits` and `consumes` for event behavior

### Flow authoring rules

- flows are composed from existing surfaces, operations, and units
- `path` entries use typed refs
- failure modes may be canonical error IDs, natural-language failures, or both

### Verification rules

- bootstrap always gets explicit checks
- operator checks are first-class verification items
- verification should be structured agent guidance, not a heavy DSL

## Completion

When files are written:

1. Use `forge list` and `forge context` to cross-check IDs and dependencies as needed.
2. Surface any structural gaps immediately.
3. Summarize what was added in this scope.
4. Ask whether to continue with the next vertical or move to planning/build.

## Failure Routing

- If discovery artifacts do not clearly define the target scope or bootstrap, route back to `forge-discover`.
- If a critical operation, surface, or type cannot be named explicitly, stop and resolve that ambiguity before drafting schema files.
- If the human asks for implementation before canonical contracts are stable enough, finish `forge-spec` first and only then move to `forge-plan` or `forge-build`.
- If flows reveal missing units or invalid capability boundaries, stop and send the issue back to `forge-discover` instead of patching around it locally.

## Key Constraints

- Never write before the scope is understood.
- Never invent operations the user has not actually described.
- Never duplicate contract truth across operations and surfaces unnecessarily.
- `forge/workbench/` is read for context but not updated by this stage.
