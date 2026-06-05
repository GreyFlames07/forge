---
name: forge-schema
description: >-
  Enterprise system design and Forge V4 central schema authoring. Use when
  translating system intent into Forge V4 C1/C2 architecture, refining
  forge/system.yaml, forge/containers.yaml, forge/entities.yaml, reasoning from
  business actions into cross-container runtime flows, choosing runtime
  containers, identifying business entities, and preserving a clean boundary
  between central C1/C2 schema and code-owned C3 annotations. Use after business
  direction is clear, and before implementation, security review, or build work.
---

# forge-schema

Read before starting:

- `../../FRAMEWORK_V4.md`
- `../../SCHEMA_REFERENCE_V4.md`

Prefer when available:

- `forge init`
- `forge crawl`
- `forge context`
- `forge audit`

## Purpose

Turn clear product or business direction into enterprise-grade Forge V4 system
architecture.

This skill owns C1/C2 system design and central Forge schema authoring. It does
not validate the business idea; that belongs to `forge-business`.

Core rule:

```text
System intent first.
Business actions inform runtime speculation.
Runtime speculation informs containers.
C1/C2 stay central.
C3 lives beside code.
```

## V4 Boundary

Central Forge V4 files own durable C1/C2 truth:

```text
forge/system.yaml
forge/containers.yaml
forge/entities.yaml
forge/decisions.yaml
forge/crawler.yaml
```

Code-owned C3 annotations own implementation architecture:

```text
@forge:component
@forge:type
@forge:persistence
@forge:operation
```

Do not model internal container/component flows centrally. A central runtime flow
may show control moving between runtime containers. Detailed flow inside a
container is C3 and should be expressed later through code annotations.

## Decision Log

Maintain `forge/decisions.yaml` for non-trivial schema and system design
decisions. Use the `forge.decisions` schema from `SCHEMA_REFERENCE_V4.md`.

Record decisions when choosing or rejecting:

- system boundary or ownership
- actors or external dependencies
- runtime containers or source roots
- cross-container flow shape
- entity ownership, lifecycle, persistence, or canonical type direction
- security, privacy, compliance, availability, or operational trade-offs

Keep each decision small and crawlable. Reference Forge ids in `refs` wherever
possible. Do not use the decision log for scratch notes.

## Working Style

Use a consultative system design workshop style.

1. Read existing artifacts before asking questions.
2. Infer what is supported by the current repo and schema.
3. Ask only questions that unblock system architecture.
4. Draft first when architecture is easier to critique than invent.
5. Explain trade-offs plainly.
6. Push back on unnecessary services, queues, databases, and abstractions.
7. Prefer the simplest architecture that satisfies the system drivers.
8. Keep schema tied to real runtime, ownership, security, or operational needs.

## Description-First Drafting

When the operator asks to evaluate ideas before schema authoring, draft
schema-conformant descriptions first.

Use this mode to refine:

- system purpose and boundary
- actor and external dependency descriptions
- business actions and outcomes
- speculative runtime flow descriptions
- container responsibilities
- entity descriptions, ownership, lifecycle, and security notes

Keep prose close enough to the V4 schema that it can be converted directly into
YAML. Do not introduce concepts that the schema cannot represent unless they are
clearly labeled as assumptions, risks, or open questions.

After operator approval, convert the refined descriptions into the central Forge
files with minimal transformation.

## Enterprise Design Lens

Evaluate the system through these lenses as relevant:

- System boundary and ownership
- Actors and external systems
- Business actions and outcomes
- Cross-container runtime behavior
- Runtime responsibility boundaries
- Data ownership and lifecycle
- Integration style and coupling
- Consistency, latency, availability, and scale
- Security, privacy, and compliance obligations
- Observability and supportability
- Deployment and operational complexity
- Team ownership and future change pressure

Use these lenses to improve judgment. Do not force every insight into YAML.

## Workflow

### Phase 1: Situation Scan

If Forge files exist, inspect them:

```bash
ls -la forge 2>/dev/null
forge crawl --format json
```

If Forge files do not exist, determine whether the user wants a new V4
workspace:

```bash
forge init
```

Do not initialize or edit files unless asked.

### Phase 2: System Intent

Clarify the system-level architectural intent.

Ask only what is missing:

- What system are we designing?
- What is inside the system boundary?
- What is explicitly outside the boundary?
- Who or what interacts with the system?
- Which external systems matter?
- What non-negotiable security, scale, reliability, or compliance constraints
  exist?

Author or refine:

```text
forge/system.yaml
```

Capture:

- system purpose
- description
- boundary
- actors
- external dependencies
- global security posture
- business actions and expected outcomes

Business actions should express intent and outcomes, not runtime mechanics.

### Phase 3: Runtime Flow Speculation

Use the business actions to speculate on cross-container runtime flows before
settling containers.

For each important business action, ask:

- What starts this action?
- What system boundary does it enter through?
- What durable state may be read or changed?
- What external systems may be called?
- What needs to happen synchronously?
- What can happen asynchronously?
- Where are the major control handoffs?
- Where do branches or failures materially change the architecture?

Draft possible runtime flow shapes in prose first. Do not overfit containers too
early.

Good runtime speculation names control movement:

```text
user submits checkout
-> web app sends request to backend
-> backend validates cart and reserves inventory
-> backend asks payment provider to authorize payment
-> backend persists order
-> backend returns confirmation
```

Avoid C3 detail:

```text
checkout_router calls validate_cart_service then payment_adapter then
order_repository
```

That belongs to code annotations.

### Phase 4: Container Model

Settle runtime containers after runtime flow speculation.

Author or refine:

```text
forge/containers.yaml
```

Capture:

- real runtime containers
- source roots when known
- responsibilities
- security responsibilities
- deployment entries when known
- cross-container runtime flows

Rules:

- Containers are runtime/deployment units, not arbitrary folders.
- Split containers only when runtime responsibility, deployment, scaling,
  security, or ownership boundaries justify it.
- Do not create microservices from domain nouns alone.
- Do not model internal operations or local component sequencing centrally.
- Cross-container flow steps describe runtime control movement.
- Inside-container logic should stay summarized until C3 annotations exist.

### Phase 5: Entity Model

Author or refine:

```text
forge/entities.yaml
```

Capture:

- business-significant entities, records, and lifecycle objects
- logical ownership
- canonical type references
- persistence location when known
- lifecycle states and transitions where useful
- entity-level security notes

Rules:

- Entity is not data shape.
- Logical owner is not always physical persistence.
- `canonical_type` should point to an existing or planned `@forge:type`.
- `persisted_in` should point to durable storage ownership.
- Do not create entities for incidental DTOs.

### Phase 6: C3 Responsibility Plan

For the first build slice, identify what implementation should later annotate:

- components
- operations
- data shapes
- persistence points
- internal container/component flows

Do not author detailed C3 centrally. Produce an annotation responsibility plan:

```text
When building this slice:
- account_router should become @forge:component role: interface
- create_account should become @forge:operation
- AccountPayload should become @forge:type
- account_store should become @forge:persistence
```

### Phase 7: Validation

After schema edits, run where available:

```bash
forge crawl --format json
forge context --system --format md
forge audit
```

Use results to fix:

- malformed schema
- broken references
- unclear cross-container runtime flows
- duplicate or missing model elements
- audit views that are valid but hard to understand

## Pattern Guidance

Choose architecture patterns only when requirements justify them.

Default bias:

- early product: monolith or modular monolith
- clear boundaries but simple operations: modular monolith
- independent deployment or scaling needs: microservices
- async reactions and loose coupling: event-driven architecture
- very different read/write models: CQRS
- audit-first state history: event sourcing
- strong domain boundary needs: hexagonal or clean architecture
- multiple clients or backend services: API gateway only when it simplifies real
  complexity

Do not choose distributed patterns to sound enterprise-grade.

## Technology Guidance

Make technology choices from constraints, not fashion.

When relevant, compare options using:

- data shape and relationship complexity
- transaction and consistency needs
- query patterns
- throughput and latency
- operational burden
- team familiarity
- deployment environment
- cost and vendor lock-in
- security and compliance obligations

Prefer boring, well-understood technology unless a requirement clearly demands
otherwise.

## Review Gates

Before calling schema work complete, check:

1. Is business validation already clear enough to design from?
2. Does `system.yaml` describe system intent, not implementation?
3. Are business actions expressed as intent and outcomes?
4. Were runtime flows speculated before containers were finalized?
5. Are containers real runtime units?
6. Are container responsibilities distinct?
7. Are central flows cross-container/runtime-level, not C3 internals?
8. Are entities business-significant?
9. Are ownership, persistence, and lifecycle separated?
10. Is C3 intentionally left to annotations?
11. Is the first build slice thin and buildable?
12. Would `forge-review` have enough context to evaluate the model?

## Output

When making changes, summarize:

- files changed
- system design decisions made
- runtime flow assumptions
- container boundaries chosen
- entities identified
- C3 responsibilities deferred to annotations
- validation run and results

When not making changes, produce a design brief with:

- recommended system intent
- inferred business-action/runtime-flow mapping
- recommended container model
- recommended entity model
- key trade-offs
- next schema steps

## Guardrails

- Do not validate the business idea; route that to `forge-business`.
- Do not start with containers before understanding runtime behavior.
- Do not model inside-container flows centrally.
- Do not over-model.
- Do not add distributed-system complexity without a concrete driver.
- Do not hide uncertainty inside confident YAML.
- Do not use technology names as architecture justification.
- Do not proceed to build before schema, security, and review concerns are clear.
