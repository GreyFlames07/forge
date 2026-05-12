# Forge V2 Architecture

Forge V2 should be built as four coordinated layers:

1. schema
2. workbench
3. CLI
4. skills and stage frameworks

The core philosophy is:

- the schema is the source of truth
- work should land vertically
- the system should become runnable as early as possible
- bootstrap should be preserved throughout build
- frameworks and skills should consume schema truth rather than invent parallel structure

## 1. Architecture Overview

### Schema

The schema defines intended system truth.

It owns:

- business intent
- capability slices
- runtime units
- canonical data and contracts
- canonical operations
- surfaces
- stores
- flows
- bootstrap
- verification targets
- build rules

The schema must not store implementation progress or delivery state.

### Workbench

The workbench stores delivery-state artifacts derived from the schema.

It owns:

- build plans
- slice status
- review artifacts
- validation artifacts

The workbench is not source-of-truth for the system design. It is source-of-truth for the current execution state of the build process.
It is primarily consumed by stage skills and frameworks, not exposed as a broad public CLI surface.

### CLI

The CLI is the schema runtime.

It loads schema files, validates references, builds the internal graph, produces context bundles, derives plans, and reports status.

The CLI should be schema-aware first and skill-aware second.

### Skills and Stage Frameworks

Skills are thin orchestration layers that use the CLI and schema.

Stage frameworks define how each stage should interpret the same schema from a different angle. They should not redefine schema concepts.

## 2. Repository Model

Forge V2 should separate schema structure from code structure.

Recommended repo layout:

```text
repo/
  forge/
    system.yaml
    bootstrap.yaml
    build_policy.yaml
    verticals/
    units/
    types/
    operations/
    surfaces/
    stores/
    flows/
    verification/
    workbench/
      plan.yaml
      status.yaml
      review.md
      validation.md

  apps/
    app/
    api/
    worker/

  packages/
    contracts/
    types/
    client/
    config/

  infra/
```

Rules:

- `forge/` contains the canonical schema and workbench artifacts
- runtime code is organized by runnable unit, not by schema section
- verticals should usually appear as feature slices inside units
- shared contracts and shared types belong in `packages/`

## 3. Schema and Workbench Separation

### Schema

Canonical schema sections:

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

### Workbench

Workbench lives under:

```text
forge/workbench/
```

Recommended artifacts:

- `plan.yaml`
- `status.yaml`
- `review.md`
- `validation.md`

### Rule

Schema describes what the system is.

Workbench describes where the build currently stands.

Implementation status must not be stored on schema objects.

## 4. Project Profiles

`forge init` should scaffold by project profile rather than only creating a generic empty tree.

Recommended initial profiles:

- `full-stack`
- `api-service`
- `cli-tool`
- `worker-service`

### Profile meanings

- `full-stack`: a system with at least a user-facing app and one backing service
- `api-service`: a service-first system exposing API surfaces without a first-class frontend app
- `cli-tool`: a system primarily exposed through command surfaces
- `worker-service`: a background-processing system that reacts to queues, schedules, or internal triggers rather than being primarily user-invoked

`worker-service` is just a background runtime profile. Typical examples:

- queue consumer
- scheduled reconciler
- async job processor
- event projector

### Profile behavior

`forge init` should:

1. ask which project profile is being created
2. scaffold the canonical `forge/` tree
3. scaffold the runtime repo shape appropriate to that profile
4. seed a bootstrap-oriented starting schema
5. seed default units, stores, and verification stubs that match the profile

Recommended lightweight schema hook:

```yaml
system:
  project_profile: full-stack | api-service | cli-tool | worker-service
```

## 5. CLI Contract

The V2 CLI should stay small.

Recommended command set:

- `forge init`
- `forge graph`
- `forge context <id>`
- `forge list`

The CLI is intentionally a thin schema-navigation layer. Planning, build orchestration, and validation continue to exist in V2, but they live in the skill/framework layer and persist their state under `forge/workbench/`.

### `forge init`

Purpose:

- initialize the schema
- scaffold the repo according to project profile
- seed bootstrap-oriented defaults

Should support:

- interactive profile selection
- runtime stack selection later if needed
- profile-specific file structure seeding

### `forge graph`

Purpose:

- render graph projections from the schema

Example flags:

- `--vertical <id>`
- `--runtime`
- `--contracts`
- `--bootstrap`

### `forge context <id>`

Purpose:

- return the relevant context bundle for any schema object

This is the main skill-facing command.

### `forge list`

Purpose:

- list schema objects by section so humans and agents can discover valid IDs quickly

Examples:

- `forge list`
- `forge list operations`
- `forge list surfaces --vertical proposals`
- `forge list units`

## 6. Workbench Artifact Contract

The framework may still maintain internal workbench state for skills and agentic execution.

That state should be:

- internal to the framework and skills
- human-readable where useful
- not part of the public CLI contract by default

Canonical internal files:

```text
forge/workbench/plan.yaml
forge/workbench/status.yaml
forge/workbench/validation.md
```

### Workbench rules

- workbench artifacts may reference schema IDs as their primary linkage
- workbench artifacts may be enriched with code-level evidence later
- every slice should identify its bootstrap impact
- every slice should identify what must be re-checked after landing

## 7. Status Artifact Contract

Skills and frameworks may read both schema and workbench state.

Canonical file:

```text
forge/workbench/status.yaml
```

Recommended responsibilities:

- record slice progress
- record current bootstrap health
- record validation state
- record operator-confirmed checkpoints

The schema should not carry progress state.

## 8. Verification Model

Verification items should be explicit schema objects, including human-required checks.

Recommended verification kinds:

- `startup`
- `surface`
- `flow`
- `operator`

### Why `operator`

Some systems cannot be fully machine-checked at bootstrap time.

Examples:

- interactive CLI flows
- systems requiring browser login through external auth
- systems with hardware or managed third-party dependencies

In those cases, the framework should require an explicit operator verification item rather than leaving the need implicit.

Example operator item:

```yaml
id: bootstrap_cli_operator_check
kind: operator
target: bootstrap
intent: Human confirms the CLI bootstrap path behaves correctly in an interactive terminal
check: Run the bootstrap command sequence and confirm the expected output and side effects
```

## 9. Bootstrap-First Build Policy

Bootstrap preservation is the central execution rule of Forge V2.

The build stage should:

1. establish the minimum bootstrap slice
2. make that slice runnable as early as possible
3. run and verify bootstrap before expanding outward
4. build additional slices against the running bootstrap when possible
5. re-check startup, bootstrap, and affected flows after each material slice
6. require operator verification when automation is insufficient

This behavior should be encoded in:

- `build_policy`
- `verification`
- the build framework
- the validate framework

### Practical interpretation

- web app + API: boot both locally, then continuously re-check health and bootstrap routes
- API service: boot service, hit health plus bootstrap contract path
- worker service: boot worker plus minimal triggering surface or queue path
- CLI tool: establish a bootstrap command path, run it, and require operator verification when interaction cannot be fully scripted

## 10. Stage Frameworks

V2 should preserve stage-specific frameworks similar to V1, but align them to the V2 schema.

Recommended stages:

- `forge-discover`
- `forge-spec`
- `forge-plan`
- `forge-build`
- `forge-review`
- `forge-validate`

### `forge-discover`

Purpose:

- clarify business intent
- define verticals
- define runtime units
- identify the smallest credible bootstrap path

Consumes:

- user intent
- existing repo if present
- partial schema if present

Produces or updates:

- `system`
- `verticals`
- `units`
- `bootstrap`
- initial `build_policy`

### `forge-spec`

Purpose:

- define the canonical truth needed before implementation drift begins

Produces or updates:

- `types`
- `operations`
- `surfaces`
- `stores`
- `flows`
- `verification`

### `forge-plan`

Purpose:

- derive vertical build slices from schema truth

Produces:

- `forge/workbench/plan.yaml`
- optional rendered plan view

Rules:

- every slice must preserve or expand runnability
- every slice must identify required checks
- human checks must be explicit when needed

### `forge-build`

Purpose:

- implement the next slice while preserving runnable capability

Consumes:

- schema
- plan artifact
- current repo state
- verification items

Rules:

- bootstrap first
- run bootstrap early
- build on a running bootstrap when possible
- re-check after each material slice

### `forge-review`

Purpose:

- review schema and implementation for drift, risk, incompleteness, and security weakness

Focus:

- contract ownership
- invariant weakness
- security posture gaps
- bootstrap fragility
- verification gaps

### `forge-validate`

Purpose:

- prove the current system still satisfies startup, bootstrap, surfaces, and flows

Consumes:

- schema
- verification items
- workbench state
- current runnable system

## 11. Skill Contract

Skills should stay thin and rely on CLI outputs rather than burying logic in prompt prose.

Recommended skill responsibilities:

- `forge-discover`: clarify and author system, verticals, units, bootstrap
- `forge-spec`: author types, operations, surfaces, stores, flows, verification
- `forge-plan`: derive the next smallest safe slice
- `forge-build`: implement the slice against live bootstrap where possible
- `forge-review`: identify bugs, risk, drift, and missing coverage
- `forge-validate`: run declared checks and report confidence or regressions

## 12. Context Contract

`forge context <id>` should be the universal context loader.

### `forge context <operation>`

Should return:

- owning vertical
- owning unit
- input, output, referenced, and error types
- read and write stores
- related surfaces
- related flows
- lifecycle transitions touched
- verification items
- bootstrap relevance

### `forge context <flow>`

Should return:

- ordered path
- participating operations
- participating units
- touched stores
- related contracts
- failure modes
- verification items
- bootstrap relevance

### `forge context <unit>`

Should return:

- served verticals
- surfaces exposed
- operations owned
- stores depended on
- env requirements
- healthcheck
- run commands

### `forge context <vertical>`

Should return:

- units serving the vertical
- operations in the vertical
- surfaces exposing those operations
- relevant flows
- bootstrap overlap

## 13. Codebase Mapping

Schema layout and code layout should not be identical.

Schema layout is organized by canonical concern.

Runtime code layout should be organized by unit first, then by vertical.

Mapping rules:

1. `units` map to runnable app or service directories
2. `verticals` map to feature slices inside units
3. `operations` map to handlers, use-cases, or service methods
4. `surfaces` map to transport adapters such as routes, commands, or consumers
5. `types` map to shared contracts and domain types
6. `stores` map to infrastructure and persistence adapters

This is the recommended way to avoid the V1 implementation-structure problem.

## 14. Open Design Constraints

These constraints should remain fixed while implementing V2:

- keep the schema as the only design source of truth
- keep the command set small
- keep project init profile-driven
- keep verification items explicit, including operator checks
- keep progress state in workbench artifacts, not in schema
- keep bootstrap preservation central to planning, build, review, and validation

## Final Principle

Forge V2 should feel like the original Forge idea, but cleaner:

- a full schema
- stage-specific frameworks
- a CLI crawler and context loader
- skills that orchestrate agent work

The improvement over V1 is that these are no longer entangled.

- schema defines truth
- workbench tracks delivery state
- CLI computes structure and context
- frameworks define stage behavior
- skills drive the workflow

That is the architecture that best supports building real software vertically while keeping the system working throughout the process.
