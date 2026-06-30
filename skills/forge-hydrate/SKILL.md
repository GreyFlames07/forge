---
name: forge-hydrate
description: Reverse-engineer an existing codebase into Forge V4. Use when creating or repairing Forge V4 schema and code-owned C3 annotations from existing implementation, tests, routes, data models, persistence code, UI surfaces, jobs, CLIs, or runtime behavior. Produces evidence-backed system, container, entity, decision, and annotation drafts without inventing unsupported business intent.
---

# forge-hydrate

Read before starting:

- `../../FRAMEWORK_V4.md`
- `../../SCHEMA_REFERENCE_V4.md`
- `../forge-schema/SKILL.md`
- `../forge-review/SKILL.md`
- `../forge-security/SKILL.md`
- `../forge-build/SKILL.md`

Prefer when available:

- `forge init`
- `forge crawl --format json`
- `forge list`
- `forge context`
- `forge knowledge list`
- `forge audit`

## Purpose

Hydrate Forge V4 from an existing implementation.

This skill works in the reverse direction:

```text
code, tests, routes, schemas, storage, jobs, UI, runtime behavior
-> observed architecture
-> Forge V4 central schema
-> code-owned C3 annotations
```

Hydration documents what exists. Do not turn it into product strategy or a
future-state redesign. If business intent is missing, mark it as inferred or
route to `forge-business` later.

## Knowledge Layer

When available, inspect `forge knowledge list` and relevant `forge knowledge
list --ref <kind>:<id>` output. Runbooks, testing docs, deployment notes, and
glossaries are supporting evidence for hydration, especially when code alone is
ambiguous. Do not infer canonical architecture from prose without code, tests,
or explicit Forge schema support.

## Evidence Standard

Every hydrated claim should be backed by evidence.

Use:

- source files and line references
- tests and fixtures
- routes, handlers, controllers, screens, jobs, CLIs, queues, events, and schedulers
- type definitions, validation schemas, DTOs, serializers, and API clients
- database migrations, models, repositories, stores, and file adapters
- configuration, deployment files, scripts, and package manifests
- logs, docs, or README text only as supporting evidence

Separate:

- `observed`: directly visible in code or tests
- `inferred`: likely from usage patterns but not explicit
- `unknown`: cannot be responsibly determined

Do not fill gaps with confident prose.

## Decision Log

Read and maintain `forge/decisions.yaml` when it exists.

Record non-trivial hydration decisions, including:

- why a source root maps to a runtime container
- why a file group is treated as one component
- why a route, screen, job, or CLI maps to an interface component
- why a data model is a business entity rather than only a data shape
- why behavior is marked inferred or unknown
- why hydration intentionally defers a schema or annotation

Use the `forge.decisions` schema from `SCHEMA_REFERENCE_V4.md`.

## Modes

Use `scaffold` mode when the repo has no Forge V4 workspace.

Use `enrich` mode when Forge files or annotations already exist and need to be
completed, corrected, or aligned with current code.

If the user does not name a mode, choose based on whether `forge/` exists.

## Scaffold Mode

Workflow:

1. Inspect repository structure, package manifests, entry points, tests, and deployment/config files.
2. Identify likely runtime containers and their `source_root` values.
3. Run `forge init` only when the user wants files created.
4. Draft or update `forge/system.yaml`, `forge/containers.yaml`, `forge/entities.yaml`, and `forge/decisions.yaml`.
5. Propose C3 annotation locations before adding large annotation batches.
6. Add the smallest useful set of C3 annotations when the user asks for implementation.
7. Run `forge crawl --format json` and fix malformed schema or annotation issues.

Scaffold the broadest truthful architecture first, then deepen one flow or
container at a time.

## Enrich Mode

Workflow:

1. Run `forge crawl --format json`.
2. Compare the merged Forge model to the actual codebase.
3. Identify missing, stale, or misleading central schema.
4. Identify missing, stale, or misleading C3 annotations.
5. Patch only the scoped area requested by the user.
6. Add or update decision entries for non-trivial interpretations.
7. Run `forge crawl --format json` again and report remaining gaps.

Do not rewrite working schema merely because a different structure is possible.
Hydration should preserve useful existing Forge intent unless the code clearly
contradicts it.

## Hydration Targets

Map implementation evidence into Forge V4 like this:

- repository/product purpose -> `forge/system.yaml`
- users, services, scheduled actors -> `system.actors`
- third-party APIs, external stores, external systems -> `system.external_dependencies`
- user-visible or system-visible actions -> `system.business_actions`
- deployable/runnable units -> `containers`
- code ownership roots -> `containers[].source_root`
- cross-container behavior -> `container_flows`
- domain objects with lifecycle or ownership -> `entities`
- architectural decisions and assumptions -> `decisions`
- screens, routers, workers, schedulers, CLIs, file/event boundaries -> `@forge:component role: interface`
- services, domain modules, orchestration modules -> `@forge:component role: logic`
- repositories, stores, adapters, database access -> `@forge:component role: persistence`
- DTOs, schemas, API payloads, records, events -> `@forge:type`
- durable storage behavior -> `@forge:persistence`
- functions, handlers, methods, commands, or workflow steps -> `@forge:operation`

## Flow Hydration

Hydrate flows from observable runtime behavior.

Use business actions to identify intent, then infer runtime steps from:

- UI event to API call
- API route to service call
- service to repository or datastore
- worker/job to queue, file, API, or database
- CLI command to service or file behavior
- branch behavior in tests, validation, authorization, or error handling

Container flows belong in `forge/containers.yaml` only when control moves across
runtime containers. Work inside one container belongs in C3 operation
annotations through `container_flow`, `local_flow`, `passes`, and `flow_logic`.

If a flow is visible but the business action is unclear, write a conservative
business action with notes or mark the decision as inferred.

## Annotation Rules

Before adding annotations:

1. Confirm the file is under a declared `source_root`.
2. Match the host language comment style from `forge/crawler.yaml`.
3. Place annotations near the code that owns the behavior.
4. Prefer fewer accurate annotations over many vague annotations.
5. Do not annotate decorative UI, incidental helpers, or private plumbing unless it is architecture-significant.
6. Use stable `snake_case` ids.
7. Preserve local code style and avoid unrelated edits.

For `@forge:operation`, always include:

- `id`
- `input`
- `returns`
- `logic`
- `participates_in` when the operation is part of a known flow

## Output

When drafting in chat, produce:

- hydration scope
- evidence summary
- proposed central schema changes
- proposed C3 annotation plan
- inferred or unknown items
- decisions to record
- validation commands to run

When editing files, keep changes narrow and finish with:

- files changed
- evidence used
- decisions recorded
- `forge crawl --format json` result
- remaining gaps or review/security follow-ups

## Guardrails

1. Do not invent business strategy; route that to `forge-business`.
2. Do not redesign architecture during hydration; route future-state design to `forge-schema`.
3. Do not treat tests as perfect truth when implementation and tests disagree; report the conflict.
4. Do not add broad annotations without first confirming source-root crawlability.
5. Do not hide uncertainty.
6. Do not claim full coverage unless crawl and evidence support it.
7. Run `forge-review` after meaningful hydration and `forge-security` when sensitive flows or trust boundaries are hydrated.
