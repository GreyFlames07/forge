# Forge Framework

Forge is a vertical-first architecture and delivery framework. It is designed to
help a team describe a system clearly, split it into buildable verticals, and
then implement one thin, testable slice at a time without losing architectural
coherence.

The framework is **skills-first**: use the Forge skills to drive the process,
and use the CLI only to fetch the narrow context or artifact those skills need.

## Core Principle

The framework should move from broad truth to narrow implementation:

1. define the system
2. define what the system does
3. define the important business things
4. define what actually runs
5. split the work into development verticals
6. deepen one vertical at a time
7. review and secure that vertical before implementation starts
8. build and validate that vertical end to end

## Recommended Authoring Order

### 1. System
Purpose:
- define the system purpose, description, boundary, actors, external
  dependencies, and global security posture

Outputs:
- system context
- C4 level 1 view
- global security rules

### 2. High-Level Flows
Purpose:
- define the business and system flows without runtime or implementation detail

Outputs:
- business flows
- major steps
- decision points
- outcomes

### 3. Early State
Purpose:
- identify the important entities, records, and lifecycle objects before exact
  typing begins

Outputs:
- key business objects
- why each object matters
- lightweight lifecycle understanding

### 4. Runtime
Purpose:
- define the containers, persistence boundaries, and real runtime
  responsibilities

Outputs:
- container topology
- ownership boundaries
- C4 level 2 view

### 5. Verticals
Purpose:
- break the system into thin development slices that can be planned, built,
  tested, and reviewed independently

Outputs:
- vertical inventory
- user value per vertical
- flow-to-vertical mapping
- deployment and build notes relevant to each slice

### 6. Runtime Flows
Purpose:
- define how one vertical is realized across containers and external boundaries

Outputs:
- runtime-aware flow steps
- contracts implied by those steps
- persistence and external call boundaries

### 7. Data Shapes
Purpose:
- define the exact payload and state shapes required by runtime flows

Outputs:
- reusable contract shapes
- explicit field definitions
- promoted business payloads and records

### 8. Persistent Shapes
Purpose:
- define the persisted subset of state, ownership, storage model, and lifecycle

Outputs:
- storage-owned shapes
- persistence behavior
- lifecycle notes
- state machines where needed

### 9. Containers
Purpose:
- define internal component structure only for containers that need explicit
  internal modeling

Outputs:
- component inventory
- internal handoff flows
- C4 level 3 view where justified

### 10. Deployment
Purpose:
- define where the runtime model runs in real environments and how trust
  boundaries are crossed

Outputs:
- environment topology
- node placement
- trust boundaries
- deployment diagrams

## How to Get the Most Out of Forge

- Stay broad until the previous layer is clear. Do not jump into components
  before runtime and vertical boundaries are stable.
- Keep verticals genuinely thin. A vertical is a development slice, not a loose
  business domain bucket.
- Promote only meaningful shapes. One-off payloads should stay inline until
  reuse, persistence, or system significance justifies naming them.
- Model container internals only where they improve delivery clarity.
- Use review and security continuously, not only at the end.
- Build each vertical with real tests across unit, integration, and full-system
  behavior in the target environment.
- Choose the skill first, then request context. Do not lead with broad CLI
  dumps.

## Skill Roles

- `forge-schema`: author or refine the architectural truth
- `forge-review`: detect drift, bloat, broken references, and schema mismatch
- `forge-security`: validate security posture across system, runtime,
  persistence, and deployment
- `forge-build`: plan or implement one vertical with TDD and full-system
  validation

## Minimal Healthy Loop

For a new repository:

1. write `system.yaml`
2. add the most important `high_level_flows`
3. define `early_state.yaml`
4. define `runtime.yaml`
5. derive `verticals`
6. choose one vertical
7. deepen it through `runtime_flows`, `data_shapes`, `persistent_shapes`,
   `containers`, and `deployment`
8. run `forge-review`
9. run `forge-security`
10. run `forge-build`
11. capture material tradeoffs in `decision_notes.md`

## Recommended Operating Mode

1. start with `forge-schema`
2. keep the current layer minimal and truthful
3. fetch scoped context only when the active skill asks for it
4. use `forge audit` whenever a human needs to inspect the whole picture
5. treat the compact ordering example as the canonical baseline and the richer
   fulfillment example as the stress case

## Anti-Bloat Rules

- Do not invent containers that do not correspond to real runtime boundaries.
- Do not create internal component models unless the container genuinely needs
  them.
- Do not create separate shapes for data that is neither reused nor persisted.
- Do not treat deployment as an infrastructure dump; keep it at the level needed
  for system understanding and delivery planning.
- Do not widen the current vertical just because adjacent behavior exists.
