# Forge V2 Schema

Forge V2 is a schema for translating business intent into working software while preserving runnability throughout the build.

The design goals are:

- software should be working throughout the build
- work should land vertically, not only horizontally
- contracts should be canonical and explicit
- runtime units should be modular and promotable
- the top level should stay conceptually small

## Top-Level Model

The recommended Forge V2 top-level sections are:

```yaml
schema_version:
system:
verticals:
units:
types:
operations:
surfaces:
stores:
flows:
bootstrap:
verification:
build_policy:
```

Each section owns one kind of truth.

- `system`: business identity and global constraints
- `verticals`: business capability slices
- `units`: runnable and promotable runtime modules
- `types`: canonical data and contract shapes
- `operations`: canonical business actions
- `surfaces`: transport bindings that expose operations
- `stores`: persistence backbones by environment
- `flows`: meaningful end-to-end business journeys
- `bootstrap`: the first working vertical slice that must stay working
- `verification`: structured guidance for checking drift and behavior
- `build_policy`: hard rules that constrain how Forge builds

## Core Principles

1. Critical operations are never inferred.
2. Public and cross-unit contracts are always named and canonical.
3. The schema should support vertical delivery, not just horizontal decomposition.
4. Runtime topology and business capability topology are distinct and both matter.
5. The bootstrap slice is a build constraint, not only a documentation note.
6. The schema should stay general enough to describe real systems without overfitting to one implementation style.

## Filesystem Layout

Forge V2 should use a multi-file layout. One file should represent one canonical object wherever possible.

```text
forge/
  system.yaml
  bootstrap.yaml
  build_policy.yaml

  verticals/
    proposals.yaml
    dashboard.yaml

  units/
    app.yaml
    bff.yaml
    worker.notifications.yaml

  types/
    Proposal.yaml
    ProposalStatus.yaml
    ApproveProposalInput.yaml
    ActionRun.yaml
    NotFound.yaml
    ValidationFailed.yaml

  operations/
    approve_proposal.yaml
    load_dashboard.yaml
    get_current_user.yaml

  surfaces/
    approve_proposal_http.yaml
    load_dashboard_http.yaml
    dashboard_route.yaml

  stores/
    main.yaml
    blobs.yaml
    derived.yaml

  flows/
    proposal_approval_flow.yaml
    dashboard_load_flow.yaml

  verification/
    startup/
      bff_health.yaml
    surfaces/
      approve_proposal_surface.yaml
    flows/
      proposal_approval_flow.yaml
    promotion_gates.yaml
```

This layout is preferred because it is:

- merge-friendly
- easy to validate
- easy to graph
- easy to extend vertically
- suitable for agent-driven editing

## Section Schemas

### `schema_version`

Purpose: identify the schema contract being authored.

Recommended root field:

```yaml
schema_version: forge.v2
```

### `system`

Purpose: define business intent and global constraints.

Recommended singleton file: `system.yaml`

```yaml
system:
  id: string
  name: string
  description: string
  purpose: string
  goals:
    - string
  invariants:
    - string
  auth_contexts:
    - id: string
      description: string
  security:
    posture:
      - string
    data_handling:
      - string
  environments:
    - id: string
      description: string
  promotion_stages:
    - dev
    - test
    - prod
```

Notes:

- `id` is the stable machine identifier for the system.
- `invariants` are global truths that no implementation may violate.
- `auth_contexts` are canonical caller-context identifiers referenced by `operations` and `surfaces`.
- `security` holds system-level security posture and data-handling expectations.
- `promotion_stages` define the ordered path from local build to production.

### `verticals`

Purpose: define business capability slices similar to the useful part of V1 modules and domains, but without overloading them with runtime concerns.

Recommended directory: `verticals/`

```yaml
id: string
name: string
description: string
purpose: string
owned_by: string
invariants:
  - string
```

Notes:

- A vertical is not a deployable runtime module.
- A vertical is used for capability grouping, planning, ownership, and graph clustering.
- `operations`, `types`, `surfaces`, and `flows` should reference a `vertical`.

### `units`

Purpose: define independently runnable or promotable parts of the system.

Recommended directory: `units/`

```yaml
id: string
name: string
description: string
kind: ui | service | worker | cli | scheduler | batch
purpose: string
owned_by: string
entrypoint: string
serves_verticals:
  - string
run:
  dev: string
  test: string
  prod: string
env:
  - name: string
    required: true | false
    description: string
    default: string
depends_on:
  units:
    - string
  stores:
    - string
  externals:
    - string
healthcheck:
  kind: http | command | process | none
  target: string
promotion:
  independently_promotable: true | false
  notes: string
```

Notes:

- A unit is a runtime boundary.
- `serves_verticals` allows runtime modules to declare business capability coverage.
- `run.dev` is required if `build_policy.preserve_runnability` is true.
- `kind` should stay explicit because it affects boot expectations, health assumptions, graphing, and scaffolding.

### `types`

Purpose: define canonical data truth, including internal state, payloads, events, projections, and errors.

Recommended directory: `types/`

```yaml
id: string
vertical: string
name: string
description: string

kind: entity | value_object | payload | projection | event | snapshot | artifact | scalar

identity:
  mode: none | single | composite
  fields:
    - string

fields:
  - name: string
    description: string
    spec: string

scalar:
  constraint: string

data_classification: public | internal | sensitive | restricted

lifecycle:
  mutability: mutable | immutable | append_only | replaceable
  rebuildable: true | false
  retention: ephemeral | medium_lived | long_lived
  state_field: string
  states:
    - string
  transitions:
    - from: string
      to: string
      via: string

persistence:
  authority: canonical | derived
  store: string
  metadata_store: string
  payload_store: string
  consistency: strong | eventual
  access_patterns:
    - point_lookup
    - filtered_list
    - transactional_write
    - append
    - upload
    - download
    - full_text_search
    - semantic_search
    - read_optimized

invariants:
  - string
```

Notes:

- `kind` explains its structural class.
- `fields[].spec` should describe the field in natural language, including type, requiredness, nullability, array semantics, defaults, derivation, or conditional rules when those matter.
- The point of `spec` is to keep field contracts readable and auditable without exploding the schema into too many low-level keys.
- Example `spec` strings:
  - `UUID; required; immutable after creation`
  - `String; optional; if present must be 1..120 chars`
  - `Array of DocumentReference; empty when no attachments exist`
  - `Decimal amount; required; must be >= 0`
- Scalar types should use `scalar.constraint` rather than a top-level free string.
- `data_classification` is the minimal canonical hook for privacy and security review.
- `lifecycle.transitions` makes valid state changes explicit rather than leaving them implied by operations or flows.
- Public and cross-unit boundaries should use named payload and error types.

### `operations`

Purpose: define canonical business actions. This is where critical behavior becomes source-of-truth.

Recommended directory: `operations/`

```yaml
id: string
vertical: string
name: string
description: string
purpose: string
unit: string

inputs:
  - string
outputs:
  - string
referenced_types:
  - string
errors:
  - string

reads:
  types:
    - string
  stores:
    - string

writes:
  types:
    - string
  stores:
    - string

emits:
  - string
consumes:
  - string

auth:
  context: string
  required: true | false

behavior:
  idempotent: true | false
  retryable: true | false

invariants:
  - string
```

Notes:

- Operations are canonical and must not be inferred from route handlers, CLI commands, or flow prose.
- Each public or cross-unit operation should declare canonical input, output, and error contracts.
- `inputs` and `outputs` may contain one or many named types. Use YAML lists. Compact inline form like `[TypeA, TypeB]` is preferred. For convenience, tooling may also accept a comma-separated string and normalize it.
- `referenced_types` is for additional named types the operation materially depends on but does not accept or return directly.
- `reads` and `writes` make behavioral impact and persistence coupling explicit.
- Events should be modeled as `types.kind = event`, then referenced from `emits` and `consumes`.

### `surfaces`

Purpose: define how operations become reachable through transport.

Recommended directory: `surfaces/`

```yaml
id: string
vertical: string
name: string
description: string
unit: string
transport: http | cli | queue | cron | internal | ui_route
operation: string

binding:
  http:
    method: string
    path: string
  cli:
    command: string
  queue:
    topic: string
  cron:
    schedule: string
  ui_route:
    route: string
  internal:
    target: string

error_mappings:
  - type: string
    mapping: string

auth:
  context: string
  required: true | false

behavior:
  idempotent: true | false
  retryable: true | false
```

Notes:

- A surface exposes exactly one canonical operation.
- A surface should not redefine input or output contracts independently if they already belong to the operation.
- `binding` should be transport-discriminated rather than a bag of unrelated optional fields.

### `stores`

Purpose: define persistence backbones and their environment-specific mappings.

Recommended directory: `stores/`

```yaml
id: string
name: string
description: string
class: transactional | artifact | derived | append_only | retrieval
dev: string
test: string
prod: string
guarantees:
  durability: durable | ephemeral
  consistency: strong | eventual
notes: string
```

Notes:

- Types declare persistence needs.
- Stores declare infrastructure choices and guarantees.
- Multiple types may share one store.

### `flows`

Purpose: define meaningful business journeys that cross operations, surfaces, units, and stores.

Recommended directory: `flows/`

```yaml
id: string
vertical: string
name: string
description: string
purpose: string
trigger: string
path:
  - kind: surface | operation | unit
    ref: string
side_effects:
  - string
failure_modes:
  - string
```

Notes:

- A flow is a business journey, not a transport binding.
- `path` should use typed references rather than plain strings to improve graphing and validation.
- `failure_modes` can stay general. They may reference canonical error IDs, or they may remain natural-language descriptions when the failure is broader than one declared error contract.

### `bootstrap`

Purpose: define the first working vertical slice and require that it stays working.

Recommended singleton file: `bootstrap.yaml`

```yaml
bootstrap:
  description: string
  required_units:
    - string
  required_stores:
    - string
  required_surfaces:
    - string
  path:
    - string
  success_criteria:
    - string
  preserve: true | false
```

Notes:

- V2 should keep exactly one formal bootstrap definition.
- Later working slices can be represented as flows, not as extra bootstrap objects.

### `verification`

Purpose: define structured agent guidance for proving the implementation still matches the schema.

Recommended directory: `verification/`

Startup checks:

```yaml
id: string
unit: string
intent: string
check: string
```

Surface checks:

```yaml
id: string
surface: string
intent: string
request: string
expect:
  - string
```

Flow checks:

```yaml
id: string
flow: string
intent: string
expect:
  - string
```

Promotion gates:

```yaml
dev:
  - string
test:
  - string
prod:
  - string
```

Notes:

- Verification in V2 is structured agent guidance, not an executable test DSL.
- The schema should keep verification readable while still making references explicit.

### `build_policy`

Purpose: define framework execution rules that constrain how Forge builds.

Recommended singleton file: `build_policy.yaml`

```yaml
build_policy:
  strategy: vertical_first
  preserve_runnability: true | false
  completion_states:
    - specified
    - scaffolded
    - implemented
    - composed
    - reachable
    - verified
  rules:
    - string
```

Notes:

- `strategy` should default to `vertical_first`.
- `preserve_runnability` should usually be `true`.
- `rules` should contain hard constraints, not aspirational prose.

## Reference Rules

Forge V2 should use strict `id` references across the schema.

Required reference discipline:

- each `vertical` reference must point to a file in `verticals/`
- each `unit` reference must point to a file in `units/`
- each `type` reference must point to a file in `types/`
- each `operation` reference must point to a file in `operations/`
- each `surface` reference must point to a file in `surfaces/`
- each `store` reference must point to a file in `stores/`
- each `flow` reference must point to a file in `flows/`
- each `auth.context` reference must point to an entry in `system.auth_contexts`

Reference rules:

1. IDs are canonical.
2. Human-readable names are descriptive only and must not be used as references.
3. No critical operation may be inferred from a surface or a flow.
4. No public or cross-unit contract may be anonymous.

## Contract Guarantees

Forge V2 guarantees contracts only if the builder and validator enforce canonical ownership rules.

The contract ownership model should be:

- `types` define contract shapes
- `operations` define canonical business contracts
- `surfaces` bind operations to transport
- `flows` compose operations into journeys

### Hard Contract Rules

1. Every public or cross-unit operation must declare:
   - `inputs`
   - `outputs`
   - `errors`
2. Every surface must reference exactly one canonical operation.
3. A surface must not invent an independent public contract if an operation already defines it.
4. All public and cross-unit payloads must use named canonical types.
5. All public and cross-unit error responses must use named canonical error types.
6. Writable canonical types must declare persistence semantics.
7. An operation may write only to stores compatible with the persistence semantics of the types it writes.
8. Contract changes must surface impact on all dependent operations and surfaces.
9. Events that cross unit boundaries must use named canonical event types.

### What This Guarantees

If the rules above are enforced, Forge V2 can guarantee:

- no critical operation exists only as route prose or handler code
- no public surface exists without a canonical operation behind it
- no boundary payload drifts into anonymous ad hoc structures
- store usage remains traceable to type semantics
- graphing can expose contract edges clearly

What it does not guarantee by itself:

- runtime correctness
- performance characteristics
- implementation quality beyond what the builder, reviewer, and verifier enforce

## Validation Rules

Recommended static validation rules:

1. Every referenced object must exist.
2. Every operation must reference an existing unit.
3. Every surface must reference an existing unit and operation.
4. Every operation input, output, and referenced type must exist.
5. Every operation error type must exist.
6. Every type store reference must exist.
7. Every operation write store must exist.
8. Every flow path reference must exist and match the declared `kind`.
9. Every bootstrap unit, store, and surface reference must exist.
10. Every unit must have a `run.dev` command when runnability preservation is enabled.
11. Every `auth.context` reference must resolve to `system.auth_contexts`.

Recommended contract-specific validation rules:

1. If `types.kind = scalar`, `scalar.constraint` should be populated.
2. If `types.lifecycle.states` is populated, `lifecycle.state_field` should also be populated.
3. If `types.lifecycle.transitions` is populated, each `via` reference should point to an existing operation.
4. If an operation is public or cross-unit, `inputs`, `outputs`, and `errors` are required.
5. If a surface is transport `http`, `binding.http.method` and `binding.http.path` are required.
6. If a type has `persistence.authority = canonical`, `persistence.store` should be declared unless the type is intentionally non-persistent.

## Graph Model

Forge V2 should preserve and improve the graph view.

Recommended graph nodes:

- system
- vertical
- unit
- type
- operation
- surface
- store
- flow
- bootstrap
- verification check

Recommended graph edges:

- `vertical -> operation`
- `vertical -> type`
- `vertical -> surface`
- `vertical -> flow`
- `unit -> surface`
- `unit -> operation`
- `surface -> operation`
- `operation -> input type`
- `operation -> output type`
- `operation -> referenced type`
- `operation -> error type`
- `operation -> read store`
- `operation -> write store`
- `type -> store`
- `flow -> surface`
- `flow -> operation`
- `bootstrap -> unit`
- `bootstrap -> store`
- `bootstrap -> surface`
- `verification -> unit`
- `verification -> surface`
- `verification -> flow`

Recommended graph projections:

1. System graph
   Shows all nodes and edges.
2. Vertical graph
   Filters to one business capability slice.
3. Runtime graph
   Focuses on units, surfaces, stores, and runtime dependencies.
4. Contract graph
   Focuses on surfaces, operations, types, and store semantics.
5. Bootstrap graph
   Focuses on the minimum working slice and its preservation.

## Recommended Defaults

These defaults fit the V2 thesis best:

- `schema_version = forge.v2`
- `build_policy.strategy = vertical_first`
- `build_policy.preserve_runnability = true`
- one formal `bootstrap`
- multi-file authoring
- strict `id` references
- explicit `operations`
- explicit `verticals`
- structured-but-human verification guidance

## Example Skeleton

```yaml
schema_version: forge.v2

system:
  id: hestia
  name: Hestia
  description: Home operations and intelligence platform
  purpose: Provide a single source of truth for home ownership and assistant-guided actions
  goals:
    - unify home information
    - support approval-gated actions
    - remain runnable throughout build
  invariants:
    - no agentic write without explicit approval
    - every canonical record is scoped to one home
    - bootstrap path must remain working
  auth_contexts:
    - id: anonymous
      description: unauthenticated caller
    - id: session_user
      description: authenticated end user with session
  security:
    posture:
      - all public writes require authenticated approval context
      - secrets must not be stored in canonical operational records
    data_handling:
      - pii must be explicitly marked on canonical types
      - derived stores must not become source of truth
  environments:
    - id: dev
      description: local development
    - id: prod
      description: production deployment
  promotion_stages:
    - dev
    - prod
```

## Final Principle

Forge V2 works when each layer stays narrow and explicit:

- `system` says what the business needs
- `verticals` say which capability slices matter
- `units` say what can run and be promoted
- `types` say what is canonically true
- `operations` say what critical actions exist
- `surfaces` say how operations become reachable
- `stores` say how truth survives across environments
- `flows` say what journeys matter
- `bootstrap` says what must work first and keep working
- `verification` says how humans and agents check for drift
- `build_policy` says how Forge itself must behave

That is the recommended V2 schema model for building working software throughout the process without collapsing back into implicit behavior or late integration.
